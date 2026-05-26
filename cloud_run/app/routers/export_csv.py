"""CSV export — returns CSV text (Cloud Run signed URLs can replace Drive in Phase 3.6)."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
import csv
import io
import time

from app.auth import CurrentUser, get_current_user_or_api_key
from app.services.firestore_client import user_col
from app.services.search_engine import search_market_by_domain

router = APIRouter()


def _csv(rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    for r in rows: w.writerow(r)
    return "﻿" + buf.getvalue()


@router.get("/export-csv/search", response_class=PlainTextResponse)
async def export_search_csv(keyword: str = Query(...), topN: int = Query(50),
                            user: CurrentUser = Depends(get_current_user_or_api_key)):
    r = search_market_by_domain(user.user_id, keyword, topN)
    rows = [["rank", "brand_or_company", "type", "production_kg", "share_pct", "confidence"]]
    if r.get("tier") == 1:
        for i, b in enumerate(r.get("mapped_brands", []), 1):
            rows.append([i, b.get("display") or b.get("brand"), b.get("type", ""), b.get("kg", 0),
                         b.get("share", 0), b.get("confidence", "M")])
        for i, c in enumerate(r.get("unmapped", []), len(rows)):
            rows.append([i, c.get("company", ""), "unmapped", c.get("kg", 0), c.get("share", 0), "-"])
    else:
        for i, c in enumerate(r.get("topCompanies", []), 1):
            rows.append([i, c.get("company", ""), "tier0", c.get("kg", 0), c.get("share", 0), "-"])
    return PlainTextResponse(_csv(rows), media_type="text/csv; charset=utf-8")


@router.get("/export-csv/brand-mapping", response_class=PlainTextResponse)
async def export_brand_csv(user: CurrentUser = Depends(get_current_user_or_api_key)):
    rows = [["category", "brand", "display_name", "seller_keywords", "brand_keywords",
             "type", "DART_revenue_eok", "confidence"]]
    for d in user_col(user.user_id, "brand_mappings").stream():
        x = d.to_dict()
        rows.append([x.get("category", ""), x.get("brand", ""), x.get("display_name", ""),
                     x.get("seller_keywords", ""), x.get("brand_keywords", ""),
                     x.get("type", ""), x.get("DART_revenue_eok", ""), x.get("confidence", "")])
    return PlainTextResponse(_csv(rows), media_type="text/csv; charset=utf-8")


@router.get("/export-csv/category-mapping", response_class=PlainTextResponse)
async def export_category_csv(user: CurrentUser = Depends(get_current_user_or_api_key)):
    rows = [["tier", "category", "item_type_filter", "include_keywords",
             "exclude_keywords", "accuracy_basis"]]
    for d in user_col(user.user_id, "category_mappings").stream():
        x = d.to_dict()
        rows.append([x.get("tier", 1), x.get("category", ""), x.get("item_type_filter", ""),
                     x.get("include_keywords", ""), x.get("exclude_keywords", ""),
                     x.get("accuracy_basis", "")])
    return PlainTextResponse(_csv(rows), media_type="text/csv; charset=utf-8")


@router.get("/export-csv/monthly-snapshots", response_class=PlainTextResponse)
async def export_monthly_csv(monthsBack: int = Query(12),
                             user: CurrentUser = Depends(get_current_user_or_api_key)):
    from datetime import datetime, timedelta
    cutoff = (datetime.utcnow() - timedelta(days=monthsBack * 31)).strftime("%Y-%m")
    rows = [["month", "category", "brand", "production_kg", "mapping_coverage", "total_rows"]]
    for d in user_col(user.user_id, "monthly_snapshots").stream():
        x = d.to_dict()
        if str(x.get("month", "")) < cutoff: continue
        rows.append([x.get("month", ""), x.get("category", ""), x.get("brand", ""),
                     x.get("production_kg", 0), x.get("mapping_coverage", 0), x.get("total_rows", 0)])
    return PlainTextResponse(_csv(rows), media_type="text/csv; charset=utf-8")
