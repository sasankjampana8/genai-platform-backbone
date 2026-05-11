from shared.api_response import utc_now_iso


def search_web(query: str, *, max_results: int = 3) -> dict:
    """Mock web/API tool with a stable shape for later replacement."""
    return {
        "tool": "mock_web_search",
        "query": query,
        "generated_at": utc_now_iso(),
        "results": [
            {
                "title": "Mock web result",
                "url": "https://example.com/mock-cloudrag-search",
                "snippet": (
                    "Web search is currently mocked. Replace shared.web_tool.search_web "
                    "with a real provider when external search is enabled."
                ),
            }
        ][:max_results],
    }


def build_web_context(result: dict) -> str:
    lines = []
    for index, item in enumerate(result.get("results", []), start=1):
        lines.append(f"[web:{index}] {item.get('title')} - {item.get('url')}\n{item.get('snippet')}")
    return "\n\n".join(lines)
