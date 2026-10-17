from sqlalchemy.orm import Session
from sqlalchemy import select
from app.repositories.models import Conversation, Message
from app.core.errors import DataTutorException
import uuid

from datetime import datetime, timezone


def get_or_create_conversation(db: Session, conv_id: uuid.UUID | None, owner_id: str, title: str) -> uuid.UUID:
    if conv_id:
        conv = db.execute(select(Conversation).where(Conversation.id == conv_id)).scalar_one_or_none()
        if not conv or conv.owner_id != owner_id:
            raise DataTutorException("conv_not_found", "Conversación no Encontrada", 404)
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()
        return conv.id

    new_conv = Conversation(owner_id=owner_id, title=title)
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)
    return new_conv.id


def save_message(db: Session, conv_id: uuid.UUID, owner_id: str, role: str, content: str,
                 decision: str | None = None, sources: list | None = None, best_score: float|None = None, latency: int | None = None) -> None:
    conv = db.execute(
        select(Conversation).where(
            Conversation.id == conv_id,
            Conversation.owner_id == owner_id,
        )
    ).scalar_one_or_none()
    if not conv:
        raise DataTutorException(
            "conv_not_found", "Conversación no encontrada.", 404
        )

    now = datetime.now(timezone.utc)
    conv.updated_at = now

    msg = Message(
        conversation_id=conv.id,
        owner_id=owner_id,
        role=role,
        content=content,
        decision=decision,
        sources=sources,
        best_score=best_score,
        latency_ms=latency,
        created_at=now,
    )

    db.add(msg)
    db.commit()


def get_conversation_history(db: Session, conv_id: uuid.UUID, owner_id: str, limit: int = 6) -> list[dict]:
    stmt = (
        select(Message)
        .join(Conversation)
        .where(
            Message.conversation_id == conv_id,
            Conversation.owner_id == owner_id,
            Message.owner_id == owner_id
        ).order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )
    msgs = db.execute(stmt).scalars().all()
    # Devolvemos de más antiguo a más reciente
    return [{"role": m.role, "content": m.content} for m in reversed(msgs)]

def list_user_conversations(db: Session, owner_id: str) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.owner_id == owner_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_conversation_messages(
    db: Session,
    conv_id: uuid.UUID,
    owner_id: str,
) -> list[Message]:
    conv = db.execute(
        select(Conversation).where(
            Conversation.id == conv_id,
            Conversation.owner_id == owner_id,
        )
    ).scalar_one_or_none()
    if not conv:
        raise DataTutorException(
            "conv_not_found", "Conversación no encontrada.", 404
        )

    stmt = (
        select(Message)
        .where(
            Message.conversation_id == conv_id,
            Message.owner_id == owner_id,
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    return list(db.execute(stmt).scalars().all())


def delete_user_conversation(
    db: Session,
    conv_id: uuid.UUID,
    owner_id: str,
) -> None:
    conv = db.execute(
        select(Conversation).where(
            Conversation.id == conv_id,
            Conversation.owner_id == owner_id,
        )
    ).scalar_one_or_none()
    if not conv:
        raise DataTutorException(
            "conv_not_found", "Conversación no encontrada.", 404
        )
    db.delete(conv)
    db.commit()