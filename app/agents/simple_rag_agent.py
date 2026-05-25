from app.agents.base import AgentInput, AgentResult
from app.schemas.retrieval import RetrievalAnswerRequest, RetrievalOptions
from app.services.retrieval_service import RetrievalService


class SimpleRagAgent:
    name = "simple_rag_agent"

    def __init__(self) -> None:
        self.retrieval = RetrievalService()

    def run(self, agent_input: AgentInput) -> AgentResult:
        if not agent_input.knowledge_base_id:
            raise ValueError("knowledge_base_id is required for SimpleRagAgent.")
        response = self.retrieval.answer(
            agent_input.user_id,
            RetrievalAnswerRequest(
                chat_id=agent_input.chat_id,
                knowledge_base_id=agent_input.knowledge_base_id,
                query=agent_input.query,
                options=RetrievalOptions(**agent_input.runtime_options.get("retrieval", {})),
            ),
        )
        return AgentResult(
            answer=response.answer,
            citations=[citation.model_dump(mode="json") for citation in response.citations],
            trace={"run_id": str(response.run_id), "retrieval_strategy": response.retrieval.strategy},
        )
