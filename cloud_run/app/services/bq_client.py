"""BigQuery client. In test mode returns canned rows; in prod uses google-cloud-bigquery."""
from __future__ import annotations
import logging
from typing import Any

from app.config import get_settings

log = logging.getLogger(__name__)
_client = None
_fake_rows: list[dict] = []


def init_bq():
    global _client
    s = get_settings()
    if s.test_mode:
        log.info("bq: test mode (no real client)")
        _client = None
        return
    try:
        from google.cloud import bigquery  # type: ignore
        _client = bigquery.Client(project=s.gcp_project)
        log.info("bq: real client project=%s", s.gcp_project)
    except Exception as e:
        log.warning("bq client init failed (%s) — disabling", e)
        _client = None


def set_fake_rows(rows: list[dict]):
    """Test hook — preload rows that query() will return."""
    global _fake_rows
    _fake_rows = list(rows)


def query(sql: str, params: dict | None = None) -> list[dict]:
    """Run a parameterised query and return list of dicts.
    In test mode returns the preloaded fake_rows regardless of SQL.
    """
    s = get_settings()
    if s.test_mode or _client is None:
        return list(_fake_rows)
    job_config = None
    if params:
        from google.cloud import bigquery  # type: ignore
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(k, _bq_type(v), v) for k, v in params.items()
            ]
        )
    rows = _client.query(sql, job_config=job_config).result()
    return [dict(r.items()) for r in rows]


def _bq_type(v: Any) -> str:
    if isinstance(v, bool): return "BOOL"
    if isinstance(v, int): return "INT64"
    if isinstance(v, float): return "FLOAT64"
    return "STRING"
