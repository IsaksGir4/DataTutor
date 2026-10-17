from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
import uuid

from app.core.deps import get_db, get_current_user
from app.schemas.document import DocumentResponse, UploadResponse
from app.repositories import document_repo
from app.services import documents as doc_service

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

@router.get("", response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return document_repo.get_documents(db, current_user["sub"])

@router.post("", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return doc_service.handle_upload(db, file, current_user["sub"], background_tasks)

@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: uuid.UUID, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return document_repo.get_document_by_id(db, doc_id, current_user["sub"])

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: uuid.UUID, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    document_repo.delete_user_document(db, doc_id, current_user["sub"])
    return None