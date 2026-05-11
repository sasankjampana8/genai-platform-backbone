# CloudRAG Agent API Contract

This document defines the target `/v1` API contract for CloudRAG Agent.

CloudRAG is a single production-grade RAG chatbot. It uses OpenAI for embeddings and LLM calls, PostgreSQL pgvector for vector search, and AWS API Gateway, Lambda, S3, DynamoDB, SQS, and RDS for the serverless backend.

CloudRAG is not an agent-builder platform. The API uses `chat_id`, `message_id`, and `run_id`. It does not introduce agent publishing, agent versioning, or user-uploaded custom tool APIs.

## Versioning

All new APIs use the `/v1` prefix.

Existing Stage 1 APIs remain temporarily for compatibility:

```text
POST /documents/upload-url
GET  /documents/{document_id}
POST /documents/{document_id}/process
GET  /process/{process_id}/status
POST /retrieval/query
POST /ask
```

The target `/v1` flow is:

```text
login -> upload document -> process document -> create chat -> send message -> poll response -> inspect run trace
```

## Authentication

Target authentication uses Cognito.

All `/v1` routes require:

```http
Authorization: Bearer <access_token>
```

except:

```text
POST /v1/auth/signup
POST /v1/auth/confirm
POST /v1/auth/login
POST /v1/auth/refresh
POST /v1/auth/logout
```

After auth is enabled, protected APIs must derive `user_id` from JWT claims. Clients should not send `user_id` in protected request bodies. Local development may support `AUTH_DISABLED=true` with a fallback user id.

## Global Response Shape

Success:

```json
{
  "request_id": "req_xxx",
  "status": "success",
  "data": {},
  "metadata": {
    "timestamp": "2026-05-11T00:00:00Z",
    "api_version": "v1"
  }
}
```

Error:

```json
{
  "request_id": "req_xxx",
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request payload.",
    "details": {}
  },
  "metadata": {
    "timestamp": "2026-05-11T00:00:00Z",
    "api_version": "v1"
  }
}
```

Handlers should return a `request_id`, log with the same `request_id`, and never expose stack traces to clients.

## Auth APIs

### POST /v1/auth/signup

Creates a Cognito user.

Request:

```json
{
  "email": "test@example.com",
  "password": "TestPassword123!",
  "name": "Test User"
}
```

Response data:

```json
{
  "user_id": "cognito-sub-or-temp-id",
  "email": "test@example.com",
  "status": "CONFIRMATION_REQUIRED"
}
```

### POST /v1/auth/confirm

Confirms a new Cognito user.

Request:

```json
{
  "email": "test@example.com",
  "confirmation_code": "123456"
}
```

Response data:

```json
{
  "email": "test@example.com",
  "status": "CONFIRMED"
}
```

### POST /v1/auth/login

Authenticates a user and returns tokens.

Request:

```json
{
  "email": "test@example.com",
  "password": "TestPassword123!"
}
```

Response data:

```json
{
  "access_token": "...",
  "id_token": "...",
  "refresh_token": "...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

### POST /v1/auth/refresh

Refreshes access and id tokens.

Request:

```json
{
  "refresh_token": "..."
}
```

Response data:

```json
{
  "access_token": "...",
  "id_token": "...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

### POST /v1/auth/logout

Logs out a user.

Request:

```json
{
  "access_token": "..."
}
```

Response data:

```json
{
  "status": "LOGGED_OUT"
}
```

## Document APIs

Documents are scoped to the authenticated user.

### POST /v1/documents/upload-url

Creates document metadata and returns presigned S3 POST data. The file binary must upload directly to S3.

Request:

```json
{
  "files": [
    {
      "file_name": "policy.pdf",
      "content_type": "application/pdf",
      "file_size_bytes": 5242880
    }
  ]
}
```

Response data:

```json
{
  "documents": [
    {
      "document_id": "doc_xxx",
      "file_name": "policy.pdf",
      "s3_bucket": "cloudrag-mvp-rawdocumentsbucket-...",
      "s3_key": "raw/user_xxx/doc_xxx/policy.pdf",
      "upload_status": "PENDING_UPLOAD",
      "processing_status": "NOT_STARTED",
      "upload": {
        "url": "https://bucket.s3.ap-south-1.amazonaws.com/",
        "fields": {
          "key": "raw/user_xxx/doc_xxx/policy.pdf",
          "Content-Type": "application/pdf",
          "policy": "...",
          "x-amz-algorithm": "...",
          "x-amz-credential": "...",
          "x-amz-date": "...",
          "x-amz-signature": "..."
        }
      }
    }
  ],
  "max_files": 10,
  "max_file_size_bytes": 10485760
}
```

Allowed document types:

```text
application/pdf
application/vnd.openxmlformats-officedocument.wordprocessingml.document
```

### GET /v1/documents

Lists documents for the authenticated user.

Query parameters:

```text
status=optional
limit=optional
next_token=optional
```

Response data:

```json
{
  "documents": [
    {
      "document_id": "doc_xxx",
      "file_name": "policy.pdf",
      "upload_status": "UPLOADED",
      "processing_status": "COMPLETED",
      "chunk_count": 48,
      "created_at": "2026-05-11T00:00:00Z",
      "updated_at": "2026-05-11T00:05:00Z"
    }
  ],
  "next_token": null
}
```

### GET /v1/documents/{document_id}

Returns document metadata and confirms S3 object existence.

Response data:

```json
{
  "document_id": "doc_xxx",
  "file_name": "policy.pdf",
  "content_type": "application/pdf",
  "file_size_bytes": 5242880,
  "s3_bucket": "cloudrag-mvp-rawdocumentsbucket-...",
  "s3_key": "raw/user_xxx/doc_xxx/policy.pdf",
  "upload_status": "UPLOADED",
  "processing_status": "COMPLETED",
  "latest_process_id": "proc_xxx",
  "chunk_count": 48,
  "s3_object_exists": true
}
```

### POST /v1/documents/{document_id}/process

Starts async document processing.

Request:

```json
{
  "embedding_model": "text-embedding-3-small",
  "chunking_strategy": "recursive",
  "chunk_size": 800,
  "chunk_overlap": 120
}
```

Response data:

```json
{
  "process_id": "proc_xxx",
  "document_id": "doc_xxx",
  "status": "QUEUED",
  "message": "Document processing job has started."
}
```

### GET /v1/documents/{document_id}/processes/{process_id}

Returns processing status for a document process job.

Response data:

```json
{
  "process_id": "proc_xxx",
  "document_id": "doc_xxx",
  "status": "COMPLETED",
  "stage": "COMPLETED",
  "total_chunks": 48,
  "embedded_chunks": 48,
  "failed_chunks": 0,
  "error_message": null
}
```

### DELETE /v1/documents/{document_id}

Deletes or tombstones a document owned by the authenticated user.

Target behavior:

- Delete document metadata or mark it deleted.
- Delete raw/processed S3 objects if configured.
- Delete pgvector chunks for that `document_id`.
- Keep run/message citations historically available where appropriate.

Response data:

```json
{
  "document_id": "doc_xxx",
  "status": "DELETED"
}
```

## Retrieval API

### POST /v1/retrieval/query

Performs semantic retrieval only. This endpoint does not call the LLM.

Request:

```json
{
  "query": "What is this document about?",
  "document_ids": ["doc_xxx"],
  "top_k": 5,
  "similarity_threshold": 0.0
}
```

Response data:

```json
{
  "query": "What is this document about?",
  "results": [
    {
      "chunk_id": "chunk_xxx",
      "document_id": "doc_xxx",
      "file_name": "policy.pdf",
      "page_number": 3,
      "chunk_index": 12,
      "score": 0.84,
      "text": "Relevant chunk text..."
    }
  ]
}
```

Retrieval must always filter by authenticated `user_id`.

## Chat APIs

### POST /v1/chats

Creates a chat conversation.

Request:

```json
{
  "title": "My first chat"
}
```

Response data:

```json
{
  "chat_id": "chat_xxx",
  "title": "My first chat",
  "status": "ACTIVE",
  "created_at": "2026-05-11T00:00:00Z"
}
```

### GET /v1/chats

Lists chats for the authenticated user.

Query parameters:

```text
status=ACTIVE
limit=20
next_token=optional
```

Response data:

```json
{
  "chats": [
    {
      "chat_id": "chat_xxx",
      "title": "My first chat",
      "status": "ACTIVE",
      "message_count": 4,
      "last_message_preview": "Summarize this document...",
      "created_at": "2026-05-11T00:00:00Z",
      "updated_at": "2026-05-11T00:10:00Z"
    }
  ],
  "next_token": null
}
```

### GET /v1/chats/{chat_id}

Returns chat details.

Response data:

```json
{
  "chat_id": "chat_xxx",
  "title": "My first chat",
  "status": "ACTIVE",
  "message_count": 4,
  "last_message_preview": "Summarize this document...",
  "memory_summary": "The user is discussing an uploaded policy document.",
  "created_at": "2026-05-11T00:00:00Z",
  "updated_at": "2026-05-11T00:10:00Z"
}
```

### GET /v1/chats/{chat_id}/messages

Lists messages in a chat.

Query parameters:

```text
limit=50
next_token=optional
```

Response data:

```json
{
  "chat_id": "chat_xxx",
  "messages": [
    {
      "message_id": "msg_user_xxx",
      "role": "USER",
      "content": "Summarize this document.",
      "status": "COMPLETED",
      "run_id": "run_xxx",
      "created_at": "2026-05-11T00:01:00Z"
    },
    {
      "message_id": "msg_assistant_xxx",
      "role": "ASSISTANT",
      "content": "The document discusses...",
      "status": "COMPLETED",
      "run_id": "run_xxx",
      "citations": [],
      "artifacts": [],
      "created_at": "2026-05-11T00:01:08Z"
    }
  ],
  "next_token": null
}
```

### POST /v1/chats/{chat_id}/messages

Creates a user message, creates a run, and enqueues async runtime processing.

Request:

```json
{
  "input": "Summarize my uploaded document and create a chart if numeric data exists.",
  "document_ids": ["doc_xxx"],
  "runtime_options": {
    "use_rag": true,
    "use_memory": true,
    "use_web": false,
    "allow_charts": true
  }
}
```

Response data:

```json
{
  "chat_id": "chat_xxx",
  "message_id": "msg_xxx",
  "run_id": "run_xxx",
  "status": "QUEUED"
}
```

### GET /v1/chats/{chat_id}/messages/{message_id}/response

Polls for the assistant response generated from a user message.

Running response data:

```json
{
  "message_id": "msg_xxx",
  "status": "RUNNING",
  "answer": null,
  "citations": [],
  "artifacts": [],
  "run_id": "run_xxx"
}
```

Completed response data:

```json
{
  "message_id": "msg_xxx",
  "status": "COMPLETED",
  "answer": "The document discusses...",
  "citations": [
    {
      "chunk_id": "chunk_xxx",
      "document_id": "doc_xxx",
      "file_name": "policy.pdf",
      "page_number": 3,
      "score": 0.84
    }
  ],
  "artifacts": [
    {
      "artifact_id": "artifact_xxx",
      "artifact_type": "chart",
      "content_type": "image/png",
      "presigned_url": "https://..."
    }
  ],
  "run_id": "run_xxx"
}
```

Failed response data:

```json
{
  "message_id": "msg_xxx",
  "status": "FAILED",
  "answer": null,
  "error_message": "Runtime failed.",
  "run_id": "run_xxx"
}
```

## Memory APIs

Memory is scoped by authenticated user and chat.

### GET /v1/chats/{chat_id}/memory

Returns the chat memory summary and detailed memory records.

Response data:

```json
{
  "chat_id": "chat_xxx",
  "memory_summary": "The user is asking about their uploaded resume template.",
  "memories": [
    {
      "memory_id": "mem_xxx",
      "memory_type": "CONVERSATION_SUMMARY",
      "content": "The chat has focused on resume optimization.",
      "source_message_ids": ["msg_1", "msg_2"],
      "importance": 0.5,
      "created_at": "2026-05-11T00:10:00Z"
    }
  ]
}
```

### POST /v1/chats/{chat_id}/memory/summarize

Summarizes recent messages and stores memory.

Request:

```json
{
  "source_message_limit": 20
}
```

Response data:

```json
{
  "chat_id": "chat_xxx",
  "memory_id": "mem_xxx",
  "status": "CREATED"
}
```

## Run And Trace APIs

Runs describe one runtime execution for a user message.

### GET /v1/runs

Lists recent runs for the authenticated user.

Query parameters:

```text
chat_id=optional
status=optional
limit=20
next_token=optional
```

Response data:

```json
{
  "runs": [
    {
      "run_id": "run_xxx",
      "chat_id": "chat_xxx",
      "message_id": "msg_xxx",
      "status": "COMPLETED",
      "route": "RAG",
      "query_preview": "Summarize this document...",
      "answer_preview": "The document discusses...",
      "latency_ms": 2300,
      "input_tokens": 1200,
      "output_tokens": 350,
      "estimated_cost": 0.0012,
      "trace_id": "trace_xxx",
      "created_at": "2026-05-11T00:01:00Z"
    }
  ],
  "next_token": null
}
```

### GET /v1/runs/{run_id}

Returns run summary metadata.

Response data:

```json
{
  "run_id": "run_xxx",
  "chat_id": "chat_xxx",
  "message_id": "msg_xxx",
  "status": "COMPLETED",
  "route": "RAG",
  "latency_ms": 2300,
  "input_tokens": 1200,
  "output_tokens": 350,
  "estimated_cost": 0.0012,
  "trace_id": "trace_xxx",
  "trace_s3_key": "traces/user_xxx/run_xxx/trace.json",
  "error_message": null,
  "created_at": "2026-05-11T00:01:00Z",
  "updated_at": "2026-05-11T00:01:08Z"
}
```

### GET /v1/runs/{run_id}/trace

Returns the full trace JSON from S3.

Response data:

```json
{
  "trace_id": "trace_xxx",
  "run_id": "run_xxx",
  "chat_id": "chat_xxx",
  "message_id": "msg_xxx",
  "status": "COMPLETED",
  "spans": [
    {
      "span_id": "span_xxx",
      "parent_span_id": null,
      "name": "runtime_retrieval",
      "start_time": "2026-05-11T00:01:01Z",
      "end_time": "2026-05-11T00:01:02Z",
      "latency_ms": 240,
      "status": "success",
      "attributes": {
        "top_k": 5,
        "retrieved_chunks": 5
      }
    }
  ],
  "retrieved_chunks": [],
  "tool_calls": [],
  "artifacts": [],
  "errors": [],
  "final_answer_preview": "The document discusses...",
  "created_at": "2026-05-11T00:01:00Z"
}
```

## Observability APIs

These APIs expose lightweight operational summaries from DynamoDB run metadata and S3 traces.

### GET /v1/observability/summary

Response data:

```json
{
  "window": "24h",
  "total_runs": 42,
  "completed_runs": 39,
  "failed_runs": 3,
  "avg_latency_ms": 2100,
  "total_input_tokens": 32000,
  "total_output_tokens": 9000,
  "estimated_cost": 0.12,
  "routes": {
    "DIRECT": 8,
    "RAG": 30,
    "WEB": 0,
    "CHART": 1,
    "HYBRID": 3
  }
}
```

### GET /v1/observability/errors

Response data:

```json
{
  "errors": [
    {
      "run_id": "run_xxx",
      "chat_id": "chat_xxx",
      "message_id": "msg_xxx",
      "error_message": "OpenAI request failed.",
      "created_at": "2026-05-11T00:15:00Z"
    }
  ],
  "next_token": null
}
```

## Compatibility API

### POST /v1/ask

Compatibility wrapper over the chat/message runtime flow.

This endpoint should not keep separate answer-generation logic. It should:

1. Use an existing `chat_id` if provided, otherwise create a chat.
2. Create a user message.
3. Create a run.
4. Enqueue runtime processing.
5. Return queued metadata.

Request:

```json
{
  "chat_id": "chat_xxx",
  "query": "Summarize this document.",
  "document_ids": ["doc_xxx"],
  "runtime_options": {
    "use_rag": true,
    "use_memory": true,
    "use_web": false,
    "allow_charts": false
  }
}
```

Response data:

```json
{
  "chat_id": "chat_xxx",
  "message_id": "msg_xxx",
  "run_id": "run_xxx",
  "status": "QUEUED"
}
```

## Runtime Routing

The internal orchestrator should start rule-based.

Routes:

```text
DIRECT
RAG
WEB
CHART
HYBRID
```

Routing rules:

- Use `RAG` when `document_ids` are supplied or `runtime_options.use_rag=true`.
- Use `WEB` when `runtime_options.use_web=true` or the query asks for latest/current/news/search-style information.
- Use `CHART` when `runtime_options.allow_charts=true` and the query asks for a chart, plot, graph, or visualization.
- Use `DIRECT` when no retrieval or tools are needed.
- Use `HYBRID` when multiple routes apply.

Current implementation notes:

- The runtime worker uses a LangGraph-compatible state boundary with a safe fallback if LangGraph is not installed.
- RAG retrieval now expands beyond plain top-k vector search: vector candidate search, optional metadata filters, lexical reranking, per-document diversity, and parent-neighbor chunk context.
- The web/API tool is currently mocked behind `shared.web_tool.search_web`.
- The chart tool currently creates SVG chart artifacts in S3 behind `shared.chart_tool.create_chart_artifact`.
- Full run traces are stored under `traces/{user_id}/{run_id}/trace.json`.

## Storage Contract

S3:

```text
raw/{user_id}/{document_id}/{safe_file_name}
processed/{user_id}/{document_id}/extracted_text.json
processed/{user_id}/{document_id}/chunks.json
traces/{user_id}/{run_id}/trace.json
artifacts/{user_id}/{run_id}/{artifact_id}.svg
```

PostgreSQL pgvector remains the primary searchable vector store. Embeddings should not be stored in S3 as the primary vector store.

DynamoDB target tables:

```text
UsersTable
DocumentsTable
ProcessJobsTable
ChatsTable
MessagesTable
RunsTable
MemoryTable
ArtifactsTable optional
```

## Final Target API Flow

```text
1. POST /v1/auth/login
2. POST /v1/documents/upload-url
3. Upload file directly to S3
4. POST /v1/documents/{document_id}/process
5. GET /v1/documents/{document_id}/processes/{process_id}
6. POST /v1/retrieval/query
7. POST /v1/chats
8. POST /v1/chats/{chat_id}/messages
9. GET /v1/chats/{chat_id}/messages/{message_id}/response
10. GET /v1/runs/{run_id}/trace
11. GET /v1/observability/summary
```
