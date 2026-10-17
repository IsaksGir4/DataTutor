import sys
from pathlib import Path

from sqlalchemy import text

# Permite ejecutar este archivo directamente con:
# uv run backend/scripts/ingest_corpus.py
sys.path.append(
    str(Path(__file__).resolve().parent.parent)
)

from app.core.database import engine, SessionLocal
from app.repositories.models import Base
from app.services.ingestion import process_pdf


def setup_db() -> None:
    print("[-] Configurando base de datos e índices...")

    with engine.begin() as conn:
        conn.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector;")
        )

    Base.metadata.create_all(bind=engine)

    print("  [OK] Tablas listas.")


def ingest_all() -> None:
    setup_db()

    # TutorDatos/corpus/
    corpus_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "corpus"
    )

    if not corpus_dir.exists():
        print(
            f"[ERROR] No se encontró el directorio "
            f"{corpus_dir}."
        )
        print(
            "  Crea la carpeta 'corpus' en la raíz "
            "y añade PDFs adentro."
        )
        sys.exit(1)

    pdfs = sorted(corpus_dir.glob("*.pdf"))

    if not pdfs:
        print(
            f"[-] No hay PDFs en {corpus_dir}. "
            "Nada que hacer."
        )
        return

    print(
        f"[-] Encontrados {len(pdfs)} PDFs "
        "para ingesta masiva."
    )

    with SessionLocal() as session:
        for filepath in pdfs:
            print(
                f"[-] Procesando {filepath.name}..."
            )

            with filepath.open("rb") as f:
                content = f.read()

            process_pdf(
                session=session,
                file_content=content,
                filename=filepath.name,
                owner_id="global",
            )


if __name__ == "__main__":
    ingest_all()