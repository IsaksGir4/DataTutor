"""Auditoría del corpus: ¿cada PDF tiene texto extraíble, cuánto y en qué idioma?

Uso:
    python audit_corpus.py <carpeta_con_pdfs>

Para cada PDF mide, sobre una muestra de ~25 páginas repartidas por todo el libro:
  - páginas totales y tamaño en MB
  - caracteres promedio por página (si es ~0, el PDF es escaneado: son imágenes)
  - % de páginas de la muestra casi vacías
  - idioma aproximado (es / en / mixto)
  - chunks estimados con CHUNK_SIZE=1000 y CHUNK_OVERLAP=150
"""
import re
import sys
import time
from pathlib import Path

import pymupdf  # PyMuPDF

CHUNK_SIZE, CHUNK_OVERLAP = 1000, 150
SAMPLE_PAGES = 25
ES = {"el", "la", "de", "que", "y", "en", "los", "las", "un", "una", "por", "con", "para", "es", "se", "del"}
EN = {"the", "of", "and", "to", "in", "is", "that", "for", "with", "as", "are", "on", "by", "this"}


def sample_indices(n_pages: int) -> list[int]:
    if n_pages <= SAMPLE_PAGES:
        return list(range(n_pages))
    step = n_pages / SAMPLE_PAGES
    return [int(i * step) for i in range(SAMPLE_PAGES)]


def audit(pdf: Path) -> dict:
    t0 = time.perf_counter()
    doc = pymupdf.open(pdf)
    n_pages = len(doc)
    chars, words = [], []
    for i in sample_indices(n_pages):
        text = doc[i].get_text("text")
        chars.append(len(text.strip()))
        words += re.findall(r"[a-záéíóúñ]+", text.lower())
    doc.close()

    avg = sum(chars) / len(chars) if chars else 0
    empty_pct = 100 * sum(c < 50 for c in chars) / len(chars) if chars else 100
    es = sum(w in ES for w in words)
    en = sum(w in EN for w in words)
    lang = "es" if es > en * 1.2 else "en" if en > es * 1.2 else "mixto/?"
    est_chars = avg * n_pages
    est_chunks = int(est_chars / (CHUNK_SIZE - CHUNK_OVERLAP))
    scanned = empty_pct > 30 or avg < 200
    return {
        "file": pdf.name,
        "mb": pdf.stat().st_size / 1_048_576,
        "pages": n_pages,
        "avg": avg,
        "empty_pct": empty_pct,
        "lang": lang,
        "chunks": est_chunks,
        "flag": "ESCANEADO?" if scanned else "ok",
        "secs": time.perf_counter() - t0,
    }


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("corpus")
    pdfs = sorted(folder.rglob("*.pdf"))
    if not pdfs:
        sys.exit(f"No hay PDFs en {folder.resolve()}")

    print(f"{'archivo':50} {'MB':>6} {'pág':>5} {'car/pág':>8} {'vacías%':>8} {'idioma':>8} {'chunks~':>8}  estado")
    total_chunks = 0
    for pdf in pdfs:
        try:
            r = audit(pdf)
        except Exception as exc:  # PDF corrupto, protegido, etc.
            print(f"{pdf.name[:50]:50} ERROR: {exc}")
            continue
        total_chunks += r["chunks"]
        print(
            f"{r['file'][:50]:50} {r['mb']:6.1f} {r['pages']:5d} {r['avg']:8.0f} "
            f"{r['empty_pct']:8.0f} {r['lang']:>8} {r['chunks']:8d}  {r['flag']}"
        )
    print(f"\nTotal estimado de chunks: ~{total_chunks}")
    print("Regla: 'ESCANEADO?' = casi sin texto extraíble; esos PDFs necesitarían OCR y quedan fuera de la v1.")


if __name__ == "__main__":
    main()
