from uuid import UUID

from app.schemas.retrieval import RetrievalAnswerRequest, RetrievalSearchRequest
from app.schemas.tools import ToolInvokeRequest, ToolInvokeResponse
from app.services.retrieval_service import RetrievalService


class ToolService:
    def __init__(self) -> None:
        self.retrieval = RetrievalService()

    def list_tools(self) -> dict:
        return {
            "tools": [
                {
                    "name": "kb.search",
                    "description": "Search a knowledge base using the configured retrieval strategy.",
                    "input_schema": {
                        "type": "object",
                        "required": ["knowledge_base_id", "query"],
                        "properties": {
                            "knowledge_base_id": {"type": "string", "format": "uuid"},
                            "query": {"type": "string"},
                            "filters": {"type": "object"},
                            "options": {"type": "object"},
                        },
                    },
                },
                {
                    "name": "kb.answer",
                    "description": "Generate a grounded answer from knowledge-base retrieval.",
                    "input_schema": {
                        "type": "object",
                        "required": ["knowledge_base_id", "query"],
                        "properties": {
                            "knowledge_base_id": {"type": "string", "format": "uuid"},
                            "query": {"type": "string"},
                            "filters": {"type": "object"},
                            "options": {"type": "object"},
                        },
                    },
                },
            ]
        }

    def invoke(self, user_id: UUID, request: ToolInvokeRequest) -> ToolInvokeResponse:
        if request.tool_name == "kb.search":
            result = self.retrieval.search(user_id, RetrievalSearchRequest(**request.arguments))
            return ToolInvokeResponse(tool_name=request.tool_name, result=result.model_dump(mode="json"))
        if request.tool_name == "kb.answer":
            result = self.retrieval.answer(user_id, RetrievalAnswerRequest(**request.arguments))
            return ToolInvokeResponse(tool_name=request.tool_name, result=result.model_dump(mode="json"))
        raise ValueError(f"Unknown tool: {request.tool_name}")

    def handle_mcp_jsonrpc(self, user_id: UUID, payload: dict) -> dict:
        method = payload.get("method")
        request_id = payload.get("id")
        if method == "tools/list":
            tools = self.list_tools()["tools"]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
        if method == "tools/call":
            params = payload.get("params") or {}
            result = self.invoke(
                user_id,
                ToolInvokeRequest(tool_name=params.get("name", ""), arguments=params.get("arguments") or {}),
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "json", "json": result.result}]}}
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Unsupported method: {method}"},
        }
