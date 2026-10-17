import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationSummary,
    MessageItem,
)
from app.services.chat import (
    get_messages_for_user_conversation,
    list_conversations_for_user,
    process_chat,
    remove_user_conversation,
)

router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "datatutor"}


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return process_chat(db, current_user["sub"], request)


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return list_conversations_for_user(db, current_user["sub"])


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageItem],
)
def list_conversation_messages(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return get_messages_for_user_conversation(
        db, conversation_id, current_user["sub"]
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    remove_user_conversation(db, conversation_id, current_user["sub"])
    return None