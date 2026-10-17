import hashlib
import logging
import math
import uuid

from fastapi import BackgroundTasks, UploadFile
import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.database import SessionLocal
from app.core.errors import DataTutorException
from app.llm.embeddings import get_embeddings_model
from app.repositories.document_repo import create_pending_document
from app.repositories.models import Chunk, Document
from app.schemas.document import UploadResponse

logger = logging.getLogger(__name__)


def handle_upload(
    db: Session,
    file: UploadFile,
    user_id: str,
    background_tasks: BackgroundTasks,
) -> UploadResponse:
    limit_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    content = file.file.read(limit_bytes + 1)

    if len(content) > limit_bytes:
        raise DataTutorException(
            "file_too_large",
            f"Excede límite de {settings.MAX_UPLOAD_MB}MB.",
            413,
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise DataTutorException(
            "invalid_file_extension", "Solo se admiten archivos PDF.", 415
        )

    if not content.startswith(b"%PDF"):
        raise DataTutorException(
            "invalid_file_type",
            "El archivo está corrupto o no es un PDF real.",
            415,
        )

    file_hash = hashlib.sha256(content).hexdigest()
    doc = create_pending_document(
        db, user_id, file.filename, file_hash, len(content)
    )

    background_tasks.add_task(process_pdf_background, doc.id, content)
    return UploadResponse(
        id=doc.id,
        status="pending",
        message="Documento en cola de procesamiento.",
    )


def process_pdf_background(doc_id: uuid.UUID, file_content: bytes) -> None:
    db = None
    try:
        db = SessionLocal()
        doc = db.get(Document, doc_id)
        if not doc:
            return

        with fitz.open(stream=file_content, filetype="pdf") as pdf:
            total_pages = len(pdf)
            # Persistimos inmediatamente el total de páginas para dar visibilidad en la UI
            doc.status = "processing"
            doc.pages = total_pages
            doc.error = None
            db.commit()

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            embed_model = get_embeddings_model()

            chunks_to_insert: list[Chunk] = []
            chunk_idx = 0

            for page_num in range(total_pages):
                page = pdf.load_page(page_num)
                text = page.get_text("text").strip()
                if not text:
                    continue

                page_chunks = splitter.split_text(text)
                if not page_chunks:
                    continue

                embeddings = embed_model.embed_documents(page_chunks)

                if len(embeddings) != len(page_chunks):
                    raise RuntimeError(
                        f"Desajuste: {len(page_chunks)} chunks vs {len(embeddings)} vectores."
                    )

                for c_text, emb in zip(page_chunks, embeddings):
                    if len(emb) != settings.EMBED_DIM:
                        raise ValueError(
                            f"Vector incorrecto: Dimensión {len(emb)}, se esperaba {settings.EMBED_DIM}."
                        )

                    if not all(math.isfinite(float(v)) for v in emb):
                        raise ValueError(
                            "El embedding contiene valores no finitos."
                        )

                    norm_sq = sum(float(v) ** 2 for v in emb)
                    if norm_sq < 1e-12:
                        raise ValueError(
                            "Embedding de norma cero o demasiado pequeña."
                        )

                    chunks_to_insert.append(
                        Chunk(
                            document_id=doc.id,
                            owner_id=doc.owner_id,
                            page=page_num + 1,
                            chunk_index=chunk_idx,
                            text=c_text,
                            embedding=emb,
                            embed_model=settings.EMBED_MODEL,
                        )
                    )
                    chunk_idx += 1

        if not chunks_to_insert:
            doc.chunks_count = 0
            doc.status = "failed"
            doc.error = "No se encontró texto seleccionable en el PDF (posible documento escaneado o solo imágenes)."
            db.commit()
            logger.warning(
                f"[BACKGROUND] Documento {doc_id} ('{doc.filename}') marcado como failed: 0 chunks de texto extraídos."
            )
            return

        db.add_all(chunks_to_insert)
        doc.chunks_count = len(chunks_to_insert)
        doc.status = "ready"
        doc.error = None
        db.commit()

        logger.info(
            f"[BACKGROUND] Documento {doc_id} ('{doc.filename}') indexado exitosamente ({doc.chunks_count} chunks)."
        )

    except Exception:
        if db:
            db.rollback()
        logger.exception(f"Error procesando documento {doc_id}")

        if db:
            try:
                doc = db.get(Document, doc_id)
                if doc:
                    doc.status = "failed"
                    doc.error = (
                        "Fallo al procesar embeddings o leer el documento."
                    )
                    db.commit()
            except Exception as inner_exc:
                logger.error(
                    f"Error crítico actualizando estado a failed: {inner_exc}"
                )
    finally:
        if db:
            db.close()