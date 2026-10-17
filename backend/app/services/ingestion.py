import hashlib

import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.llm.embeddings import get_embeddings_model
from app.repositories.models import Chunk, Document


def calculate_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def process_pdf(
    session: Session,
    file_content: bytes,
    filename: str,
    owner_id: str,
    scope: str = "global",
) -> None:
    file_hash = calculate_sha256(file_content)

    # 1. Idempotencia
    existing_doc = session.execute(
        select(Document).where(
            Document.owner_id == owner_id,
            Document.sha256 == file_hash,
        )
    ).scalar_one_or_none()

    if existing_doc:
        print(
            f"  [SKIP] Documento '{filename}' "
            f"ya ingerido para owner '{owner_id}'."
        )
        return

    new_doc = None

    try:
        # 2. Abrir PDF
        with fitz.open(
            stream=file_content,
            filetype="pdf",
        ) as doc:
            total_pages = len(doc)

            # 3. Registrar documento
            new_doc = Document(
                owner_id=owner_id,
                scope=scope,
                filename=filename,
                title=filename,
                sha256=file_hash,
                size_bytes=len(file_content),
                pages=total_pages,
                chunks_count=0,
                status="processing",
                error=None,
            )

            session.add(new_doc)
            session.flush()

            # 4. Configurar procesamiento
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )

            embed_model = get_embeddings_model()

            chunks_to_insert: list[Chunk] = []
            chunk_idx = 0

            # 5. Procesar páginas
            for page_num in range(total_pages):
                page = doc.load_page(page_num)
                text = page.get_text("text").strip()

                if not text:
                    continue

                page_chunks = splitter.split_text(text)

                if not page_chunks:
                    continue

                embeddings = embed_model.embed_documents(
                    page_chunks
                )

                if len(embeddings) != len(page_chunks):
                    raise RuntimeError(
                        "La cantidad de embeddings no coincide "
                        "con la cantidad de chunks."
                    )

                for c_text, emb in zip(
                    page_chunks,
                    embeddings,
                ):
                    if len(emb) != settings.EMBED_DIM:
                        raise RuntimeError(
                            f"Dimensión de embedding inesperada: "
                            f"{len(emb)}. "
                            f"Se esperaba {settings.EMBED_DIM}."
                        )

                    chunks_to_insert.append(
                        Chunk(
                            document_id=new_doc.id,
                            owner_id=owner_id,
                            page=page_num + 1,
                            chunk_index=chunk_idx,
                            text=c_text,
                            embedding=emb,
                            embed_model=settings.EMBED_MODEL,
                        )
                    )

                    chunk_idx += 1

            # 6. Persistir
            session.add_all(chunks_to_insert)

            new_doc.chunks_count = len(chunks_to_insert)
            new_doc.status = "ready"
            new_doc.error = None

            session.commit()

            print(
                f"  [OK] '{filename}': "
                f"{total_pages} páginas, "
                f"{len(chunks_to_insert)} chunks procesados."
            )

    except Exception as exc:
        session.rollback()

        # Intentamos registrar el error en una transacción nueva.
        if new_doc is not None:
            try:
                new_doc = session.get(Document, new_doc.id)

                if new_doc is not None:
                    new_doc.status = "error"
                    new_doc.error = str(exc)[:1000]
                    session.commit()

            except Exception:
                session.rollback()

        print(
            f"  [ERROR] Falló la ingesta de '{filename}': {exc}"
        )

        raise