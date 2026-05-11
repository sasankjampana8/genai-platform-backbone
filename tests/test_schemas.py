import pytest
from pydantic import ValidationError

from shared.schemas import (
    AskCompatibilityRequest,
    DocumentUploadUrlRequest,
    ProcessDocumentRequest,
    RetrievalQueryRequest,
    RuntimeOptions,
    SendMessageRequest,
    SignupRequest,
)


def test_signup_request_normalizes_email():
    request = SignupRequest(email="TEST@Example.com", password="TestPassword123!", name="Test User")

    assert request.email == "test@example.com"


def test_upload_request_accepts_pdf_and_docx():
    request = DocumentUploadUrlRequest(
        files=[
            {
                "file_name": "sample.pdf",
                "content_type": "application/pdf",
                "file_size_bytes": 100,
            },
            {
                "file_name": "notes.docx",
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "file_size_bytes": 200,
            },
        ]
    )

    assert len(request.files) == 2


def test_upload_request_rejects_extension_mismatch():
    with pytest.raises(ValidationError):
        DocumentUploadUrlRequest(
            files=[
                {
                    "file_name": "sample.docx",
                    "content_type": "application/pdf",
                    "file_size_bytes": 100,
                }
            ]
        )


def test_upload_request_rejects_large_files():
    with pytest.raises(ValidationError):
        DocumentUploadUrlRequest(
            files=[
                {
                    "file_name": "large.pdf",
                    "content_type": "application/pdf",
                    "file_size_bytes": 10_485_761,
                }
            ]
        )


def test_process_request_rejects_overlap_larger_than_chunk_size():
    with pytest.raises(ValidationError):
        ProcessDocumentRequest(chunk_size=800, chunk_overlap=800)


def test_retrieval_request_validates_top_k_bounds():
    with pytest.raises(ValidationError):
        RetrievalQueryRequest(query="hello", top_k=0)

    with pytest.raises(ValidationError):
        RetrievalQueryRequest(query="hello", top_k=51)


def test_send_message_request_defaults_runtime_options():
    request = SendMessageRequest(input="Summarize this", document_ids=["doc_123"])

    assert request.runtime_options == RuntimeOptions()
    assert request.runtime_options.use_rag is True


def test_ask_compatibility_request_supports_optional_chat_id():
    request = AskCompatibilityRequest(query="What is this?", document_ids=["doc_123"])

    assert request.chat_id is None
    assert request.runtime_options.use_memory is True
