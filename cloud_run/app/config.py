"""Centralised config loaded from env vars.

Env layers:
- Production (Cloud Run)  → values supplied via --set-env-vars in cloudbuild.yaml
- Local dev               → .env or shell exports; defaults below safe for tests
"""
from __future__ import annotations
import os
from functools import lru_cache
from typing import Literal


class Settings:
    # ── GCP ──────────────────────────────────────────────────────────────────
    gcp_project: str = os.getenv("GCP_PROJECT", "market-insight-dev")
    bq_dataset: str = os.getenv("BQ_DATASET", "food_data")
    bq_aggregated_table: str = os.getenv("BQ_AGG_TABLE", "aggregated_results")

    # ── Firebase / Firestore ─────────────────────────────────────────────────
    firebase_project: str = os.getenv("FIREBASE_PROJECT", gcp_project)
    firestore_emulator: str | None = os.getenv("FIRESTORE_EMULATOR_HOST")  # local dev

    # ── Auth ─────────────────────────────────────────────────────────────────
    jwt_audience: str = os.getenv("JWT_AUDIENCE", firebase_project)
    api_key_required: bool = os.getenv("API_KEY_REQUIRED", "false").lower() == "true"
    api_key_header: str = "X-API-Key"

    # ── Behaviour ────────────────────────────────────────────────────────────
    rate_limit_per_hour: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))
    cache_ttl_sec: int = int(os.getenv("CACHE_TTL_SEC", "300"))
    cors_origins: list[str] = (os.getenv("CORS_ORIGINS") or "*").split(",")

    # ── Test mode ────────────────────────────────────────────────────────────
    test_mode: bool = os.getenv("TEST_MODE", "false").lower() == "true"

    runtime: Literal["local", "cloudrun"] = (
        "cloudrun" if os.getenv("K_SERVICE") else "local"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
