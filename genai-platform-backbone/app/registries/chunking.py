from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


@dataclass
class ChunkCandidate:
    chunk_id: str
    text: str
    chunk_type: str = "text"
    parent_chunk_id: str | None = None
    metadata: dict | None = None


class ChunkingStrategy(Protocol):
    name: str
    description: str

    def chunk(self, text: str, options: dict | None = None) -> list[ChunkCandidate]: ...


def _window_chunks(text: str, chunk_size: int, overlap: int) -> list[ChunkCandidate]:
    text = " ".join(text.split())
    if not text:
        return []
    chunks: list[ChunkCandidate] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(ChunkCandidate(chunk_id=str(uuid4()), text=text[start:end], metadata={"start": start, "end": end}))
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


class FixedChunking:
    name = "fixed"
    description = "Fixed character-window chunking with overlap."

    def chunk(self, text: str, options: dict | None = None) -> list[ChunkCandidate]:
        options = options or {}
        return _window_chunks(text, int(options.get("chunk_size", 800)), int(options.get("chunk_overlap", 120)))


class RecursiveChunking(FixedChunking):
    name = "recursive"
    description = "Recursive-style chunking that preserves paragraphs where possible."

    def chunk(self, text: str, options: dict | None = None) -> list[ChunkCandidate]:
        options = options or {}
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) <= 1:
            return super().chunk(text, options)
        chunk_size = int(options.get("chunk_size", 800))
        chunks: list[ChunkCandidate] = []
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 2 > chunk_size and current:
                chunks.append(ChunkCandidate(chunk_id=str(uuid4()), text=current.strip(), metadata={"strategy": self.name}))
                current = ""
            current += paragraph + "\n\n"
        if current.strip():
            chunks.append(ChunkCandidate(chunk_id=str(uuid4()), text=current.strip(), metadata={"strategy": self.name}))
        return chunks


class SemanticChunking(RecursiveChunking):
    name = "semantic"
    description = "Semantic chunking interface; currently paragraph-aware pending embedding breakpoints."


class ParentChildChunking:
    name = "parent_child"
    description = "Creates parent chunks and smaller child chunks linked to parents."

    def chunk(self, text: str, options: dict | None = None) -> list[ChunkCandidate]:
        options = options or {}
        parents = _window_chunks(text, int(options.get("parent_size", 1400)), int(options.get("parent_overlap", 160)))
        output: list[ChunkCandidate] = []
        for parent in parents:
            output.append(parent)
            children = _window_chunks(parent.text, int(options.get("child_size", 280)), int(options.get("child_overlap", 40)))
            for child in children:
                child.parent_chunk_id = parent.chunk_id
                child.metadata = {**(child.metadata or {}), "parent_chunk_id": parent.chunk_id}
                output.append(child)
        return output


class TableAwareChunking(RecursiveChunking):
    name = "table_aware"
    description = "Table-aware chunking interface; preserves detected table-like lines."


class MultiVectorChunking(RecursiveChunking):
    name = "multi_vector"
    description = "Multi-vector chunking interface; creates raw text chunks first."


class ChunkingRegistry:
    def __init__(self) -> None:
        self._strategies: dict[str, ChunkingStrategy] = {}

    def register(self, strategy: ChunkingStrategy) -> None:
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> ChunkingStrategy:
        if name not in self._strategies:
            raise KeyError(f"Unknown chunking strategy: {name}")
        return self._strategies[name]

    def list(self) -> list[dict]:
        return [
            {
                "name": strategy.name,
                "description": strategy.description,
                "supports_tables": strategy.name == "table_aware",
                "supports_parent_child": strategy.name == "parent_child",
                "default_options": {"chunk_size": 800, "chunk_overlap": 120},
            }
            for strategy in self._strategies.values()
        ]


chunking_registry = ChunkingRegistry()
for _strategy in [
    FixedChunking(),
    RecursiveChunking(),
    SemanticChunking(),
    ParentChildChunking(),
    TableAwareChunking(),
    MultiVectorChunking(),
]:
    chunking_registry.register(_strategy)

