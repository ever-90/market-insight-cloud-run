from fastapi import APIRouter, Depends, Query
from app.auth import CurrentUser, get_current_user_or_api_key
from app.services.firestore_client import db
from app.services.search_engine import match_category, search_by_category

router = APIRouter()


@router.get("/market-size")
async def market_size(
    category: str = Query(...),
    user: CurrentUser = Depends(get_current_user_or_api_key),
):
    cfg = match_category(user.user_id, category)
    if not cfg:
        return {"success": False, "error": "category_not_mapped"}
    snap = db().document(f"global_category_pricing/{category}").get()
    if not snap.exists:
        return {"success": False, "error": "no_pricing_data"}
    price = snap.to_dict().get("avg_price_per_kg") or 0
    if price <= 0:
        return {"success": False, "error": "invalid_pricing"}
    r = search_by_category(user.user_id, cfg, 5)
    total_kg = r.get("totalKg", 0)
    return {
        "success": True, "category": category, "total_kg": total_kg,
        "avg_price_per_kg": price,
        "estimated_market_size": round(total_kg * price),
        "source": snap.to_dict().get("source"),
        "note": "Average-price estimate. Actual revenue may differ.",
    }
