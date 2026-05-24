from uuid import UUID, uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.providers.object_storage import MockObjectStorageProvider
from app.repositories.memory import store
from app.schemas.documents import DocumentDetail, DocumentListResponse, DocumentStatus, DocumentUploadResponse

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class DocumentService:
    def __init__(self) -> None:
        self.storage = MockObjectStorageProvider()

    async def upload(self, user_id: UUID, knowledge_base_id: UUID, files: list[UploadFile]) -> dict:
        if len(files) > settings.max_upload_files:
            raise AppError("VALIDATION_ERROR", f"Maximum {settings.max_upload_files} files are allowed.", 422)
        documents: list[DocumentUploadResponse] = []
        for file in files:
            if file.content_type not in ALLOWED_CONTENT_TYPES:
                raise AppError("UNSUPPORTED_FILE_TYPE", f"Unsupported content type: {file.content_type}", 422)
            data = await file.read()
            if len(data) > settings.max_upload_file_size_bytes:
                raise AppError("FILE_TOO_LARGE", f"File exceeds {settings.max_upload_file_size_bytes} bytes.", 422)
            document_id = uuid4()
            s3_key = f"raw/{user_id}/{knowledge_base_id}/{document_id}/{file.filename}"
            self.storage.put_bytes(s3_key, data, file.content_type or "application/octet-stream")
            item = {
                "document_id": document_id,
                "user_id": user_id,
                "knowledge_base_id": knowledge_base_id,
                "file_name": file.filename or "document",
                "content_type": file.content_type or "application/octet-stream",
                "file_size_bytes": len(data),
                "status": DocumentStatus.uploaded,
                "s3_key": s3_key,
            }
            store.documents[document_id] = item
            documents.append(DocumentUploadResponse(**item))
        return {
            "documents": documents,
            "rules": {
                "max_files": settings.max_upload_files,
                "max_file_size_bytes": settings.max_upload_file_size_bytes,
                "allowed_content_types": sorted(ALLOWED_CONTENT_TYPES),
            },
        }

    def list(self, user_id: UUID) -> DocumentListResponse:
        docs = [DocumentDetail(**item) for item in store.documents.values() if item["user_id"] == user_id]
        return DocumentListResponse(documents=docs)

    def get(self, user_id: UUID, document_id: UUID) -> DocumentDetail:
        item = store.documents.get(document_id)
        if not item or item["user_id"] != user_id:
            raise NotFoundError("Document not found.")
        return DocumentDetail(**item)

    def delete(self, user_id: UUID, document_id: UUID) -> dict:
        document = self.get(user_id, document_id)
        store.documents[document_id]["status"] = DocumentStatus.deleted
        return {"document_id": document.document_id, "status": "deleted"}

