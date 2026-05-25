from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.db import initialize_database
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger
from app.core.responses import error_payload

configure_logging()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Reusable GenAI platform backbone for ingestion, retrieval, chat, tracing, and evaluation.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/v1")

    @app.on_event("startup")
    def startup() -> None:
        if not settings.mock_mode:
            initialize_database()

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok", "environment": settings.app_env}

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=request_id,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("unhandled request failure request_id=%s", request_id)
        return JSONResponse(
            status_code=500,
            content=error_payload(
                code="INTERNAL_SERVER_ERROR",
                message="Internal server error.",
                request_id=request_id,
            ),
        )

    return app


app = create_app()
