from uuid import UUID, uuid4

from app.providers.model_gateway import MockModelGateway
from app.registries.retrieval import retrieval_registry
from app.repositories.memory import store
from app.schemas.retrieval import Citation, RetrievalAnswerRequest, RetrievalAnswerResponse, RetrievalSearchRequest, RetrievalSearchResponse
from app.services.context_builder import ContextBuilder


class RetrievalService:
    def __init__(self) -> None:
        self.context_builder = ContextBuilder()
        self.model_gateway = MockModelGateway()

    def search(self, user_id: UUID, request: RetrievalSearchRequest) -> RetrievalSearchResponse:
        strategy = retrieval_registry.get(request.options.strategy)
        return strategy.search(user_id, request)

    def answer(self, user_id: UUID, request: RetrievalAnswerRequest) -> RetrievalAnswerResponse:
        retrieval = self.search(user_id, request)
        context = self.context_builder.build(retrieval.results)
        response = self.model_gateway.generate_answer(
            [
                {"role": "system", "content": self.context_builder.system_prompt()},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {request.query}"},
            ]
        )
        run_id = uuid4()
        citations = [
            Citation(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                page_number=item.page_number,
                score=item.score,
            )
            for item in retrieval.results
        ]
        store.runs[run_id] = {
            "run_id": run_id,
            "user_id": user_id,
            "status": "completed",
            "answer": response["content"],
            "citations": [item.model_dump() for item in citations],
        }
        return RetrievalAnswerResponse(answer=response["content"], citations=citations, run_id=run_id, retrieval=retrieval)

