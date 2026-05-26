from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from app.auth import CurrentUser, get_current_user_or_api_key
from app.services.firestore_client import user_col

router = APIRouter()


class CompareBody(BaseModel):
    brands: list[str] = Field(..., min_length=1, max_length=5)
    periodMonths: int = Field(6, ge=1, le=60)


@router.post("/brand-compare")
async def compare(body: CompareBody, user: CurrentUser = Depends(get_current_user_or_api_key)):
    cutoff = (datetime.utcnow() - timedelta(days=body.periodMonths * 31)).strftime("%Y-%m")
    matrix: dict[str, dict[str, float]] = {b: {} for b in body.brands}
    months_set: set[str] = set()
    for d in user_col(user.user_id, "monthly_snapshots").stream():
        data = d.to_dict()
        if str(data.get("month", "")) < cutoff: continue
        b = data.get("brand")
        if b not in matrix: continue
        m = data["month"]
        matrix[b][m] = matrix[b].get(m, 0) + (data.get("production_kg") or 0)
        months_set.add(m)
    months = sorted(months_set)
    series = [
        {
            "brand": b,
            "data": [{"month": m, "production_kg": matrix[b].get(m, 0)} for m in months],
            "total_kg": sum(matrix[b].values()),
        }
        for b in body.brands
    ]
    return {
        "success": True, "brands": body.brands, "period_months": body.periodMonths,
        "months": months, "series": series,
        "insufficient": f"need 2+ months, have {len(months)}" if len(months) < 2 else None,
    }
