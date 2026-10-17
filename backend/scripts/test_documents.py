import math
import sys
import time
import uuid
from pathlib import Path

import fitz
import httpx
from sqlalchemy import select

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.config.settings import settings
from app.core.database import SessionLocal
from app.repositories.models import Chunk

TOKEN_URL = "http://127.0.0.1:8080/realms/datatutor/protocol/openid-connect/token"
API_URL = "http://127.0.0.1:8000/api/v1/documents"
TIMEOUT_POLLING_SECS = 45


def get_token(username: str, password: str) -> str:
    data = {
        "client_id": "datatutor-swagger",
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    r = httpx.post(TOKEN_URL, data=data, timeout=10.0)
    if r.status_code != 200:
        print(f"[ERROR] Falló auth ({r.status_code}): {r.text}")
        sys.exit(1)
    return r.json()["access_token"]


def build_test_pdf(run_id: str) -> bytes:
    with fitz.open() as doc:
        page = doc.new_page(width=595, height=842)
        text = (
            f"DataTutor integration test document ({run_id}).\n"
            "Data engineering pipelines require idempotent ingestion, "
            "schema validation, and vector indexing with HNSW in PostgreSQL."
        )
        page.insert_text((72, 72), text, fontsize=11)
        return doc.tobytes()


def main() -> None:
    print("[-] 1. Obteniendo token de estudiante...")
    token = get_token("estudiante", "estudiante123")
    headers = {"Authorization": f"Bearer {token}"}

    run_id = uuid.uuid4().hex
    pdf_filename = f"datatutor-test-{run_id}.pdf"
    pdf_bytes = build_test_pdf(run_id)

    print(f"\n[-] 2. Subiendo PDF temporal: {pdf_filename}")
    files = {"file": (pdf_filename, pdf_bytes, "application/pdf")}
    r_upload = httpx.post(API_URL, headers=headers, files=files, timeout=10.0)
    assert r_upload.status_code == 202, (
        f"Falló subida: {r_upload.status_code} - {r_upload.text}"
    )
    doc_id = r_upload.json()["id"]
    print(f"  [OK] Subida aceptada (HTTP 202). ID: {doc_id}")

    print("\n[-] 3. Esperando el procesamiento...")
    attempts = TIMEOUT_POLLING_SECS // 3
    for _ in range(attempts):
        r_status = httpx.get(f"{API_URL}/{doc_id}", headers=headers, timeout=10.0)
        assert r_status.status_code == 200, (
            f"Error obteniendo estado: {r_status.status_code} - {r_status.text}"
        )
        status_data = r_status.json()
        status = status_data["status"]
        print(f"     Estado actual: {status}")

        if status == "ready":
            assert status_data.get("error") is None, (
                "El documento está ready, pero conserva un error anterior."
            )
            print("  [OK] Procesamiento finalizado.")
            break
        elif status == "failed":
            print(f"  [ERROR] Procesamiento fallido: {status_data.get('error')}")
            sys.exit(1)

        time.sleep(3)
    else:
        print(f"\n[ERROR] Timeout esperando a 'ready' tras {TIMEOUT_POLLING_SECS} segundos.")
        sys.exit(1)

    print("\n[-] 4. Probando el listado...")
    r_list = httpx.get(API_URL, headers=headers, timeout=10.0)
    assert r_list.status_code == 200, "Falló endpoint GET /documents"
    assert any(d["id"] == doc_id for d in r_list.json()), (
        "El documento no aparece en la lista."
    )
    print("  [OK] Documento encontrado en el listado.")

    print("\n[-] 5. Comprobando idempotencia (409)...")
    files_dup = {"file": (pdf_filename, pdf_bytes, "application/pdf")}
    r_dup = httpx.post(API_URL, headers=headers, files=files_dup, timeout=10.0)
    assert r_dup.status_code == 409, f"Esperaba 409, dio: {r_dup.status_code}"
    print("  [OK] El duplicado fue rechazado (HTTP 409).")

    print("\n[-] 6. Validando los embeddings...")
    doc_uuid = uuid.UUID(doc_id)
    with SessionLocal() as db:
        chunks_before = db.execute(
            select(Chunk).where(Chunk.document_id == doc_uuid)
        ).scalars().all()

        assert len(chunks_before) > 0, (
            "El documento está ready, pero no tiene chunks almacenados."
        )

        for chunk in chunks_before:
            embedding = [float(value) for value in chunk.embedding]
            assert len(embedding) == settings.EMBED_DIM, (
                f"Dimensión incorrecta en chunk {chunk.id}: {len(embedding)}"
            )
            assert all(math.isfinite(value) for value in embedding), (
                f"El chunk {chunk.id} contiene valores no finitos."
            )
            norm_sq = sum(value * value for value in embedding)
            assert norm_sq >= 1e-12, (
                f"El chunk {chunk.id} tiene un embedding de norma cero."
            )

        print(
            f"  [OK] {len(chunks_before)} chunks validados: "
            "dimensión, valores finitos y norma."
        )

    print("\n[-] 7. Eliminando el documento...")
    r_del = httpx.delete(f"{API_URL}/{doc_id}", headers=headers, timeout=10.0)
    assert r_del.status_code == 204, (
        f"Fallo borrando: {r_del.status_code} - {r_del.text}"
    )
    print("  [OK] Documento eliminado (HTTP 204).")

    print("\n[-] 8. Verificando que ya no sea accesible...")
    r_verify = httpx.get(f"{API_URL}/{doc_id}", headers=headers, timeout=10.0)
    assert r_verify.status_code == 404, "El documento sigue expuesto por API."
    print("  [OK] API devuelve HTTP 404.")

    print("\n[-] 9. Verificando el borrado en cascada...")
    with SessionLocal() as db:
        remaining_chunks = db.execute(
            select(Chunk).where(Chunk.document_id == doc_uuid)
        ).scalars().all()
        assert len(remaining_chunks) == 0, (
            f"Fallo de cascada: quedan {len(remaining_chunks)} chunks."
        )
    print("  [OK] Todos los chunks fueron eliminados.")
    print("\nFASE 4: TODAS LAS COMPROBACIONES DEL TEST SUPERADAS.")


if __name__ == "__main__":
    main()