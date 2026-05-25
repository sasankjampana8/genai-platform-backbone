from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GenAI Platform Backbone"
    app_env: str = "local"
    api_version: str = "v1"
    log_level: str = "INFO"
    mock_mode: bool = False
    auth_disabled: bool = False
    inline_processing: bool = True

    aws_region: str = "ap-south-1"
    s3_bucket: str = "genai-platform-backbone-artifacts"
    processing_queue_url: str | None = None
    evaluation_queue_url: str | None = None

    cognito_user_pool_id: str | None = None
    cognito_client_id: str | None = None
    cognito_issuer: str | None = None

    database_url: str = "postgresql://postgres:postgres@localhost:5432/genai_backbone"
    pgvector_dimension: int = 1536

    openai_api_key: str | None = Field(default=None, repr=False)
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4.1-mini"
    llm_provider: str = "openai"

    bedrock_region: str = "ap-south-1"
    bedrock_rerank_model_id: str = "cohere.rerank-v3-5:0"
    enable_bedrock_rerank: bool = True

    langfuse_host: str | None = None
    langfuse_public_key: str | None = Field(default=None, repr=False)
    langfuse_secret_key: str | None = Field(default=None, repr=False)

    max_upload_files: int = 5
    max_upload_file_size_bytes: int = 10 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
