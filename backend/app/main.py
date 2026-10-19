from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.controllers import chat, documents
from app.core.database import SessionLocal
from app.core.errors import setup_exception_handlers
from app.repositories.document_repo import fail_interrupted_documents

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with SessionLocal() as db:
        recovered = fail_interrupted_documents(db)
        if recovered > 0:
            logger.warning(
                f"Se marcaron como 'failed' {recovered} documentos que quedaron interrumpidos en estado pending/processing."
            )
    yield


app = FastAPI(title="DataTutor", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_exception_handlers(app)
app.include_router(chat.router)
app.include_router(documents.router)