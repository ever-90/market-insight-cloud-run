from fastapi import APIRouter, Depends, Query
from app.auth import CurrentUser, get_current_user_or_api_key
from app.services.firestore_client import user_col
import time

router = APIRouter()


@router.get("/search-history")
async def get_history(
    daysBack: int = Query(7, ge=1, le=90),
    user: CurrentUser = Depends(get_current_user_or_api_key),
):
    cutoff = time.time() - daysBack * 86400
    rows = []
    for d in user_col(user.user_id, "search_history").stream():
        data = d.to_dict()
        ts = data.get("timestamp", 0)
        if ts >= cutoff:
            rows.append(data)
    rows.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return {"success": True, "user_email": user.email, "daysBack": daysBack, "history": rows[:20]}
