from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text

from app.core.database import SessionLocal
from app.core.deps import get_current_user
from app.main import app
from app.repositories.models import Conversation, Message

client = TestClient(app)


def test_health_and_openapi_expose_all_endpoints():
    r_health = client.get("/api/v1/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_oas = client.get("/openapi.json")
    assert r_oas.status_code == 200
    paths = r_oas.json().get("paths", {})

    expected_paths = [
        "/api/v1/health",
        "/api/v1/me",
        "/api/v1/chat",
        "/api/v1/conversations",
        "/api/v1/conversations/{conversation_id}/messages",
        "/api/v1/conversations/{conversation_id}",
        "/api/v1/documents",
        "/api/v1/documents/{doc_id}",
    ]
    for path in expected_paths:
        assert path in paths, f"Falta ruta en /openapi.json: {path}"


def test_protected_endpoints_reject_anonymous():
    fake_id = uuid.uuid4()
    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/api/v1/conversations").status_code == 401
    assert client.get(f"/api/v1/conversations/{fake_id}/messages").status_code == 401
    assert client.delete(f"/api/v1/conversations/{fake_id}").status_code == 401
    assert client.get("/api/v1/documents").status_code == 401
    assert client.post("/api/v1/chat", json={"question": "Hola"}).status_code == 401


def test_database_foreign_keys_enforce_sql_on_delete_cascade():
    """Comprueba que PostgreSQL (y no solo el ORM) tenga ON DELETE CASCADE."""
    owner = f"pytest-sql-cascade-{uuid.uuid4()}"
    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT conname, confdeltype
                FROM pg_constraint
                WHERE conname IN ('chunks_document_id_fkey', 'messages_conversation_id_fkey')
                """
            )
        ).all()
        constraints = {row[0]: row[1] for row in rows}
        assert constraints.get("chunks_document_id_fkey") == "c"
        assert constraints.get("messages_conversation_id_fkey") == "c"

        conv = Conversation(owner_id=owner, title="Prueba cascada SQL")
        db.add(conv)
        db.commit()
        db.refresh(conv)

        msg = Message(
            conversation_id=conv.id,
            owner_id=owner,
            role="user",
            content="Mensaje que debe borrarse por FK de PostgreSQL",
        )
        db.add(msg)
        db.commit()

        # DELETE SQL directo (sin pasar por db.delete(conv) del ORM)
        db.execute(delete(Conversation).where(Conversation.id == conv.id))
        db.commit()

        rem_msgs = db.execute(
            select(Message).where(Message.conversation_id == conv.id)
        ).scalars().all()
        assert len(rem_msgs) == 0


def test_chat_503_returns_conversation_id_to_avoid_duplicate_conversations():
    user_id = f"pytest-503-user-{uuid.uuid4()}"
    created_conv_id = None

    app.dependency_overrides[get_current_user] = lambda: {
        "sub": user_id,
        "preferred_username": "user_503",
        "roles": ["user"],
    }
    try:
        with patch(
            "app.services.chat.agent_app.invoke",
            side_effect=RuntimeError("Fallo simulado de Ollama"),
        ):
            r_fail = client.post(
                "/api/v1/chat",
                json={"question": "¿Qué pasa si el LLM falla tras guardar la pregunta?"},
            )
        assert r_fail.status_code == 503
        err_body = r_fail.json()["error"]
        assert err_body["code"] == "agent_error"
        assert "conversation_id" in err_body
        created_conv_id = err_body["conversation_id"]

        # Reintentar reutiliza la conversación (no duplica Conversation),
        # aunque registra el nuevo envío de Message(role='user').
        fake_ok = {
            "answer": "Respuesta recuperada en el reintento [1].",
            "decision": "answered",
            "sources": [],
            "best_score": 0.78,
        }
        with patch("app.services.chat.agent_app.invoke", return_value=fake_ok):
            r_retry = client.post(
                "/api/v1/chat",
                json={
                    "question": "¿Qué pasa si el LLM falla tras guardar la pregunta?",
                    "conversation_id": created_conv_id,
                },
            )
        assert r_retry.status_code == 200
        assert r_retry.json()["conversation_id"] == created_conv_id

        r_convs = client.get("/api/v1/conversations")
        assert len(r_convs.json()) == 1

        r_msgs = client.get(f"/api/v1/conversations/{created_conv_id}/messages")
        assert r_msgs.status_code == 200
        assert len(r_msgs.json()) == 3
    finally:
        app.dependency_overrides.clear()
        if created_conv_id:
            with SessionLocal() as db:
                conv_obj = db.get(Conversation, uuid.UUID(created_conv_id))
                if conv_obj:
                    db.delete(conv_obj)
                    db.commit()


def test_conversation_lifecycle_and_cross_user_isolation():
    user_a = f"pytest-user-a-{uuid.uuid4()}"
    user_b = f"pytest-user-b-{uuid.uuid4()}"
    conv_id = None

    fake_agent_output = {
        "answer": "Respuesta simulada con cita [1].",
        "decision": "answered",
        "sources": [
            {
                "document": "doc_test.pdf",
                "page": 2,
                "snippet": "Fragmento de prueba...",
                "score": 0.81,
            }
        ],
        "best_score": 0.81,
    }

    try:
        app.dependency_overrides[get_current_user] = lambda: {
            "sub": user_a,
            "preferred_username": "usuario_a",
            "roles": ["user"],
        }

        r_blank = client.post("/api/v1/chat", json={"question": "   "})
        assert r_blank.status_code == 422

        with patch("app.services.chat.agent_app.invoke", return_value=fake_agent_output):
            r_chat_a = client.post(
                "/api/v1/chat",
                json={"question": "¿Qué es un índice HNSW en pgvector?"},
            )
        assert r_chat_a.status_code == 200
        conv_id = r_chat_a.json()["conversation_id"]

        r_msgs_a = client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert r_msgs_a.status_code == 200
        msgs_payload = r_msgs_a.json()
        assert len(msgs_payload) == 2
        assert msgs_payload[0]["role"] == "user"
        assert msgs_payload[0]["content"] == "¿Qué es un índice HNSW en pgvector?"
        assert msgs_payload[1]["role"] == "assistant"
        assert msgs_payload[1]["content"] == "Respuesta simulada con cita [1]."
        assert isinstance(msgs_payload[1]["sources"], list)
        assert len(msgs_payload[1]["sources"]) == 1
        assert msgs_payload[1]["sources"][0]["document"] == "doc_test.pdf"

        app.dependency_overrides[get_current_user] = lambda: {
            "sub": user_b,
            "preferred_username": "usuario_b",
            "roles": ["user"],
        }

        r_list_b = client.get("/api/v1/conversations")
        assert r_list_b.status_code == 200
        assert all(c["id"] != conv_id for c in r_list_b.json())

        assert (
            client.get(f"/api/v1/conversations/{conv_id}/messages").status_code
            == 404
        )
        assert (
            client.delete(f"/api/v1/conversations/{conv_id}").status_code == 404
        )

        with patch("app.services.chat.agent_app.invoke", return_value=fake_agent_output):
            r_hijack = client.post(
                "/api/v1/chat",
                json={"question": "Intento ajeno", "conversation_id": conv_id},
            )
        assert r_hijack.status_code == 404

        app.dependency_overrides[get_current_user] = lambda: {
            "sub": user_a,
            "preferred_username": "usuario_a",
            "roles": ["user"],
        }
        r_del_a = client.delete(f"/api/v1/conversations/{conv_id}")
        assert r_del_a.status_code == 204
        conv_id = None
    finally:
        app.dependency_overrides.clear()
        if conv_id is not None:
            with SessionLocal() as db:
                conv_obj = db.get(Conversation, uuid.UUID(conv_id))
                if conv_obj:
                    db.delete(conv_obj)
                    db.commit()