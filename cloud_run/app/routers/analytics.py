from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from app.auth import CurrentUser, get_current_user_or_api_key
from app.services.firestore_client import user_col

router = APIRouter()


@router.get("/analytics")
async def analytics(daysBack: int = Query(30, ge=1, le=90),
                    user: CurrentUser = Depends(get_current_user_or_api_key)):
    cutoff = (datetime.utcnow() - timedelta(days=daysBack)).timestamp()
    tier1 = tier0 = 0
    hourly = [0] * 24
    cov_by_day: dict[str, dict] = {}
    for d in user_col(user.user_id, "search_history").stream():
        data = d.to_dict()
        ts = data.get("timestamp", 0)
        if ts < cutoff: continue
        tier = data.get("tier", 0) or 0
        if tier >= 1: tier1 += 1
        else: tier0 += 1
        dt = datetime.utcfromtimestamp(ts)
        hourly[dt.hour] += 1
        day = dt.strftime("%Y-%m-%d")
        cov = data.get("mapping_coverage", 0) or 0
        if day not in cov_by_day: cov_by_day[day] = {"sum": 0, "n": 0}
        cov_by_day[day]["sum"] += cov; cov_by_day[day]["n"] += 1
    cov_series = sorted([{"date": d, "avg": round(v["sum"]/v["n"]*10)/10}
                         for d, v in cov_by_day.items()], key=lambda x: x["date"])

    # production_by_category from latest monthly_snapshots
    prod_by_cat: dict[str, float] = {}
    latest_month = ""
    snap_rows = [d.to_dict() for d in user_col(user.user_id, "monthly_snapshots").stream()]
    for r in snap_rows:
        m = str(r.get("month", ""))
        if m > latest_month: latest_month = m
    for r in snap_rows:
        if str(r.get("month", "")) != latest_month: continue
        c = r.get("category", "")
        prod_by_cat[c] = prod_by_cat.get(c, 0) + (r.get("production_kg") or 0)
    prod_series = sorted([{"category": c, "kg": v} for c, v in prod_by_cat.items()],
                         key=lambda x: x["kg"], reverse=True)
    return {
        "success": True, "daysBack": daysBack,
        "tier_distribution": {"tier1": tier1, "tier0": tier0},
        "hourly": [{"hour": h, "count": c} for h, c in enumerate(hourly)],
        "coverage_trend": cov_series,
        "production_by_category": prod_series,
        "latest_snapshot_month": latest_month,
    }
