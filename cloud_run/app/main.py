"""FastAPI entry point. Wires routers, CORS, auth middleware, and a health probe."""
from __future__ import annotations
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import (
    search, analytics, pricing, market_size, history,
    favorites, brand_compare, export_csv, timeseries,
)
from app.services.firestore_client import init_firestore
from app.services.bq_client import init_bq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
log = logging.getLogger("market-insight")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firestore()
    init_bq()
    log.info("market-insight Cloud Run app started")
    yield
    log.info("market-insight Cloud Run app shutting down")


app = FastAPI(
    title="Market Insight API",
    version="0.1.0",
    description="Phase 3 multi-tenant SaaS port of the Apps Script v205 reference.",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    elapsed_ms = round((time.monotonic() - t0) * 1000)
    log.info(
        "%s %s -> %s (%dms) [%s]",
        request.method, request.url.path, response.status_code, elapsed_ms,
        request.headers.get("x-forwarded-for", "-"),
    )
    response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
    return response


@app.get("/health")
async def health():
    return {"ok": True, "service": "market-insight-api", "runtime": settings.runtime}


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    log.exception("unhandled at %s", request.url.path)
    return JSONResponse(status_code=500, content={"success": False, "error": str(exc)[:300]})


# Routers
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(pricing.router, prefix="/api", tags=["pricing"])
app.include_router(market_size.router, prefix="/api", tags=["pricing"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(favorites.router, prefix="/api", tags=["favorites"])
app.include_router(brand_compare.router, prefix="/api", tags=["compare"])
app.include_router(export_csv.router, prefix="/api", tags=["export"])
app.include_router(timeseries.router, prefix="/api", tags=["timeseries"])
