from fastapi import APIRouter

from app.api.v1 import (
    auth,
    chunking,
    chats,
    documents,
    evaluations,
    knowledge_bases,
    observability,
    processing,
    profile,
    prompts,
    retrieval,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(knowledge_bases.router, prefix="/knowledge-bases", tags=["knowledge-bases"])
api_router.include_router(processing.router, prefix="/processing", tags=["processing"])
api_router.include_router(chunking.router, prefix="/chunking", tags=["chunking"])
api_router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
api_router.include_router(chats.router, tags=["chats"])
api_router.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
api_router.include_router(observability.router, prefix="/observability", tags=["observability"])

