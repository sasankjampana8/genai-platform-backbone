from shared.orchestrator import decide_route


def test_route_rag_for_document_query():
    state = decide_route(
        {
            "query": "Summarize this document",
            "document_ids": ["doc_1"],
            "runtime_options": {"use_rag": True},
        }
    )
    assert state["route"] == "RAG"
    assert state["needs_rag"] is True


def test_route_hybrid_for_web_chart_query():
    state = decide_route(
        {
            "query": "Search latest numbers and plot a chart",
            "document_ids": [],
            "runtime_options": {"use_rag": False, "use_web": True, "allow_charts": True},
        }
    )
    assert state["route"] == "HYBRID"
    assert state["needs_web"] is True
    assert state["needs_chart"] is True
