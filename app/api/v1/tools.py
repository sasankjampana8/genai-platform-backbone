from fastapi import APIRouter, Depends

from app.core.responses import success_payload
from app.core.security import AuthContext, get_auth_context
from app.schemas.tools import McpJsonRpcRequest, ToolInvokeRequest
from app.services.tool_service import ToolService

router = APIRouter()
service = ToolService()


@router.get("")
def list_tools(auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.list_tools())


@router.post("/invoke")
def invoke_tool(request: ToolInvokeRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.invoke(auth.user_id, request))


@router.post("/mcp")
def mcp_jsonrpc(request: McpJsonRpcRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return service.handle_mcp_jsonrpc(auth.user_id, request.model_dump())
