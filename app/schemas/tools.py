from typing import Any

from pydantic import Field

from app.schemas.base import PlatformModel


class ToolInvokeRequest(PlatformModel):
    tool_name: str = Field(min_length=1, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolInvokeResponse(PlatformModel):
    tool_name: str
    result: dict[str, Any]


class McpJsonRpcRequest(PlatformModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)
