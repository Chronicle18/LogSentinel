"""LogSentinel FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.db import engine
from api.models.base import Base
from api.routes import ingest, jobs, events, validate, sourcetypes
from configs.loader import ConfigManager

log = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address)
config_manager: ConfigManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global config_manager
    config_dir = os.getenv("CONFIG_DIR", "./configs")
    config_manager = ConfigManager(config_dir)
    config_manager.start_watching()
    app.state.config_manager = config_manager
    log.info("app_startup", config_dir=config_dir,
             sourcetypes=list(config_manager.configs.keys()))
    yield
    config_manager.stop_watching()
    await engine.dispose()
    log.info("app_shutdown")


app = FastAPI(
    title="LogSentinel",
    description="Security Log Ingestion & Normalization Pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, tags=["Ingestion"])
app.include_router(jobs.router, tags=["Jobs"])
app.include_router(events.router, tags=["Events"])
app.include_router(validate.router, tags=["Validation"])
app.include_router(sourcetypes.router, tags=["Sourcetypes"])


@app.get("/health")
async def health():
    return {"status": "ok"}
