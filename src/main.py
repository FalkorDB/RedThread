"""RedThread — Graph-Powered Financial Investigation Platform.

Main FastAPI application entry point.
"""

from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError as RedisResponseError
from redis.exceptions import TimeoutError as RedisTimeoutError

from src.config import settings
from src.database.falkordb_client import db
from src.database.schema import setup_schema
from src.database.sqlite_client import sqlite_db

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="RedThread",
    description="Graph-Powered Financial Investigation Platform — Discover hidden connections, trace money flows, map fraud networks.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
def startup() -> None:
    """Initialize database connections and schema on startup."""
    logger.info("starting_redthread", host=settings.app_host, port=settings.app_port)
    try:
        db.connect()
        setup_schema(db)
        logger.info("falkordb_ready")
    except Exception as e:
        logger.error("falkordb_startup_failed", error=str(e))

    try:
        sqlite_db.connect()
        logger.info("sqlite_ready")
    except Exception as e:
        logger.error("sqlite_startup_failed", error=str(e))


@app.on_event("shutdown")
def shutdown() -> None:
    """Clean up connections on shutdown."""
    db.close()
    sqlite_db.close()
    logger.info("redthread_shutdown")


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    logger.warning("validation_error", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=422, content={"error": str(exc)})


@app.exception_handler(RedisResponseError)
async def redis_response_error_handler(request: Request, exc: RedisResponseError) -> JSONResponse:
    msg = str(exc)
    if "timed out" in msg.lower():
        logger.warning("query_timeout", path=request.url.path, error=msg)
        return JSONResponse(
            status_code=504,
            content={"error": "Query timed out — try reducing depth or scope"},
        )
    logger.error("redis_response_error", path=request.url.path, error=msg)
    return JSONResponse(status_code=502, content={"error": f"Graph query error: {msg}"})


@app.exception_handler(RedisConnectionError)
@app.exception_handler(RedisTimeoutError)
async def redis_connection_error_handler(
    request: Request, exc: RedisConnectionError | RedisTimeoutError
) -> JSONResponse:
    logger.error("redis_connection_error", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=503, content={"error": "FalkorDB is unavailable — please try again later"}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


# Register API routers
from src.api.analysis import router as analysis_router
from src.api.entities import router as entities_router
from src.api.export import router as export_router
from src.api.ingestion import router as ingestion_router
from src.api.investigations import router as investigations_router
from src.api.nlquery import router as nlquery_router
from src.api.relationships import router as relationships_router
from src.api.snapshots import router as snapshots_router
from src.api.temporal import router as temporal_router

app.include_router(entities_router)
app.include_router(relationships_router)
app.include_router(analysis_router)
app.include_router(investigations_router)
app.include_router(ingestion_router)
app.include_router(export_router)
app.include_router(temporal_router)
app.include_router(snapshots_router)
app.include_router(nlquery_router)


@app.get("/api/health")
def health_check() -> dict:
    """Application health check with graph statistics."""
    from src.database.schema import get_graph_stats

    falkordb_health = db.health_check()
    graph_stats = {}
    try:
        graph_stats = get_graph_stats(db)
    except Exception:
        pass

    return {
        "status": "healthy" if falkordb_health["status"] == "healthy" else "degraded",
        "falkordb": falkordb_health,
        "graph": graph_stats,
        "version": "0.1.0",
    }


@app.get("/", response_class=HTMLResponse)
def serve_ui() -> HTMLResponse:
    """Serve the main web UI."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(
        content="<h1>RedThread</h1><p>Static files not found. Run from project root.</p>"
    )
