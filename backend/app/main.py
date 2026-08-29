from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import create_tables, init_db
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    # Initialize DB engine and session factory
    init_db(settings.database_url)
    # Auto-generate DB tables (cached models, etc.)
    try:
        await create_tables()
    except Exception as exc:
        import logging

        logger = logging.getLogger("app.main")
        logger.warning(
            f"Could not initialize database tables: {exc}. "
            "Skipping table creation (application will run but DB calls may fail)."
        )
    yield


app = FastAPI(
    title="PRISM API",
    version="0.1.0",
    description=(
        "PRISM: One signal. Multiple perspectives. Better decisions. "
        "Paper-only infrastructure API; execution is disabled by default."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(router)
