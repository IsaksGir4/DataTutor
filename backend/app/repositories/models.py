import uuid
from datetime import datetime, timezone
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[str] = mapped_column(String, index=True)
    scope: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    area: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sha256: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pages: Mapped[int] = mapped_column(Integer)
    chunks_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="pending")
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "sha256",
            name="uix_owner_sha256",
        ),
        Index(
            "idx_docs_owner_created",
            "owner_id",
            "created_at",
        ),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
    )
    owner_id: Mapped[str] = mapped_column(String, index=True)
    page: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

    # Debe coincidir con la dimensión real de bge-m3.
    embedding: Mapped[list[float]] = mapped_column(
        Vector(1024)
    )

    embed_model: Mapped[str] = mapped_column(String)

    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
    )

    __table_args__ = (
        Index(
            "idx_chunk_doc_idx",
            "document_id",
            "chunk_index",
        ),
        Index(
            "idx_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={
                "m": 16,
                "ef_construction": 64,
            },
            postgresql_ops={
                "embedding": "vector_cosine_ops",
            },
        ),
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "idx_conv_owner_updated",
            "owner_id",
            "updated_at",
        ),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )
    owner_id: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    decision: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    sources: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    best_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    latency_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    __table_args__ = (
        Index(
            "idx_msg_conv_created",
            "conversation_id",
            "created_at",
        ),
    )