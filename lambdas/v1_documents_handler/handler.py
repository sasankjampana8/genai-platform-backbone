from datetime import UTC, datetime

from pydantic import ValidationError as PydanticValidationError

from shared.api_response import error_response, success_response
from shared.config import settings
from shared.ids import generate_document_id, generate_process_id
from shared.logger import get_logger
from shared.pgvector_service import delete_document_chunks
from shared.repositories.document_repository import (
    get_document_for_user,
    get_process_job_for_user,
    list_documents_for_user,
    mark_document_deleted,
    put_document,
    put_process_job,
    update_document_status,
)
from shared.request_context import AuthError, build_request_context, get_request_id, parse_json_body
from shared.s3_service import create_presigned_post, delete_prefix, object_exists
from shared.schemas import DocumentUploadUrlRequest, ProcessDocumentRequest
from shared.sqs_service import send_processing_message
from shared.validation import sanitize_file_name

logger = get_logger(__name__)


def lambda_handler(event, context):
    request_id = get_request_id(event)
    route_key = event.get("routeKey", "")

    try:
        body = parse_json_body(event)
        request_context = build_request_context(event, body)
        path = event.get("pathParameters") or {}

        if route_key == "POST /v1/documents/upload-url":
            data = create_upload_urls(request_context.user_id, body)
        elif route_key == "GET /v1/documents":
            data = list_documents(request_context.user_id)
        elif route_key == "GET /v1/documents/{document_id}":
            data = get_document_detail(request_context.user_id, path.get("document_id"))
        elif route_key == "POST /v1/documents/{document_id}/process":
            data = start_processing(request_context.user_id, path.get("document_id"), body)
        elif route_key == "GET /v1/documents/{document_id}/processes/{process_id}":
            data = get_process_status(request_context.user_id, path.get("document_id"), path.get("process_id"))
        elif route_key == "DELETE /v1/documents/{document_id}":
            data = delete_document(request_context.user_id, path.get("document_id"))
        else:
            return error_response(
                request_id=request_id,
                code="NOT_FOUND",
                message="Document route not found.",
                status_code=404,
            )

        return success_response(data, request_id=request_context.request_id)
    except AuthError as exc:
        return error_response(request_id=request_id, code="UNAUTHORIZED", message=str(exc), status_code=401)
    except PydanticValidationError as exc:
        return error_response(
            request_id=request_id,
            code="VALIDATION_ERROR",
            message="Invalid request payload.",
            details={"errors": exc.errors()},
            status_code=422,
        )
    except ValueError as exc:
        return error_response(request_id=request_id, code="BAD_REQUEST", message=str(exc), status_code=400)
    except LookupError as exc:
        return error_response(request_id=request_id, code="NOT_FOUND", message=str(exc), status_code=404)
    except Exception:
        logger.exception("v1 document handler failed | request_id=%s", request_id)
        return error_response(
            request_id=request_id,
            code="INTERNAL_SERVER_ERROR",
            message="Internal server error.",
            status_code=500,
        )


def create_upload_urls(user_id: str, body: dict) -> dict:
    payload = DocumentUploadUrlRequest.model_validate(body)
    documents = []
    now = now_iso()

    for file_info in payload.files:
        document_id = generate_document_id()
        safe_file_name = sanitize_file_name(file_info.file_name)
        file_extension = safe_file_name.rsplit(".", 1)[-1].lower()
        s3_key = f"raw/{user_id}/{document_id}/{safe_file_name}"
        upload = create_presigned_post(s3_key, file_info.content_type)
        item = {
            "document_id": document_id,
            "user_id": user_id,
            "file_name": file_info.file_name,
            "safe_file_name": safe_file_name,
            "file_extension": file_extension,
            "content_type": file_info.content_type,
            "file_size_bytes": file_info.file_size_bytes,
            "s3_bucket": settings.RAW_BUCKET,
            "s3_key": s3_key,
            "upload_status": "PENDING_UPLOAD",
            "processing_status": "NOT_STARTED",
            "latest_process_id": None,
            "chunk_count": 0,
            "status": "ACTIVE",
            "created_at": now,
            "updated_at": now,
        }
        put_document(item)
        documents.append(
            {
                "document_id": document_id,
                "file_name": file_info.file_name,
                "s3_bucket": settings.RAW_BUCKET,
                "s3_key": s3_key,
                "upload_status": "PENDING_UPLOAD",
                "processing_status": "NOT_STARTED",
                "upload": upload,
            }
        )

    return {
        "documents": documents,
        "max_files": settings.MAX_FILES,
        "max_file_size_bytes": settings.MAX_FILE_SIZE_BYTES,
    }


def list_documents(user_id: str) -> dict:
    return {
        "documents": [document_summary(item) for item in list_documents_for_user(user_id)],
        "next_token": None,
    }


def get_document_detail(user_id: str, document_id: str | None) -> dict:
    document = require_document(user_id, document_id)
    exists = object_exists(document["s3_bucket"], document["s3_key"])
    if exists and document.get("upload_status") == "PENDING_UPLOAD":
        update_document_status(document["document_id"], upload_status="UPLOADED")
        document["upload_status"] = "UPLOADED"
    return {**document_summary(document), "s3_object_exists": exists}


def start_processing(user_id: str, document_id: str | None, body: dict) -> dict:
    document = require_document(user_id, document_id)
    payload = ProcessDocumentRequest.model_validate(body or {})
    if not object_exists(document["s3_bucket"], document["s3_key"]):
        raise ValueError("Document file has not been uploaded yet")

    process_id = generate_process_id()
    now = now_iso()
    job = {
        "process_id": process_id,
        "document_id": document["document_id"],
        "user_id": user_id,
        "status": "QUEUED",
        "stage": "QUEUED",
        "embedding_model": payload.embedding_model,
        "chunking_strategy": payload.chunking_strategy,
        "chunk_size": payload.chunk_size,
        "chunk_overlap": payload.chunk_overlap,
        "total_chunks": 0,
        "embedded_chunks": 0,
        "failed_chunks": 0,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }
    put_process_job(job)
    update_document_status(
        document["document_id"],
        upload_status="UPLOADED",
        processing_status="QUEUED",
        latest_process_id=process_id,
    )
    send_processing_message(
        {
            **job,
            "s3_bucket": document["s3_bucket"],
            "s3_key": document["s3_key"],
            "file_name": document["file_name"],
            "file_extension": document["file_extension"],
        }
    )
    return {
        "process_id": process_id,
        "document_id": document["document_id"],
        "status": "QUEUED",
        "message": "Document processing job has started.",
    }


def get_process_status(user_id: str, document_id: str | None, process_id: str | None) -> dict:
    if not document_id:
        raise ValueError("document_id path parameter is required")
    if not process_id:
        raise ValueError("process_id path parameter is required")
    require_document(user_id, document_id)
    job = get_process_job_for_user(process_id, document_id, user_id)
    if not job:
        raise LookupError("Process job not found")
    return {
        "process_id": job["process_id"],
        "document_id": job["document_id"],
        "status": job["status"],
        "stage": job.get("stage"),
        "total_chunks": int(job.get("total_chunks", 0)),
        "embedded_chunks": int(job.get("embedded_chunks", 0)),
        "failed_chunks": int(job.get("failed_chunks", 0)),
        "error_message": job.get("error_message"),
    }


def delete_document(user_id: str, document_id: str | None) -> dict:
    document = require_document(user_id, document_id)
    delete_document_chunks(user_id, document["document_id"])
    delete_prefix(settings.RAW_BUCKET, f"raw/{user_id}/{document['document_id']}/")
    delete_prefix(settings.RAW_BUCKET, f"processed/{user_id}/{document['document_id']}/")
    mark_document_deleted(document["document_id"])
    return {
        "document_id": document["document_id"],
        "status": "DELETED",
    }


def require_document(user_id: str, document_id: str | None) -> dict:
    if not document_id:
        raise ValueError("document_id path parameter is required")
    document = get_document_for_user(document_id, user_id)
    if not document:
        raise LookupError("Document not found")
    return document


def document_summary(document: dict) -> dict:
    return {
        "document_id": document["document_id"],
        "file_name": document["file_name"],
        "content_type": document.get("content_type"),
        "file_extension": document.get("file_extension"),
        "file_size_bytes": int(document.get("file_size_bytes", 0)),
        "s3_bucket": document.get("s3_bucket"),
        "s3_key": document.get("s3_key"),
        "upload_status": document.get("upload_status"),
        "processing_status": document.get("processing_status"),
        "latest_process_id": document.get("latest_process_id"),
        "chunk_count": int(document.get("chunk_count", 0)),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
    }


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
