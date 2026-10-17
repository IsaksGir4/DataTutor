from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceModel(BaseModel):
    document: str
    page: int
    snippet: str
    score: float


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)
    conversation_id: Optional[uuid.UUID] = None

    @field_validator("question")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError(
                "La pregunta no puede estar vacia y debe tener al menos 2 caracteres."
            )
        return cleaned


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    answer: str
    decision: str
    sources: List[SourceModel]
    latency_ms: int


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    decision: Optional[str] = None
    sources: Optional[List[SourceModel]] = None
    best_score: Optional[float] = None
    latency_ms: Optional[int] = None
    created_at: datetime