CREATE INDEX IF NOT EXISTS idx_app_knowledge_bases_user_id ON app_knowledge_bases(user_id);
CREATE INDEX IF NOT EXISTS idx_app_documents_user_kb ON app_documents(user_id, knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_app_processing_jobs_document ON app_processing_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_app_chunks_user_kb ON app_chunks(user_id, knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_app_chunks_document ON app_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_app_chats_user_updated ON app_chats(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_app_messages_chat_created ON app_messages(chat_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_app_runs_user_created ON app_runs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_app_runs_chat_created ON app_runs(chat_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_app_feedback_run ON app_feedback(run_id);
CREATE INDEX IF NOT EXISTS idx_app_chunks_search_vector ON app_chunks USING gin(search_vector);

-- Add an HNSW or IVFFLAT vector index after representative data is loaded.
-- Example:
-- CREATE INDEX idx_app_chunks_embedding_hnsw
-- ON app_chunks USING hnsw (embedding vector_cosine_ops);
