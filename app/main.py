from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, health, omi_tools, omi_webhooks, setup
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger, get_request_id, new_request_id

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("app_started", env=settings.app_env)
    yield
    logger.info("app_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        new_request_id()
        response = await call_next(request)
        response.headers["X-Request-ID"] = get_request_id()
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled_error", path=str(request.url.path), error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )

    app.include_router(health.router)
    app.include_router(setup.router)
    app.include_router(omi_webhooks.router)
    app.include_router(omi_tools.router)
    app.include_router(admin.router)

    if settings.legacy_omi_routes:
        app.include_router(omi_webhooks.legacy_router)

    return app


app = create_app()
