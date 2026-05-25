from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID


@dataclass
class AgentInput:
    user_id: UUID
    query: str
    knowledge_base_id: UUID | None = None
    chat_id: UUID | None = None
    runtime_options: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)


class AgentRuntime(Protocol):
    name: str

    def run(self, agent_input: AgentInput) -> AgentResult: ...
