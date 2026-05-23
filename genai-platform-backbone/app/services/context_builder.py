from app.schemas.retrieval import RetrievedChunk


class ContextBuilder:
    def build(self, chunks: list[RetrievedChunk]) -> str:
        lines: list[str] = []
        for index, chunk in enumerate(chunks, 1):
            page = f"page {chunk.page_number}" if chunk.page_number else "page unknown"
            lines.append(
                f"[{index}] document_id={chunk.document_id} chunk_id={chunk.chunk_id} {page}\n{chunk.text}"
            )
        return "\n\n".join(lines)

    def system_prompt(self) -> str:
        return (
            "You are a grounded GenAI platform assistant. Answer only from provided context. "
            "If the context is insufficient, say that the available sources do not contain enough information."
        )

