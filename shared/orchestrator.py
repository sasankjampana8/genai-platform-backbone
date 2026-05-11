from typing import TypedDict


class AgentState(TypedDict, total=False):
    user_id: str
    chat_id: str
    message_id: str
    run_id: str
    query: str
    document_ids: list[str]
    runtime_options: dict
    route: str
    needs_rag: bool
    needs_web: bool
    needs_chart: bool


WEB_KEYWORDS = {"latest", "current", "today", "news", "web", "search", "internet"}
CHART_KEYWORDS = {"chart", "plot", "graph", "visualize", "bar chart", "line chart"}


def decide_route(state: AgentState) -> AgentState:
    query = (state.get("query") or "").lower()
    options = state.get("runtime_options") or {}
    document_ids = state.get("document_ids") or []
    needs_rag = bool(options.get("use_rag", True) and (document_ids or options.get("use_rag")))
    needs_web = bool(options.get("use_web") or any(keyword in query for keyword in WEB_KEYWORDS))
    needs_chart = bool(options.get("allow_charts") and any(keyword in query for keyword in CHART_KEYWORDS))

    active = [name for name, enabled in {"RAG": needs_rag, "WEB": needs_web, "CHART": needs_chart}.items() if enabled]
    route = active[0] if len(active) == 1 else "HYBRID" if active else "DIRECT"
    return {
        **state,
        "route": route,
        "needs_rag": needs_rag,
        "needs_web": needs_web,
        "needs_chart": needs_chart,
    }


def build_langgraph_app():
    """Return a tiny LangGraph app when installed, otherwise a compatible callable.

    This keeps local tests and Lambda packaging resilient while preserving the
    LangGraph boundary for the production runtime.
    """
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(AgentState)
        graph.add_node("route", decide_route)
        graph.set_entry_point("route")
        graph.add_edge("route", END)
        return graph.compile()
    except Exception:
        return lambda state: decide_route(state)


def plan_runtime(state: AgentState) -> AgentState:
    app = build_langgraph_app()
    if callable(app):
        return app(state)
    return app.invoke(state)
