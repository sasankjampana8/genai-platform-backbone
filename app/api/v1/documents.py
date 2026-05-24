from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.responses import success_payload
from app.core.security import AuthContext, get_auth_context
from app.services.document_service import DocumentService

router = APIRouter()
service = DocumentService()


@router.post("/upload")
async def upload_documents(
    knowledge_base_id: UUID = Form(...),
    files: list[UploadFile] = File(...),
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    return success_payload(await service.upload(auth.user_id, knowledge_base_id, files))


@router.get("")
def list_documents(auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.list(auth.user_id))


@router.get("/{document_id}")
def get_document(document_id: UUID, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.get(auth.user_id, document_id))


@router.delete("/{document_id}")
def delete_document(document_id: UUID, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.delete(auth.user_id, document_id))

