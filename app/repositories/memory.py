from collections import defaultdict
from typing import Any
from uuid import UUID


class InMemoryStore:
    """Development-only store used before PostgreSQL is wired."""

    def __init__(self) -> None:
        self.users: dict[UUID, dict[str, Any]] = {}
        self.knowledge_bases: dict[UUID, dict[str, Any]] = {}
        self.documents: dict[UUID, dict[str, Any]] = {}
        self.processing_jobs: dict[UUID, dict[str, Any]] = {}
        self.chats: dict[UUID, dict[str, Any]] = {}
        self.messages: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
        self.runs: dict[UUID, dict[str, Any]] = {}
        self.prompts: dict[UUID, dict[str, Any]] = {}
        self.evaluation_datasets: dict[UUID, dict[str, Any]] = {}
        self.evaluation_cases: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
        self.evaluation_runs: dict[UUID, dict[str, Any]] = {}
        self.feedback: list[dict[str, Any]] = []


store = InMemoryStore()

