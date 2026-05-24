from fastapi import APIRouter

from app.core.responses import success_payload
from app.registries.chunking import chunking_registry

router = APIRouter()


@router.get("/strategies")
def list_chunking_strategies() -> dict:
    return success_payload({"strategies": chunking_registry.list()})

