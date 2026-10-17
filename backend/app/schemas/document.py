from pydantic import BaseModel, ConfigDict
from typing import Optional
import uuid

from datetime import datetime

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    scope: str
    status: str
    pages: int
    chunks_count: int
    size_bytes: Optional[int]
    created_at: datetime
    error: Optional[str]

class UploadResponse(BaseModel):
    id: uuid.UUID
    status: str
    message: str