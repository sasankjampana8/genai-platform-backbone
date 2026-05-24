from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.schemas.base import PlatformModel


class DocumentStatus(StrEnum):
    uploaded = "uploaded"
    queued = "queued"
    processing = "processing"
    processed = "processed"
    failed = "failed"
    deleted = "deleted"


class DocumentUploadResponse(PlatformModel):
    document_id: UUID
    knowledge_base_id: UUID
    file_name: str
    content_type: str
    file_size_bytes: int
    status: DocumentStatus
    s3_key: str


class DocumentDetail(DocumentUploadResponse):
    user_id: UUID


class DocumentListResponse(PlatformModel):
    documents: list[DocumentDetail]


class UploadRules(PlatformModel):
    max_files: int
    max_file_size_bytes: int
    allowed_content_types: list[str] = Field(default_factory=list)

