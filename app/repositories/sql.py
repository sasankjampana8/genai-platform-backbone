from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, TYPE_CHECKING
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

from app.core.config import settings
from app.core.errors import NotFoundError

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool

_pool: "ConnectionPool | None" = None


def json_param(value: Any) -> Any:
    from psycopg.types.json import Jsonb

    return Jsonb(value)


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        _pool = ConnectionPool(settings.database_url, open=False, kwargs={"row_factory": dict_row})
        _pool.open()
    return _pool


@contextmanager
def get_connection() -> Iterator:
    with get_pool().connection() as conn:
        yield conn


def user_id_from_cognito_sub(cognito_sub: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"cognito:{cognito_sub}")


def vector_literal(values: list[float]) -> str:
    if not values:
        raise ValueError("Embedding vector cannot be empty.")
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"


class SqlRepository:
    def ensure_user(
        self,
        *,
        cognito_sub: str,
        email: str | None = None,
        display_name: str | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        user_id = user_id_from_cognito_sub(cognito_sub)
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO app_users (user_id, cognito_sub, email, display_name, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (cognito_sub) DO UPDATE
                SET email = COALESCE(EXCLUDED.email, app_users.email),
                    display_name = COALESCE(EXCLUDED.display_name, app_users.display_name),
                    status = EXCLUDED.status,
                    updated_at = now()
                RETURNING *
                """,
                (user_id, cognito_sub, email, display_name or email or "User", status),
            ).fetchone()
            conn.commit()
            return dict(row)

    def create_knowledge_base(self, *, user_id: UUID, name: str, description: str | None) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO app_knowledge_bases (user_id, name, description)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (user_id, name, description),
            ).fetchone()
            conn.commit()
            return dict(row)

    def list_knowledge_bases(self, user_id: UUID) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM app_knowledge_bases WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_knowledge_base(self, user_id: UUID, knowledge_base_id: UUID) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM app_knowledge_bases WHERE user_id = %s AND knowledge_base_id = %s",
                (user_id, knowledge_base_id),
            ).fetchone()
            if not row:
                raise NotFoundError("Knowledge base not found.")
            return dict(row)

    def create_document(self, item: dict[str, Any]) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO app_documents (
                    document_id, user_id, knowledge_base_id, file_name, content_type,
                    file_size_bytes, s3_key, status, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    item["document_id"],
                    item["user_id"],
                    item["knowledge_base_id"],
                    item["file_name"],
                    item["content_type"],
                    item["file_size_bytes"],
                    item["s3_key"],
                    item["status"],
                    json_param(item.get("metadata", {})),
                ),
            ).fetchone()
            conn.commit()
            return dict(row)

    def list_documents(self, user_id: UUID) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM app_documents WHERE user_id = %s AND status <> 'deleted' ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_document(self, user_id: UUID, document_id: UUID) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM app_documents WHERE user_id = %s AND document_id = %s AND status <> 'deleted'",
                (user_id, document_id),
            ).fetchone()
            if not row:
                raise NotFoundError("Document not found.")
            return dict(row)

    def update_document_status(self, user_id: UUID, document_id: UUID, status: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE app_documents SET status = %s, updated_at = now() WHERE user_id = %s AND document_id = %s",
                (status, user_id, document_id),
            )
            conn.commit()

    def create_processing_job(
        self,
        *,
        user_id: UUID,
        document_id: UUID,
        knowledge_base_id: UUID,
        chunking_strategy: str,
        embedding_model: str,
    ) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO app_processing_jobs (
                    user_id, document_id, knowledge_base_id, chunking_strategy, embedding_model
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, document_id, knowledge_base_id, chunking_strategy, embedding_model),
            ).fetchone()
            conn.commit()
            return dict(row)

    def get_processing_job(self, user_id: UUID, processing_job_id: UUID) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM app_processing_jobs WHERE user_id = %s AND processing_job_id = %s",
                (user_id, processing_job_id),
            ).fetchone()
            if not row:
                raise NotFoundError("Processing job not found.")
            return dict(row)

    def update_processing_job(self, processing_job_id: UUID, **fields: Any) -> None:
        allowed = {"status", "stage", "total_chunks", "error_message"}
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return
        assignments = ", ".join(f"{key} = %s" for key in updates)
        values = list(updates.values()) + [processing_job_id]
        with get_connection() as conn:
            conn.execute(
                f"UPDATE app_processing_jobs SET {assignments}, updated_at = now() WHERE processing_job_id = %s",
                values,
            )
            conn.commit()

    def delete_chunks_for_document(self, user_id: UUID, document_id: UUID) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM app_chunks WHERE user_id = %s AND document_id = %s", (user_id, document_id))
            conn.commit()

    def insert_chunks(self, chunks: list[dict[str, Any]]) -> int:
        if not chunks:
            return 0
        with get_connection() as conn:
            with conn.cursor() as cur:
                for chunk in chunks:
                    cur.execute(
                        """
                        INSERT INTO app_chunks (
                            chunk_id, user_id, document_id, knowledge_base_id, parent_chunk_id,
                            chunk_index, chunk_text, page_number, embedding, embedding_model,
                            chunking_strategy, metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s, %s, %s)
                        ON CONFLICT (chunk_id) DO NOTHING
                        """,
                        (
                            chunk["chunk_id"],
                            chunk["user_id"],
                            chunk["document_id"],
                            chunk["knowledge_base_id"],
                            chunk.get("parent_chunk_id"),
                            chunk["chunk_index"],
                            chunk["chunk_text"],
                            chunk.get("page_number"),
                            vector_literal(chunk["embedding"]),
                            chunk["embedding_model"],
                            chunk["chunking_strategy"],
                            json_param(chunk.get("metadata", {})),
                        ),
                    )
            conn.commit()
            return len(chunks)

    def vector_search(
        self,
        *,
        user_id: UUID,
        knowledge_base_id: UUID,
        query_embedding: list[float],
        top_k: int,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]:
        where = ["user_id = %s", "knowledge_base_id = %s", "embedding IS NOT NULL"]
        values: list[Any] = [user_id, knowledge_base_id]
        for key, value in (filters or {}).items():
            where.append("metadata ->> %s = %s")
            values.extend([key, str(value)])
        query_vector = vector_literal(query_embedding)
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT chunk_id, document_id, knowledge_base_id, chunk_text AS text,
                       page_number, metadata, 1 - (embedding <=> %s::vector) AS score
                FROM app_chunks
                WHERE {" AND ".join(where)}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                [query_vector] + values + [query_vector, top_k],
            ).fetchall()
            return [dict(row) for row in rows]

    def keyword_search(
        self,
        *,
        user_id: UUID,
        knowledge_base_id: UUID,
        query: str,
        top_k: int,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]:
        where = ["user_id = %s", "knowledge_base_id = %s", "search_vector @@ plainto_tsquery('english', %s)"]
        values: list[Any] = [user_id, knowledge_base_id, query]
        for key, value in (filters or {}).items():
            where.append("metadata ->> %s = %s")
            values.extend([key, str(value)])
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT chunk_id, document_id, knowledge_base_id, chunk_text AS text, page_number, metadata,
                       ts_rank_cd(search_vector, plainto_tsquery('english', %s)) AS score
                FROM app_chunks
                WHERE {" AND ".join(where)}
                ORDER BY score DESC
                LIMIT %s
                """,
                [query] + values + [top_k],
            ).fetchall()
            return [dict(row) for row in rows]

    def create_chat(self, *, user_id: UUID, title: str, knowledge_base_id: UUID | None) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                "INSERT INTO app_chats (user_id, title, knowledge_base_id) VALUES (%s, %s, %s) RETURNING *",
                (user_id, title, knowledge_base_id),
            ).fetchone()
            conn.commit()
            return dict(row)

    def list_chats(self, user_id: UUID) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM app_chats WHERE user_id = %s ORDER BY updated_at DESC", (user_id,)).fetchall()
            return [dict(row) for row in rows]

    def get_chat(self, user_id: UUID, chat_id: UUID) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM app_chats WHERE user_id = %s AND chat_id = %s", (user_id, chat_id)).fetchone()
            if not row:
                raise NotFoundError("Chat not found.")
            return dict(row)

    def create_message(self, *, user_id: UUID, chat_id: UUID, role: str, content: str, metadata: dict | None = None) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO app_messages (user_id, chat_id, role, content, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, chat_id, role, content, json_param(metadata or {})),
            ).fetchone()
            conn.execute("UPDATE app_chats SET updated_at = now() WHERE chat_id = %s", (chat_id,))
            conn.commit()
            return dict(row)

    def create_run(self, item: dict[str, Any]) -> dict[str, Any]:
        run_id = item.get("run_id") or uuid4()
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO app_runs (
                    run_id, user_id, chat_id, message_id, status, route, answer,
                    citations, trace_s3_key, latency_ms, token_usage, error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    run_id,
                    item["user_id"],
                    item.get("chat_id"),
                    item.get("message_id"),
                    item.get("status", "completed"),
                    item.get("route"),
                    item.get("answer"),
                    json_param(item.get("citations", [])),
                    item.get("trace_s3_key"),
                    item.get("latency_ms"),
                    json_param(item.get("token_usage", {})),
                    item.get("error_message"),
                ),
            ).fetchone()
            conn.commit()
            return dict(row)

    def get_run(self, user_id: UUID, run_id: UUID) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM app_runs WHERE user_id = %s AND run_id = %s", (user_id, run_id)).fetchone()
            if not row:
                raise NotFoundError("Run not found.")
            return dict(row)

    def create_evaluation_dataset(self, *, user_id: UUID, name: str, description: str | None) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                "INSERT INTO app_evaluation_datasets (user_id, name, description) VALUES (%s, %s, %s) RETURNING *",
                (user_id, name, description),
            ).fetchone()
            conn.commit()
            return dict(row)

    def create_evaluation_case(
        self,
        *,
        dataset_id: UUID,
        query: str,
        expected_answer: str | None,
        expected_citations: list[str] | None = None,
    ) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO app_evaluation_cases (dataset_id, query, expected_answer, expected_citations)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (dataset_id, query, expected_answer, json_param(expected_citations or [])),
            ).fetchone()
            conn.commit()
            return dict(row)

    def list_evaluation_cases(self, dataset_id: UUID) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM app_evaluation_cases WHERE dataset_id = %s ORDER BY created_at ASC",
                (dataset_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def create_evaluation_run(
        self,
        *,
        user_id: UUID,
        dataset_id: UUID,
        knowledge_base_id: UUID,
        status: str,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO app_evaluation_runs (user_id, dataset_id, knowledge_base_id, status, metrics)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, dataset_id, knowledge_base_id, status, json_param(metrics)),
            ).fetchone()
            conn.commit()
            return dict(row)

    def get_evaluation_run(self, user_id: UUID, evaluation_run_id: UUID) -> dict[str, Any]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM app_evaluation_runs WHERE user_id = %s AND evaluation_run_id = %s",
                (user_id, evaluation_run_id),
            ).fetchone()
            if not row:
                raise NotFoundError("Evaluation run not found.")
            return dict(row)


repository = SqlRepository()
