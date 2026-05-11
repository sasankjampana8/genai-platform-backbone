from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ALLOWED_CONTENT_TYPES = {PDF_CONTENT_TYPE: "pdf", DOCX_CONTENT_TYPE: "docx"}
MAX_FILE_SIZE_BYTES = 10_485_760


class CloudRAGModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GlobalResponseMetadata(CloudRAGModel):
    timestamp: str
    api_version: str = "v1"


class GlobalSuccessResponse(CloudRAGModel):
    request_id: str
    status: Literal["success"] = "success"
    data: dict[str, Any] | list[Any] = Field(default_factory=dict)
    metadata: GlobalResponseMetadata


class ErrorDetail(CloudRAGModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class GlobalErrorResponse(CloudRAGModel):
    request_id: str
    status: Literal["error"] = "error"
    error: ErrorDetail
    metadata: GlobalResponseMetadata


def validate_email(value: str) -> str:
    value = value.strip().lower()
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        raise ValueError("email must be valid")
    return value


class SignupRequest(CloudRAGModel):
    email: str
    password: str = Field(min_length=8, max_length=256)
    name: str = Field(min_length=1, max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return validate_email(value)


class ConfirmRequest(CloudRAGModel):
    email: str
    confirmation_code: str = Field(min_length=4, max_length=16)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return validate_email(value)


class LoginRequest(CloudRAGModel):
    email: str
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return validate_email(value)


class RefreshRequest(CloudRAGModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(CloudRAGModel):
    access_token: str = Field(min_length=1)


class AuthTokenResponse(CloudRAGModel):
    access_token: str
    id_token: str | None = None
    refresh_token: str | None = None
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(default=900, ge=1)


class UploadFileRequest(CloudRAGModel):
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str
    file_size_bytes: int = Field(gt=0, le=MAX_FILE_SIZE_BYTES)

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, value: str) -> str:
        if value not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"unsupported content_type: {value}")
        return value

    @model_validator(mode="after")
    def validate_extension_matches_content_type(self) -> "UploadFileRequest":
        expected = ALLOWED_CONTENT_TYPES[self.content_type]
        actual = self.file_name.rsplit(".", 1)[-1].lower() if "." in self.file_name else ""
        if actual != expected:
            raise ValueError(f"file extension .{actual or '(missing)'} does not match {self.content_type}")
        return self


class DocumentUploadUrlRequest(CloudRAGModel):
    files: list[UploadFileRequest] = Field(min_length=1, max_length=10)


class UploadPostData(CloudRAGModel):
    url: str
    fields: dict[str, str]


class DocumentDetail(CloudRAGModel):
    document_id: str
    file_name: str
    upload_status: str
    processing_status: str
    content_type: str | None = None
    file_extension: str | None = None
    file_size_bytes: int | None = None
    s3_bucket: str | None = None
    s3_key: str | None = None
    latest_process_id: str | None = None
    chunk_count: int | None = None
    s3_object_exists: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DocumentUploadUrlItem(DocumentDetail):
    upload: UploadPostData


class DocumentUploadUrlResponse(CloudRAGModel):
    documents: list[DocumentUploadUrlItem]
    max_files: int
    max_file_size_bytes: int


class ProcessDocumentRequest(CloudRAGModel):
    embedding_model: str = "text-embedding-3-small"
    chunking_strategy: str = "recursive"
    chunk_size: int = Field(default=800, ge=100, le=5000)
    chunk_overlap: int = Field(default=120, ge=0)

    @model_validator(mode="after")
    def validate_chunk_overlap(self) -> "ProcessDocumentRequest":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return self


class ProcessStatusResponse(CloudRAGModel):
    process_id: str
    document_id: str
    status: str
    stage: str | None = None
    total_chunks: int = 0
    embedded_chunks: int = 0
    failed_chunks: int = 0
    error_message: str | None = None


class RetrievalQueryRequest(CloudRAGModel):
    query: str = Field(min_length=1, max_length=8000)
    document_ids: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) != len(value):
            raise ValueError("document_ids must be non-empty strings")
        return cleaned


class RetrievalResult(CloudRAGModel):
    chunk_id: str
    document_id: str
    file_name: str | None = None
    page_number: int | None = None
    chunk_index: int | None = None
    score: float
    text: str


class RetrievalQueryResponse(CloudRAGModel):
    query: str
    results: list[RetrievalResult]


class CreateChatRequest(CloudRAGModel):
    title: str = Field(default="New Chat", min_length=1, max_length=160)


class ChatSummary(CloudRAGModel):
    chat_id: str
    title: str
    status: Literal["ACTIVE", "ARCHIVED"] = "ACTIVE"
    message_count: int = 0
    last_message_preview: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ChatDetail(ChatSummary):
    memory_summary: str | None = None


class RuntimeOptions(CloudRAGModel):
    use_rag: bool = True
    use_memory: bool = True
    use_web: bool = False
    allow_charts: bool = False


class SendMessageRequest(CloudRAGModel):
    input: str = Field(min_length=1, max_length=16000)
    document_ids: list[str] = Field(default_factory=list)
    runtime_options: RuntimeOptions = Field(default_factory=RuntimeOptions)

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) != len(value):
            raise ValueError("document_ids must be non-empty strings")
        return cleaned


class SendMessageResponse(CloudRAGModel):
    chat_id: str
    message_id: str
    run_id: str
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED"]


class Citation(CloudRAGModel):
    chunk_id: str
    document_id: str
    file_name: str | None = None
    page_number: int | None = None
    score: float | None = None


class Artifact(CloudRAGModel):
    artifact_id: str
    artifact_type: str
    content_type: str
    s3_key: str | None = None
    presigned_url: str | None = None


class MessageDetail(CloudRAGModel):
    chat_id: str
    message_id: str
    role: Literal["USER", "ASSISTANT", "TOOL", "SYSTEM"]
    content: str
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED"]
    run_id: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class MessageResponse(CloudRAGModel):
    message_id: str
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED"]
    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    run_id: str
    error_message: str | None = None


class MemoryRecord(CloudRAGModel):
    memory_id: str
    memory_type: Literal["CONVERSATION_SUMMARY", "IMPORTANT_FACT", "TOOL_RESULT_SUMMARY"]
    content: str
    source_message_ids: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: str | None = None
    updated_at: str | None = None


class MemorySummary(CloudRAGModel):
    chat_id: str
    memory_summary: str | None = None
    memories: list[MemoryRecord] = Field(default_factory=list)


class SummarizeMemoryRequest(CloudRAGModel):
    source_message_limit: int = Field(default=20, ge=1, le=100)


class RunSummary(CloudRAGModel):
    run_id: str
    chat_id: str
    message_id: str
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED"]
    route: Literal["DIRECT", "RAG", "WEB", "CHART", "HYBRID"] | None = None
    query_preview: str | None = None
    answer_preview: str | None = None
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    trace_id: str | None = None
    trace_s3_key: str | None = None
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class TraceSpan(CloudRAGModel):
    span_id: str
    parent_span_id: str | None = None
    name: str
    start_time: str
    end_time: str | None = None
    latency_ms: int | None = None
    status: Literal["success", "error", "running"] = "running"
    attributes: dict[str, Any] = Field(default_factory=dict)


class RunTrace(CloudRAGModel):
    trace_id: str
    run_id: str
    user_id: str
    chat_id: str
    message_id: str
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED"]
    spans: list[TraceSpan] = Field(default_factory=list)
    retrieved_chunks: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    final_answer_preview: str | None = None
    created_at: str | None = None


class ObservabilitySummary(CloudRAGModel):
    window: str = "24h"
    total_runs: int = 0
    completed_runs: int = 0
    failed_runs: int = 0
    avg_latency_ms: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost: float = 0.0
    routes: dict[str, int] = Field(default_factory=dict)


class AskCompatibilityRequest(CloudRAGModel):
    chat_id: str | None = None
    query: str = Field(min_length=1, max_length=16000)
    document_ids: list[str] = Field(default_factory=list)
    runtime_options: RuntimeOptions = Field(default_factory=RuntimeOptions)


class PaginatedResponse(CloudRAGModel):
    next_token: str | None = None


def parse_model(model: type[CloudRAGModel], payload: dict[str, Any]) -> CloudRAGModel:
    return model.model_validate(payload)
