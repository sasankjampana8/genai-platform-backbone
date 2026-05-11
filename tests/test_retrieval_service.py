from shared.retrieval_service import _rerank_candidates, _select_diverse


def test_rerank_combines_vector_and_lexical_score():
    candidates = [
        {"chunk_id": "a", "document_id": "doc_1", "text": "unrelated text", "score": 0.8},
        {"chunk_id": "b", "document_id": "doc_1", "text": "alpha beta policy", "score": 0.7},
    ]
    ranked = _rerank_candidates("alpha beta", candidates)
    assert ranked[0]["chunk_id"] == "b"
    assert ranked[0]["retrieval_strategy"] == "vector_lexical_rerank"


def test_select_diverse_caps_per_document():
    candidates = [
        {"chunk_id": "a", "document_id": "doc_1", "score": 0.9},
        {"chunk_id": "b", "document_id": "doc_1", "score": 0.8},
        {"chunk_id": "c", "document_id": "doc_2", "score": 0.7},
    ]
    selected = _select_diverse(candidates, top_k=3, per_document_limit=1)
    assert [item["chunk_id"] for item in selected] == ["a", "c"]
