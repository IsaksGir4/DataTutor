import time
import logging
import uuid

from sqlalchemy.orm import Session

from app.agents.graph import agent_app

from app.repositories.chat_repo import (
    get_or_create_conversation,
    get_conversation_history,
    save_message,
    delete_user_conversation,
    get_conversation_messages,
    list_user_conversations,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.core.errors import DataTutorException

from app.repositories.models import Conversation, Message

logger = logging.getLogger(__name__)

def process_chat(db: Session, user_id: str, request: ChatRequest) -> ChatResponse:
    """
    Orquesta un turno de conversación con el grafo LangGraph.

    Nota sobre consistencia transaccional y reintentos tras HTTP 503:
    1. La creación/validación de la conversación y el guardado del mensaje del
       usuario (role='user') realizan commit antes de invocar `agent_app.invoke`
       para no mantener transacciones SQL abiertas durante la inferencia en CPU.
    2. Si `agent_app.invoke` lanza una excepción, se responde HTTP 503 incluyendo
       `error.conversation_id`. Esto permite al frontend fijar `activeConvId` y
       evitar la creación de conversaciones duplicadas al reintentar.
    3. Limitación conocida: el envío del mensaje NO es idempotente. Si el usuario
       reintenta enviando la misma pregunta tras un 503, se reutilizará la misma
       conversación, pero se insertará un nuevo registro `Message` (role='user')
       en la tabla `messages`.
    """
    start_time = time.time()

    conv_id = get_or_create_conversation(
        db, request.conversation_id, user_id, title=request.question[:40]
    )
    history = get_conversation_history(db, conv_id, user_id)

    save_message(db, conv_id, user_id, role="user", content=request.question)

    state_input = {
        "question": request.question,
        "owner_id": user_id,
        "history": history,
        "retries": 0,
    }

    try:
        final_state = agent_app.invoke(state_input)
    except Exception:
        logger.exception("Error interno al ejecutar el grafo de LangGraph")
        raise DataTutorException(
            "agent_error",
            "El agente no pudo procesar la consulta temporalmente.",
            503,
            conversation_id=str(conv_id),
        )

    latency = int((time.time() - start_time) * 1000)

    save_message(
        db=db,
        conv_id=conv_id,
        owner_id=user_id,
        role="assistant",
        content=final_state.get("answer", "Error interno"),
        decision=final_state.get("decision", "error"),
        sources=final_state.get("sources", []),
        best_score=final_state.get("best_score", 0.0),
        latency=latency,
    )

    return ChatResponse(
        conversation_id=conv_id,
        answer=final_state.get("answer", "Sin respuesta"),
        decision=final_state.get("decision", "error"),
        sources=final_state.get("sources", []),
        latency_ms=latency,
    )


def list_conversations_for_user(db: Session, user_id: str) -> list[Conversation]:
    return list_user_conversations(db, user_id)


def get_messages_for_user_conversation(
    db: Session, conv_id: uuid.UUID, user_id: str
) -> list[Message]:
    return get_conversation_messages(db, conv_id, user_id)


def remove_user_conversation(
    db: Session, conv_id: uuid.UUID, user_id: str
) -> None:
    delete_user_conversation(db, conv_id, user_id)