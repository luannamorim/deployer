from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from deployer.config import settings
from deployer.middleware.request_id import request_id_dispatch
from deployer.observability.logger import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(settings.log_level)
    logger.info(
        "application starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
    yield
    logger.info("application shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    # Middleware registered innermost-first; Starlette makes last-registered the outermost.
    app.middleware("http")(request_id_dispatch)
    return app


app = create_app()
