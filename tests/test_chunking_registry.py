from app.registries.chunking import chunking_registry


def test_chunking_registry_lists_expected_strategies() -> None:
    names = {item["name"] for item in chunking_registry.list()}
    assert {"fixed", "recursive", "semantic", "parent_child", "table_aware", "multi_vector"} <= names


def test_parent_child_strategy_links_children() -> None:
    text = " ".join(["alpha beta gamma"] * 80)
    chunks = chunking_registry.get("parent_child").chunk(text, {"parent_size": 200, "child_size": 60})
    assert chunks
    assert any(chunk.parent_chunk_id for chunk in chunks)

