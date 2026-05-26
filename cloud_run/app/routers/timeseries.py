from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from app.auth import CurrentUser, get_current_user_or_api_key
from app.services.firestore_client import user_col

router = APIRouter()


def _load_snapshots(user_id: str, months_back: int) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=months_back * 31)
    cutoff_ym = cutoff.strftime("%Y-%m")
    out = []
    for d in user_col(user_id, "monthly_snapshots").stream():
        data = d.to_dict()
        if str(data.get("month", "")) >= cutoff_ym:
            out.append(data)
    return out


@router.get("/timeseries")
async def timeseries(category: str = Query(...), monthsBack: int = Query(12, ge=1, le=60),
                     user: CurrentUser = Depends(get_current_user_or_api_key)):
    snaps = _load_snapshots(user.user_id, monthsBack)
    by_month: dict[str, float] = {}
    for s in snaps:
        if s.get("category") != category: continue
        m = s["month"]
        by_month[m] = by_month.get(m, 0) + (s.get("production_kg") or 0)
    series = [{"month": m, "production_kg": v} for m, v in sorted(by_month.items())]
    return {"success": True, "category": category, "series": series, "count": len(series),
            "insufficient": "insufficient_data (need 3+ months)" if len(series) < 3 else None}


@router.get("/quarterly")
async def quarterly(category: str = Query(...),
                    user: CurrentUser = Depends(get_current_user_or_api_key)):
    snaps = _load_snapshots(user.user_id, 24)
    by_q: dict[str, float] = {}
    for s in snaps:
        if s.get("category") != category: continue
        m = s["month"]
        y, mo = m.split("-")
        q = f"{y}-Q{(int(mo)-1)//3 + 1}"
        by_q[q] = by_q.get(q, 0) + (s.get("production_kg") or 0)
    quarters = [{"quarter": q, "kg": v} for q, v in sorted(by_q.items())]
    return {"success": True, "category": category, "quarters": quarters, "count": len(quarters),
            "insufficient": "insufficient_data (need 2+ quarters)" if len(quarters) < 2 else None}


@router.get("/brand-trend")
async def brand_trend(brand: str = Query(...), monthsBack: int = Query(12, ge=1, le=60),
                      user: CurrentUser = Depends(get_current_user_or_api_key)):
    snaps = _load_snapshots(user.user_id, monthsBack)
    series = sorted(
        [{"month": s["month"], "production_kg": s.get("production_kg") or 0}
         for s in snaps if s.get("brand") == brand],
        key=lambda x: x["month"],
    )
    return {"success": True, "brand": brand, "series": series, "count": len(series),
            "insufficient": "insufficient_data" if len(series) < 3 else None}


@router.get("/cagr")
async def cagr(category: str = Query(...), periodMonths: int = Query(12, ge=3, le=60),
               user: CurrentUser = Depends(get_current_user_or_api_key)):
    snaps = _load_snapshots(user.user_id, periodMonths + 3)
    by_month: dict[str, float] = {}
    for s in snaps:
        if s.get("category") != category: continue
        by_month[s["month"]] = by_month.get(s["month"], 0) + (s.get("production_kg") or 0)
    months = sorted(by_month.keys())
    if len(months) < 3:
        return {"success": True, "category": category, "cagr_pct": None,
                "insufficient": f"need 3+ months, have {len(months)}"}
    first, last = by_month[months[0]], by_month[months[-1]]
    if first <= 0:
        return {"success": True, "category": category, "cagr_pct": None, "note": "first period zero"}
    n = len(months) - 1
    cagr_v = (last / first) ** (12 / n) - 1
    return {"success": True, "category": category, "cagr_pct": round(cagr_v * 1000) / 10,
            "first_month": months[0], "last_month": months[-1],
            "first_kg": first, "last_kg": last, "period_months": n}


@router.get("/yoy")
async def yoy(category: str = Query(...),
              user: CurrentUser = Depends(get_current_user_or_api_key)):
    snaps = _load_snapshots(user.user_id, 15)
    by_month: dict[str, float] = {}
    for s in snaps:
        if s.get("category") != category: continue
        by_month[s["month"]] = by_month.get(s["month"], 0) + (s.get("production_kg") or 0)
    months = sorted(by_month.keys())
    if len(months) < 13:
        return {"success": True, "category": category, "yoy_pct": None,
                "insufficient": f"need 13+ months, have {len(months)}"}
    latest = months[-1]
    y, m = latest.split("-")
    prev_ym = f"{int(y)-1}-{m}"
    cur = by_month.get(latest, 0)
    prev = by_month.get(prev_ym, 0)
    if prev <= 0:
        return {"success": True, "category": category, "yoy_pct": None,
                "note": f"no prior-year data ({prev_ym})"}
    return {"success": True, "category": category, "latest_month": latest, "prev_year_month": prev_ym,
            "latest_kg": cur, "prev_year_kg": prev,
            "yoy_pct": round((cur - prev) / prev * 1000) / 10}
