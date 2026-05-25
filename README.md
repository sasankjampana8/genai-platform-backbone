# GenAI Platform Backbone

GenAI Platform Backbone is a reusable backend foundation for building production-style GenAI applications and agentic systems. It provides the shared platform capabilities that most AI products need: authentication, knowledge bases, document ingestion, chunking, embeddings, retrieval, reranking, chat runs, tools, evaluation, and observability.

The idea is simple: agents and business workflows should be replaceable, but the platform services underneath them should be stable. A LangGraph or LangChain agent can use this backend for storage, retrieval, tracing, tools, and evaluation instead of rebuilding those pieces for every project.

This project is independent from the earlier CloudRAG Lambda MVP. It is designed as a standalone FastAPI service deployed on AWS ECS/Fargate.

## What This Project Does

- Provides Cognito-based user authentication.
- Stores user profile, knowledge base, document, chat, run, prompt, and evaluation metadata in PostgreSQL.
- Stores document chunks and embeddings in PostgreSQL with pgvector.
- Stores raw documents, traces, and artifacts in S3.
- Supports PDF and DOCX ingestion.
- Supports multiple chunking strategies through a registry.
- Supports multiple retrieval strategies through a registry.
- Uses LiteLLM as the model gateway.
- Uses OpenAI for chat and embedding models.
- Uses Amazon Bedrock Cohere rerank for reranking.
- Runs Langfuse as a deployed observability service.
- Exposes a versioned FastAPI API with Swagger.
- Includes GitHub Actions for deploy and destroy.
- Uses CloudFormation to create and delete the AWS stack.

## Architecture Summary

```text
User / Swagger / Client
  -> Application Load Balancer
  -> ECS Fargate FastAPI API
  -> Service Layer
  -> PostgreSQL / pgvector
  -> S3
  -> SQS
  -> Cognito
  -> OpenAI through LiteLLM
  -> Bedrock Cohere rerank
  -> Langfuse
```

The code follows this structure:

```text
Router -> Service -> Repository / Provider
```

Routers handle HTTP boundaries, services contain application logic, repositories handle PostgreSQL persistence, and providers wrap external systems such as S3, Cognito, OpenAI, Bedrock, SQS, and Langfuse.

## AWS Services Used

| Service | Purpose |
| --- | --- |
| Amazon ECS Fargate | Runs the FastAPI API service and Langfuse service as containers. |
| Application Load Balancer | Provides public HTTP access to the API and Langfuse. |
| Amazon ECR | Stores the Docker image built by GitHub Actions. |
| Amazon RDS PostgreSQL | Stores platform metadata and pgvector embeddings. |
| pgvector | Enables vector similarity search inside PostgreSQL. |
| Amazon S3 | Stores uploaded documents, processed artifacts, traces, and exports. |
| Amazon SQS | Provides processing and evaluation queues. |
| Amazon Cognito | Handles signup, confirmation, login, refresh, and JWT authentication. |
| Amazon Bedrock | Hosts Cohere rerank for retrieval reranking. |
| AWS CloudFormation | Creates and deletes the full infrastructure stack. |
| AWS IAM | Provides least-scoped roles for ECS tasks, GitHub Actions, and service access. |
| Amazon CloudWatch Logs | Stores container logs for the API and Langfuse. |

## Model Providers

The API uses LiteLLM as the model gateway.

Default model configuration:

```text
Embeddings: text-embedding-3-small
Chat:       gpt-4.1-mini
Rerank:     cohere.rerank-v3-5:0 through Amazon Bedrock
```

The model gateway keeps application code independent from direct SDK calls. Services call the gateway, and the gateway handles provider-specific details.

## Main Capabilities

### Authentication

Users sign up with email and password, confirm their email using a verification code, login, and receive tokens. Protected APIs use the Cognito access token.

### Knowledge Bases

A knowledge base groups uploaded documents and retrieval configuration. Documents, chunks, retrieval queries, and chat runs are scoped to a user and knowledge base.

### Document Ingestion

The document flow supports PDF and DOCX uploads. Uploaded files are saved to S3, metadata is saved to PostgreSQL, text is extracted, chunks are generated, embeddings are created, and chunks are stored in pgvector.

### Chunking

Chunking is strategy-based. The API can list available strategies and processing requests can select the strategy to use.

Current strategy names:

```text
fixed
recursive
semantic
parent_child
table_aware
multi_vector
```

### Retrieval

Retrieval is also strategy-based. This makes it easier to experiment with different retrieval methods without changing API contracts.

Current strategy names:

```text
vector
hybrid_rrf
query_rewrite
hyde
adaptive
```

Retrieval always filters by `user_id` and `knowledge_base_id`.

### Reranking

The retrieval layer supports reranking with Cohere rerank through Amazon Bedrock. This improves result ordering after the initial pgvector or hybrid search.

### Chat And Runs

Chat APIs create conversations and generate runs. A run stores the route, answer, citations, token usage, latency, and trace metadata.

### Tools And MCP-Style Endpoint

The tool layer exposes a normal REST interface and an MCP-style JSON-RPC endpoint. This gives future agents a clean way to list and call platform tools.

### Evaluation

Evaluation APIs support datasets, cases, CSV/JSON upload, and evaluation runs. This is useful for benchmarking retrieval and answer quality against known inputs and expected outputs.

### Observability

Langfuse runs as part of the AWS stack. The API can record trace metadata and feedback, while Langfuse provides the observability UI.

## Repository Layout

```text
app/
  api/v1/              FastAPI routers
  agents/              Reusable agent runtime interfaces
  core/                Config, DB, logging, errors, responses, security
  providers/           External provider wrappers
  registries/          Chunking and retrieval registries
  repositories/        SQL and in-memory repository implementations
  schemas/             Pydantic request/response models
  services/            Application services
  workers/             Processing and evaluation worker entrypoints

infra/cloudformation/
  genai-platform-backbone.yaml

sql/
  001_init.sql
  002_indexes.sql

.github/workflows/
  deploy-genai-platform.yml
  destroy-genai-platform.yml

langfuse/
  docker-compose.yml
```

## Database Schema

The application tables are prefixed with `app_` so they do not collide with Langfuse internal tables in the same PostgreSQL instance.

Main tables:

```text
app_users
app_idempotency_keys
app_knowledge_bases
app_documents
app_processing_jobs
app_chunks
app_chats
app_messages
app_runs
app_prompts
app_prompt_versions
app_evaluation_datasets
app_evaluation_cases
app_evaluation_runs
app_feedback
```

The `app_chunks` table stores `vector(1536)` embeddings for `text-embedding-3-small`.

## Local Setup

Create and activate a virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a local `.env` file:

```bash
cp .env.example .env
```

For local mock-mode testing:

```text
APP_ENV=local
MOCK_MODE=true
AUTH_DISABLED=true
INLINE_PROCESSING=true
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/genai_backbone
OPENAI_API_KEY=
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

Run tests:

```bash
pytest
```

## Local PostgreSQL Setup

Start PostgreSQL with pgvector locally, then create the database:

```bash
createdb genai_backbone
```

Run migrations:

```bash
psql "$DATABASE_URL" -f sql/001_init.sql
psql "$DATABASE_URL" -f sql/002_indexes.sql
```

The FastAPI service also applies these migrations at startup in deployed environments.

## Local Langfuse

Start Langfuse locally:

```bash
cd langfuse
docker compose up -d
```

Use:

```text
LANGFUSE_HOST=http://localhost:3001
LANGFUSE_PUBLIC_KEY=<langfuse-public-key>
LANGFUSE_SECRET_KEY=<langfuse-secret-key>
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
INLINE_PROCESSING=true
```

AWS:

```text
AWS_REGION=ap-south-1
S3_BUCKET=
PROCESSING_QUEUE_URL=
EVALUATION_QUEUE_URL=
```

Cognito:

```text
COGNITO_USER_POOL_ID=
COGNITO_CLIENT_ID=
COGNITO_ISSUER=
```

Database:

```text
DATABASE_URL=
PGVECTOR_DIMENSION=1536
```

Models:

```text
OPENAI_API_KEY=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4.1-mini
LLM_PROVIDER=openai
BEDROCK_REGION=ap-south-1
BEDROCK_RERANK_MODEL_ID=cohere.rerank-v3-5:0
ENABLE_BEDROCK_RERANK=true
```

Observability:

```text
LANGFUSE_HOST=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

Upload limits:

```text
MAX_UPLOAD_FILES=5
MAX_UPLOAD_FILE_SIZE_BYTES=10485760
```

## GitHub Secrets And Variables

The deploy workflow uses GitHub OIDC to assume an AWS IAM role. No long-term AWS access keys are needed in GitHub.

Repository secrets:

```text
AWS_GITHUB_DEPLOY_ROLE_ARN
OPENAI_API_KEY
DB_PASSWORD
LANGFUSE_NEXTAUTH_SECRET
LANGFUSE_SALT
```

Repository variables:

```text
AWS_REGION=ap-south-1
GENAI_STACK_NAME=genai-platform-backbone-dev
GENAI_ECR_REPOSITORY=genai-platform-backbone
```

## Deploy To AWS

Deployment is handled by:

```text
.github/workflows/deploy-genai-platform.yml
```

The workflow performs these steps:

1. Assumes the AWS deploy role through GitHub OIDC.
2. Resolves AWS account, region, ECR repository, and image URI.
3. Creates the ECR repository if it does not exist.
4. Builds and pushes the Docker image.
5. Validates the CloudFormation template.
6. Removes a previous `ROLLBACK_COMPLETE` stack if needed.
7. Deploys the CloudFormation stack.
8. Prints stack outputs.

Run it from:

```text
GitHub -> Actions -> Deploy GenAI Platform Backbone -> Run workflow
```

## AWS Stack Outputs

After deployment, CloudFormation prints:

```text
LoadBalancerUrl
LangfuseUrl
ArtifactBucketName
ProcessingQueueUrl
EvaluationQueueUrl
CognitoUserPoolId
CognitoClientId
DatabaseEndpoint
```

Open Swagger:

```text
<LoadBalancerUrl>/docs
```

Open Langfuse:

```text
<LangfuseUrl>
```

## Destroy AWS Resources

Destroy is handled by:

```text
.github/workflows/destroy-genai-platform.yml
```

Run it from:

```text
GitHub -> Actions -> Destroy GenAI Platform Backbone -> Run workflow
```

This deletes the CloudFormation stack and waits for deletion to complete.

## API Overview

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

### Knowledge Bases

```text
POST /v1/knowledge-bases
GET  /v1/knowledge-bases
GET  /v1/knowledge-bases/{knowledge_base_id}
```

### Documents

```text
POST   /v1/documents/upload
GET    /v1/documents
GET    /v1/documents/{document_id}
DELETE /v1/documents/{document_id}
```

### Processing

```text
POST /v1/processing/jobs
GET  /v1/processing/jobs/{processing_job_id}
```

### Chunking

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

### Evaluations

```text
POST /v1/evaluations/datasets
POST /v1/evaluations/datasets/{dataset_id}/cases
POST /v1/evaluations/datasets/{dataset_id}/cases/upload
POST /v1/evaluations/runs
GET  /v1/evaluations/runs/{evaluation_run_id}
```

### Tools

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

## Standard API Response

Success:

```json
{
  "request_id": "uuid",
  "status": "success",
  "data": {},
  "metadata": {
    "api_version": "v1",
    "timestamp": "2026-05-25T00:00:00Z"
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
    "timestamp": "2026-05-25T00:00:00Z"
  }
}
```

## End-To-End Test Flow

1. Open Swagger at `<LoadBalancerUrl>/docs`.
2. Register a user with `/v1/auth/register`.
3. Confirm the user with `/v1/auth/confirm`.
4. Login with `/v1/auth/login`.
5. Copy the access token.
6. Use Swagger authorization with `Bearer <access_token>`.
7. Create a profile with `/v1/profile`.
8. Create a knowledge base with `/v1/knowledge-bases`.
9. Upload a PDF or DOCX with `/v1/documents/upload`.
10. Start processing with `/v1/processing/jobs`.
11. Check processing status with `/v1/processing/jobs/{processing_job_id}`.
12. Search the knowledge base with `/v1/retrieval/search`.
13. Ask a grounded question with `/v1/retrieval/answer`.
14. Create a chat with `/v1/chats`.
15. Send a chat message with `/v1/chats/{chat_id}/messages`.
16. View the run with `/v1/runs/{run_id}`.
17. Open Langfuse to inspect traces and model activity.

## Mermaid Architecture Diagram

This diagram can be used as the starting point for a draw.io architecture diagram.

```mermaid
flowchart TB
    User["User / Swagger / Client"]
    ALB["Application Load Balancer"]
    API["ECS Fargate: FastAPI API"]
    Langfuse["ECS Fargate: Langfuse"]
    Cognito["Amazon Cognito"]
    S3["Amazon S3: Documents, Artifacts, Traces"]
    SQSProc["SQS Processing Queue"]
    SQSEval["SQS Evaluation Queue"]
    RDS["RDS PostgreSQL"]
    PGV["pgvector Embeddings"]
    ECR["Amazon ECR"]
    OpenAI["OpenAI via LiteLLM"]
    Bedrock["Amazon Bedrock: Cohere Rerank"]
    CW["CloudWatch Logs"]
    CFN["CloudFormation"]
    GHA["GitHub Actions"]

    User --> ALB
    ALB --> API
    ALB --> Langfuse

    API --> Cognito
    API --> S3
    API --> SQSProc
    API --> SQSEval
    API --> RDS
    RDS --> PGV
    API --> OpenAI
    API --> Bedrock
    API --> Langfuse
    API --> CW
    Langfuse --> RDS
    Langfuse --> CW

    GHA --> ECR
    GHA --> CFN
    CFN --> ALB
    CFN --> API
    CFN --> Langfuse
    CFN --> Cognito
    CFN --> S3
    CFN --> SQSProc
    CFN --> SQSEval
    CFN --> RDS
```

## High-Level Request Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Cognito
    participant S3
    participant DB as PostgreSQL + pgvector
    participant OpenAI
    participant Bedrock
    participant Langfuse

    Client->>API: Register / Login
    API->>Cognito: Create user / authenticate
    Cognito-->>API: JWT tokens
    Client->>API: Upload document with access token
    API->>S3: Store raw file
    API->>DB: Store document metadata
    Client->>API: Start processing
    API->>S3: Read document
    API->>OpenAI: Generate embeddings
    API->>DB: Store chunks and vectors
    Client->>API: Ask question
    API->>OpenAI: Embed query
    API->>DB: Vector / hybrid search
    API->>Bedrock: Rerank candidates
    API->>OpenAI: Generate grounded answer
    API->>Langfuse: Record trace
    API-->>Client: Answer, citations, run metadata
```
