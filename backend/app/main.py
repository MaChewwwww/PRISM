import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.autonomous.worker import AutonomousWorker
from app.core.config import get_settings
from app.core.database import close_database, init_db
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db(settings.database_url)
    stop_event = asyncio.Event()
    worker_task: asyncio.Task[None] | None = None
    # Settings rejects this flag in staging. Keep the environment condition as
    # a second, local guard so a staging process can never instantiate the
    # order-capable worker if configuration validation changes in the future.
    if settings.autonomous_trading_enabled and settings.environment != "staging":
        worker_task = asyncio.create_task(AutonomousWorker(settings).run_forever(stop_event))
    yield
    if worker_task is not None:
        stop_event.set()
        await worker_task
    await close_database()


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
    allow_origins=get_settings().cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(router)
