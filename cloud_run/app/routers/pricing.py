from fastapi import APIRouter, Depends, Query
from app.auth import CurrentUser, get_current_user_or_api_key
from app.services.firestore_client import db

router = APIRouter()


@router.get("/category-pricing")
async def category_pricing(
    category: str = Query(...),
    user: CurrentUser = Depends(get_current_user_or_api_key),
):
    snap = db().document(f"global_category_pricing/{category}").get()
    if not snap.exists:
        return {"success": False, "error": "no_pricing_data", "category": category}
    data = snap.to_dict()
    return {
        "success": True, "category": category,
        "avg_price_per_kg": data.get("avg_price_per_kg"),
        "sample_count": data.get("sample_count", 0),
        "source": data.get("source"),
        "last_updated": data.get("last_updated"),
    }
