import logging
import uuid

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DataTutorException
from app.repositories.models import Document

logger = logging.getLogger(__name__)


def get_documents(db: Session, owner_id: str) -> list[Document]:
    stmt = (
        select(Document)
        .where(or_(Document.owner_id == owner_id, Document.scope == "global"))
        .order_by(Document.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_document_by_id(
    db: Session, doc_id: uuid.UUID, owner_id: str
) -> Document:
    doc = db.execute(
        select(Document).where(Document.id == doc_id)
    ).scalar_one_or_none()
    if not doc or (doc.owner_id != owner_id and doc.scope != "global"):
        raise DataTutorException(
            "doc_not_found", "Documento no encontrado.", 404
        )
    return doc


def create_pending_document(
    db: Session, owner_id: str, filename: str, sha256: str, size_bytes: int
) -> Document:
    existing = db.execute(
        select(Document).where(
            Document.owner_id == owner_id, Document.sha256 == sha256
        )
    ).scalar_one_or_none()
    if existing:
        raise DataTutorException(
            "doc_duplicate", "El documento ya fue subido.", 409
        )

    new_doc = Document(
        owner_id=owner_id,
        scope="user",
        filename=filename,
        title=filename,
        sha256=sha256,
        size_bytes=size_bytes,
        pages=0,
        chunks_count=0,
        status="pending",
    )
    db.add(new_doc)
    try:
        db.commit()
        db.refresh(new_doc)
        return new_doc
    except IntegrityError as e:
        db.rollback()
        if hasattr(e.orig, "sqlstate") and e.orig.sqlstate == "23505":
            raise DataTutorException(
                "doc_duplicate", "El documento ya fue subido.", 409
            )
        raise


def delete_user_document(
    db: Session, doc_id: uuid.UUID, owner_id: str
) -> None:
    doc = db.execute(
        select(Document).where(
            Document.id == doc_id, Document.owner_id == owner_id
        )
    ).scalar_one_or_none()
    if not doc:
        raise DataTutorException(
            "doc_not_found",
            "Documento no encontrado o no tienes permiso para borrarlo.",
            404,
        )

    if doc.status in ["pending", "processing"]:
        raise DataTutorException(
            "doc_locked",
            "El documento está en procesamiento, inténtalo más tarde.",
            409,
        )

    db.delete(doc)
    db.commit()


def fail_interrupted_documents(db: Session) -> int:
    """
    Marca como 'failed' los documentos que quedaron en 'pending' o 'processing'
    tras un reinicio previo del proceso del servidor.
    """
    stmt = (
        update(Document)
        .where(Document.status.in_(["pending", "processing"]))
        .values(
            status="failed",
            error="Procesamiento interrumpido por reinicio del servidor. Elimina el documento y vuelve a subirlo.",
        )
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0