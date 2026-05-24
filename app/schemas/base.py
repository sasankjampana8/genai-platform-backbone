from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PlatformModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Metadata(PlatformModel):
    timestamp: datetime
    api_version: str = "v1"


class Envelope(PlatformModel, Generic[T]):
    request_id: UUID | str
    status: str = "success"
    data: T
    metadata: Metadata


class ErrorBody(PlatformModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(PlatformModel):
    request_id: UUID | str
    status: str = "error"
    error: ErrorBody
    metadata: Metadata

