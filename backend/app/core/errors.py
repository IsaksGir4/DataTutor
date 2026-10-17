from typing import Optional
import uuid

from fastapi import Request, status
from fastapi.responses import JSONResponse


class DataTutorException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        conversation_id: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.conversation_id = conversation_id


def setup_exception_handlers(app):
    @app.exception_handler(DataTutorException)
    async def datatutor_exception_handler(
        request: Request, exc: DataTutorException
    ):
        error_payload = {
            "code": exc.code,
            "message": exc.message,
            "request_id": str(uuid.uuid4()),
        }
        if exc.conversation_id is not None:
            error_payload["conversation_id"] = exc.conversation_id

        return JSONResponse(
            status_code=exc.status_code,
            content={"error": error_payload},
        )