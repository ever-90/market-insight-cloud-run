"""Tier-based search engine — Python port of v205 _searchByCategory_ / _searchByKeyword_.

User isolation: every read/write keyed by user_id (Firestore subcollections).
BigQuery layer is read-only and shared (production data is public).
"""
from __future__ import annotations
import logging
import re
import time
from typing import Any

from app.config import get_settings
from app.services.firestore_client import db, user_col
from app.services import bq_client

log = logging.getLogger(__name__)


_norm_ws = re.compile(r"\s+")
def _norm(s: str) -> str:
    return _norm_ws.sub("", (s or "").lower())


def _split_pipe(s: str) -> list[str]:
    return [_norm(t) for t in (s or "").split("|") if t.strip()]


def _load_category_mappings(user_id: str) -> list[dict]:
    return [d.to_dict() for d in user_col(user_id, "category_mappings").stream()]


def _load_brand_mappings(user_id: str, category: str | None = None) -> list[dict]:
    q = user_col(user_id, "brand_mappings")
    if category:
        q = q.where("category", "==", category)
    return [d.to_dict() for d in q.stream()]


def match_category(user_id: str, keyword: str) -> dict | None:
    """v205 _matchCategory_ port — bidirectional substring match."""
    kw = _norm(keyword)
    if not kw:
        return None
    for cat in _load_category_mappings(user_id):
        cat_norm = _norm(cat.get("category", ""))
        if kw == cat_norm:
            return cat
        includes = _split_pipe(cat.get("포함_키워드") or cat.get("include_keywords") or "")
        if any(kw and (kw in inc or inc in kw) for inc in includes if inc):
            return cat
    return None


def _fetch_production_rows(keywords: list[str]) -> list[dict]:
    """Calls BigQuery aggregated_results joined with brand_mapping.

    In test mode, bq_client returns the canned rows. SQL kept simple — production
    pipeline can substitute a more efficient parameterised version.
    """
    if not keywords:
        return []
    placeholders = " OR ".join(
        [f"REGEXP_CONTAINS(LOWER(REPLACE(product_name, ' ', '')), @kw{i})"
         for i, _ in enumerate(keywords)]
    )
    s = get_settings()
    sql = f"""
        SELECT report_no, product_name AS name, company, item_type AS type,
               kg_2024 AS kg24, kg_2023 AS kg23, kg_2022 AS kg22
        FROM `{s.gcp_project}.{s.bq_dataset}.{s.bq_aggregated_table}`
        WHERE kg_2024 > 0 AND ({placeholders})
        LIMIT 50000
    """
    params = {f"kw{i}": kw for i, kw in enumerate(keywords)}
    return bq_client.query(sql, params)


def search_by_category(user_id: str, cfg: dict, top_n: int = 10) -> dict:
    bq_t0 = time.monotonic()
    brands = _load_brand_mappings(user_id, cfg["category"])
    include = _split_pipe(cfg.get("포함_키워드") or cfg.get("include_keywords") or "")
    exclude = _split_pipe(cfg.get("제외_키워드") or cfg.get("exclude_keywords") or "")
    item_type_filter = _norm(cfg.get("item_type_filter", ""))

    # Expand BQ pull keywords with brand_keywords (v202c fix)
    bq_kws = list(include)
    for b in brands:
        for k in _split_pipe(b.get("brand_keywords", "")):
            if k and k not in bq_kws:
                bq_kws.append(k)

    all_rows = _fetch_production_rows(bq_kws)
    bq_call_ms = round((time.monotonic() - bq_t0) * 1000)

    all_brand_kws = [k for b in brands for k in _split_pipe(b.get("brand_keywords", ""))]

    def passes_filter(p: dict) -> bool:
        nm = _norm(p.get("name", ""))
        ty = _norm(p.get("type", ""))
        hit_inc = any(k in nm for k in include if k)
        hit_br = any(k in nm for k in all_brand_kws if k)
        if not (hit_inc or hit_br):
            return False
        if exclude and any(k in nm for k in exclude if k):
            return False
        if item_type_filter and item_type_filter not in ty:
            return False
        return True

    prods = [p for p in all_rows if passes_filter(p)]
    agg: dict[str, dict] = {b["brand"]: {"b": b, "kg": 0.0, "rows": 0} for b in brands}
    unm: dict[str, float] = {}
    total_kg = 0.0
    for p in prods:
        kg = float(p.get("kg24") or 0)
        total_kg += kg
        nm = _norm(p.get("name", ""))
        co = str(p.get("company", "") or "(미상)")
        hit = None
        for b in brands:
            in_b = any(k in nm for k in _split_pipe(b.get("brand_keywords", "")))
            in_c = any(k in co for k in (b.get("영업자_keywords") or "").split("|") if k.strip())
            if in_b or in_c:
                hit = b["brand"]; break
        if hit:
            agg[hit]["kg"] += kg
            agg[hit]["rows"] += 1
        else:
            unm[co] = unm.get(co, 0.0) + kg

    mapped = [
        {
            "brand": v["b"]["brand"],
            "display": v["b"].get("display_name") or v["b"]["brand"],
            "type": v["b"].get("type", ""),
            "dart": v["b"].get("DART_revenue_eok") or v["b"].get("dart_revenue_eok"),
            "confidence": v["b"].get("confidence") or v["b"].get("신뢰등급", "M"),
            "kg": v["kg"], "rows": v["rows"],
            "share": round(v["kg"] / total_kg * 1000) / 10 if total_kg > 0 else 0,
        }
        for v in agg.values() if v["rows"] > 0
    ]
    mapped.sort(key=lambda x: x["kg"], reverse=True)
    unmapped = [
        {"company": c, "kg": k, "share": round(k / total_kg * 1000) / 10 if total_kg > 0 else 0}
        for c, k in unm.items()
    ]
    unmapped.sort(key=lambda x: x["kg"], reverse=True)

    mapped_kg = sum(x["kg"] for x in mapped)
    coverage = round(mapped_kg / total_kg * 100) if total_kg > 0 else 0

    # Type breakdown (v205 작업 25.6)
    breakdown = {"자체": 0.0, "OEM": 0.0, "수입": 0.0, "미분류": 0.0}
    for m in mapped:
        key = (m.get("type") or "").strip()
        if key in breakdown: breakdown[key] += m["kg"]
        else: breakdown["미분류"] += m["kg"]
    breakdown["미분류"] += (total_kg - mapped_kg)

    return {
        "tier": 1,
        "category": cfg["category"],
        "accuracy": cfg.get("정확도_기준") or cfg.get("accuracy_basis") or "80%+",
        "mapping_coverage": coverage,
        "totalRows": len(prods),
        "totalKg": total_kg,
        "mapped_brands": mapped,
        "unmapped": unmapped[:top_n],
        "mapped_count": len(mapped),
        "unmapped_count": len(unmapped),
        "bq_call_ms": bq_call_ms,
        "type_breakdown": breakdown,
    }


def search_by_keyword(user_id: str, keyword: str, top_n: int = 10) -> dict:
    bq_t0 = time.monotonic()
    rows = _fetch_production_rows([_norm(keyword)])
    bq_call_ms = round((time.monotonic() - bq_t0) * 1000)
    kwl = _norm(keyword)
    prods = [p for p in rows if kwl in _norm(p.get("name", ""))]
    by_co: dict[str, float] = {}
    total = 0.0
    for p in prods:
        kg = float(p.get("kg24") or 0)
        co = p.get("company") or "(미상)"
        by_co[co] = by_co.get(co, 0.0) + kg
        total += kg
    top = sorted(
        [{"company": c, "kg": k, "share": round(k/total*1000)/10 if total>0 else 0}
         for c, k in by_co.items()],
        key=lambda x: x["kg"], reverse=True,
    )[:top_n]
    return {
        "tier": 0, "accuracy": "60%", "mapping_coverage": 60,
        "totalRows": len(prods), "totalKg": total,
        "topCompanies": top, "bq_call_ms": bq_call_ms,
    }


def search_market_by_domain(user_id: str, keyword: str, top_n: int = 10) -> dict:
    if not keyword or not keyword.strip():
        return {"success": False, "error": "keyword required"}
    t0 = time.monotonic()
    keyword = keyword.strip()
    cfg = match_category(user_id, keyword)
    res = search_by_category(user_id, cfg, top_n) if cfg else search_by_keyword(user_id, keyword, top_n)
    res["success"] = True
    res["keyword"] = keyword
    res["elapsedMs"] = round((time.monotonic() - t0) * 1000)
    res["limit_note"] = "Absolute revenue not derivable; relative ranking only."
    # Log to history
    try:
        user_col(user_id, "search_history").add({
            "timestamp": time.time(), "keyword": keyword,
            "total_rows": res.get("totalRows", 0), "elapsed_ms": res["elapsedMs"],
            "bq_call_ms": res.get("bq_call_ms", 0),
            "category_matched": res.get("category"),
            "tier": res.get("tier", 0),
            "brand_matched_count": res.get("mapped_count", 0),
            "unmapped_count": res.get("unmapped_count", 0),
            "mapping_coverage": res.get("mapping_coverage", 0),
        })
    except Exception as e:
        log.warning("search_history append failed: %s", e)
    return res
