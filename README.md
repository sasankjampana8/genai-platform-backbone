# GenAI Platform Backbone

This subproject is a reusable GenAI backend platform designed for future agentic applications. It is intentionally separate from the existing CloudRAG Lambda implementation in the repository.

The platform is a modular monolith FastAPI service with clean routers, services, repositories, providers, registries, workers, migrations, and infrastructure. It is designed so future business workflows, including a LangGraph-based AI Systems Architect Copilot, can call the platform instead of owning ingestion, retrieval, tracing, and evaluation themselves.

This implementation is meant to be an independent reusable backend. LangGraph/LangChain agents should use this backbone for durable platform capabilities such as auth, knowledge bases, ingestion, retrieval, tracing, tools, and evaluation. Agent workflows remain swappable.

## Core Principles

- Keep the backend reusable across GenAI applications.
- Use FastAPI as one modular API service.
- Use Cognito for authentication.
- Use PostgreSQL for metadata and pgvector for embeddings.
- Use S3 for raw files, processed artifacts, traces, and exports.
- Use SQS for asynchronous processing and evaluation work.
- Use ECS/Fargate for the API service and workers.
- Use OpenAI for embeddings and generation.
- Use Amazon Bedrock only for Cohere reranking.
- Use registries for chunking and retrieval strategies.
- Do not let routers directly call OpenAI, S3, PostgreSQL, SQS, Bedrock, or Langfuse.

Required internal shape:

```text
Router -> Service -> Repository / Provider
```

## Current Implementation Status

This subproject currently provides real deployable infrastructure and real provider wiring for the core platform path:

- FastAPI application with versioned `/v1` routers.
- Pydantic request/response schemas.
- Service layer boundaries.
- PostgreSQL repository implementation for metadata, chats, runs, evals, and pgvector chunks.
- S3 provider for raw document storage.
- LiteLLM model gateway for OpenAI embeddings and chat models.
- Bedrock Cohere reranker provider with local fallback for tests.
- Cognito signup, confirmation, login, refresh, logout, and JWT-based request context.
- Chunking strategy registry.
- Retrieval strategy registry and real retrieval service for vector, hybrid RRF, query rewrite, HyDE, and adaptive modes.
- Context builder.
- Processing path for PDF/DOCX extraction, chunking, embedding, and pgvector indexing.
- Evaluation dataset/case upload and benchmark run APIs.
- Tool API plus an MCP-style JSON-RPC endpoint for `tools/list` and `tools/call`.
- Reusable `AgentRuntime` interface and `SimpleRagAgent` implementation.
- PostgreSQL/pgvector migration SQL.
- CloudFormation ECS/Fargate stack for the API, RDS, S3, SQS, Cognito, ALB, and Langfuse service.
- GitHub Actions deploy/destroy workflows.
- Local Langfuse Docker Compose file.
- Local smoke script.
- Unit tests for the registries and API envelope.

`MOCK_MODE=true` still exists for local tests, but deployed environments use real providers when the required AWS and model credentials are configured.

## Architecture

```text
Client / Swagger
  -> ALB
  -> ECS Fargate FastAPI service
  -> Services
  -> PostgreSQL / S3 / SQS / OpenAI / Bedrock / Langfuse

Document processing
  -> API-triggered inline processing for Swagger-friendly testing
  -> S3 raw files
  -> extraction
  -> chunk registry
  -> OpenAI embeddings
  -> PostgreSQL pgvector

Evaluation
  -> API-triggered benchmark runs for Swagger-friendly testing
  -> uploaded CSV/JSON cases
  -> retrieval + generation
  -> metrics persisted in PostgreSQL
```

## Local Setup

Create a virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

Minimum local mock-mode values:

```text
APP_ENV=local
MOCK_MODE=true
AUTH_DISABLED=true
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/genai_backbone
OPENAI_API_KEY=not-needed-in-mock-mode
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Open Swagger:

```text
http://localhost:8000/docs
```

Health check:

```bash
curl http://localhost:8000/health
```

## Environment Variables

Core:

```text
APP_NAME=GenAI Platform Backbone
APP_ENV=local
API_VERSION=v1
LOG_LEVEL=INFO
MOCK_MODE=false
AUTH_DISABLED=false
```

Database:

```text
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/genai_backbone
PGVECTOR_DIMENSION=1536
```

AWS:

```text
AWS_REGION=ap-south-1
S3_BUCKET=genai-platform-backbone-artifacts
PROCESSING_QUEUE_URL=
EVALUATION_QUEUE_URL=
COGNITO_USER_POOL_ID=
COGNITO_CLIENT_ID=
```

Models:

```text
OPENAI_API_KEY=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4.1-mini
BEDROCK_REGION=ap-south-1
BEDROCK_RERANK_MODEL_ID=cohere.rerank-v3-5:0
```

Observability:

```text
LANGFUSE_HOST=http://localhost:3001
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

Upload limits:

```text
MAX_UPLOAD_FILES=5
MAX_UPLOAD_FILE_SIZE_BYTES=10485760
```

## API Routers

### Auth

```text
POST /v1/auth/register
POST /v1/auth/confirm
POST /v1/auth/login
POST /v1/auth/refresh
POST /v1/auth/logout
```

### Profile

```text
POST /v1/profile
GET  /v1/profile
```

### Documents

```text
POST   /v1/documents/upload
GET    /v1/documents
GET    /v1/documents/{document_id}
DELETE /v1/documents/{document_id}
```

### Knowledge Bases

```text
POST /v1/knowledge-bases
GET  /v1/knowledge-bases
GET  /v1/knowledge-bases/{knowledge_base_id}
```

### Processing

```text
POST /v1/processing/jobs
GET  /v1/processing/jobs/{processing_job_id}
```

### Chunking Strategies

```text
GET /v1/chunking/strategies
```

### Retrieval

```text
POST /v1/retrieval/search
POST /v1/retrieval/answer
```

### Chats And Runs

```text
POST /v1/chats
GET  /v1/chats
POST /v1/chats/{chat_id}/messages
GET  /v1/runs/{run_id}
```

### Prompts

```text
POST /v1/prompts
POST /v1/prompts/{prompt_id}/versions
GET  /v1/prompts
```

### Evaluation

```text
POST /v1/evaluations/datasets
POST /v1/evaluations/datasets/{dataset_id}/cases
POST /v1/evaluations/datasets/{dataset_id}/cases/upload
POST /v1/evaluations/runs
GET  /v1/evaluations/runs/{evaluation_run_id}
```

### Tools And MCP-Style JSON-RPC

```text
GET  /v1/tools
POST /v1/tools/invoke
POST /v1/tools/mcp
```

### Observability

```text
POST /v1/observability/feedback
GET  /v1/observability/runs/{run_id}/trace
```

## Response Envelope

Success:

```json
{
  "request_id": "uuid",
  "status": "success",
  "data": {},
  "metadata": {
    "api_version": "v1",
    "timestamp": "2026-05-23T00:00:00Z"
  }
}
```

Error:

```json
{
  "request_id": "uuid",
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request.",
    "details": {}
  },
  "metadata": {
    "api_version": "v1",
    "timestamp": "2026-05-23T00:00:00Z"
  }
}
```

## Database Setup

Run migrations manually for local development:

```bash
psql "$DATABASE_URL" -f sql/001_init.sql
psql "$DATABASE_URL" -f sql/002_indexes.sql
```

The schema includes:

- users
- idempotency_keys
- knowledge_bases
- documents
- processing_jobs
- chunks
- chats
- messages
- runs
- prompts
- prompt_versions
- evaluation_datasets
- evaluation_cases
- evaluation_runs
- feedback

## Chunking Registry

Strategies are exposed through `app/registries/chunking.py`.

Current strategy names:

```text
fixed
recursive
semantic
parent_child
table_aware
multi_vector
```

Some advanced strategies currently use simplified logic internally. The interface is stable so implementations can improve without changing API contracts.

## Retrieval Registry

Strategies are exposed through `app/registries/retrieval.py`.

Current strategy names:

```text
vector
hybrid_rrf
query_rewrite
hyde
adaptive
```

Every retrieval query must filter by:

```text
user_id
knowledge_base_id
```

## Workers

Processing worker:

```bash
python -m app.workers.processing_worker
```

Evaluation worker:

```bash
python -m app.workers.evaluation_worker
```

Container commands:

```text
api: uvicorn app.main:app --host 0.0.0.0 --port 8000
processing-worker: python -m app.workers.processing_worker
evaluation-worker: python -m app.workers.evaluation_worker
```

## Langfuse

The AWS stack runs Langfuse as an ECS/Fargate service on the same load balancer using port `3001`.

After deployment, open:

```text
http://<load-balancer-dns>:3001
```

For local development, start Langfuse with Docker Compose.

Start local Langfuse:

```bash
cd langfuse
docker compose up -d
```

Then configure:

```text
LANGFUSE_HOST=http://localhost:3001
LANGFUSE_PUBLIC_KEY=<from-langfuse>
LANGFUSE_SECRET_KEY=<from-langfuse>
```

Telemetry failures must never fail user-facing APIs.

## CloudFormation

Stack template:

```text
infra/cloudformation/genai-platform-backbone.yaml
```

It is designed to create:

- VPC and subnets.
- ALB.
- ECS cluster.
- ECS service for the FastAPI API.
- ECS service for Langfuse.
- S3 artifact bucket.
- SQS processing and evaluation queues.
- RDS PostgreSQL.
- Cognito User Pool and User Pool Client.
- IAM roles.
- CloudWatch log groups.

The template is deployable for development, but you should review CIDR ranges, DB access, secrets, and IAM scoping before running it in AWS.

## GitHub Actions

Workflows:

```text
.github/workflows/deploy-genai-platform.yml
.github/workflows/destroy-genai-platform.yml
```

This branch is now a standalone backbone branch, so the workflows live at the repository root and will appear in GitHub Actions for this branch.

Expected secrets:

```text
AWS_GITHUB_DEPLOY_ROLE_ARN
OPENAI_API_KEY
DB_PASSWORD
LANGFUSE_PUBLIC_KEY
LANGFUSE_SECRET_KEY
```

Expected variables:

```text
AWS_REGION
GENAI_STACK_NAME
CONTAINER_IMAGE
```

Deploy workflow responsibilities:

1. Configure AWS credentials through GitHub OIDC.
2. Validate CloudFormation.
3. Deploy/update CloudFormation.
4. Print stack outputs.

The deploy workflow builds and pushes the container image, validates CloudFormation, deploys the stack, and prints outputs. Database migrations run at FastAPI startup when the service boots.

## Infrastructure Notes

The CloudFormation template creates an ECS/Fargate oriented stack, not the older Lambda RAG stack. It includes the cloud shape for the reusable platform:

- VPC, public subnets, internet gateway, route table.
- S3 artifact bucket.
- Processing and evaluation queues with DLQs for future async worker mode.
- Cognito user pool and app client.
- RDS PostgreSQL.
- ECS cluster, task role, execution role, API task definition, API service, Langfuse task definition, and Langfuse service.
- ALB, target group, listener.

Before running in AWS, review:

- `DatabasePassword`
- `OpenAIApiKey`
- `ContainerImage`
- VPC CIDR ranges
- RDS instance size
- IAM scope
- Whether RDS should be private-only with NAT/VPC endpoints

## Tests

Run:

```bash
pytest
```

Current tests cover:

- API envelope helpers.
- Chunking registry.
- Retrieval registry.
- Context builder.

## Remaining Hardening Work

Recommended next implementation order:

1. Add long-running ECS worker loops for SQS processing and evaluation queues.
2. Add full Langfuse trace emission from services and agent decorators.
3. Add a first LangGraph agent package that consumes `AgentRuntime`, retrieval, tools, and tracing.
4. Add hosted MCP transport if a standards-complete remote MCP server is required.
5. Replace lightweight built-in eval metrics with full DeepEval/RAGAS scoring jobs.
6. Add HTTPS/custom domain for API and Langfuse.
7. Move sensitive runtime values from CloudFormation parameters into Secrets Manager.

## Acceptance Criteria

The backbone is acceptable when:

- Swagger exposes all platform APIs.
- Cognito register/login flow works.
- User profile creation works.
- User can create a knowledge base.
- User can upload a PDF/DOCX through API multipart upload.
- Processing job is queued and completed by worker.
- Chunks and vectors are stored in pgvector.
- Retrieval search returns relevant chunks.
- Retrieval answer returns grounded answer with citations.
- Chat run creates trace metadata.
- Evaluation dataset/case/run flow works.
- Stack can deploy and destroy repeatedly.
