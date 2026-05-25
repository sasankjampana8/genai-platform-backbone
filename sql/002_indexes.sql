CREATE INDEX IF NOT EXISTS idx_knowledge_bases_user_id ON knowledge_bases(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_kb ON documents(user_id, knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_document ON processing_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_user_kb ON chunks(user_id, knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chats_user_updated ON chats(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_chat_created ON messages(chat_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_runs_user_created ON runs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_chat_created ON runs(chat_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_run ON feedback(run_id);
CREATE INDEX IF NOT EXISTS idx_chunks_search_vector ON chunks USING gin(search_vector);

-- Add an HNSW or IVFFLAT vector index after representative data is loaded.
-- Example:
-- CREATE INDEX idx_chunks_embedding_hnsw
-- ON chunks USING hnsw (embedding vector_cosine_ops);
