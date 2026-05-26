from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user_or_api_key
from app.services.firestore_client import user_col
import time

router = APIRouter()


class FavoriteBody(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    frequency: str = Field("weekly", pattern="^(daily|weekly)$")


@router.get("/favorites")
async def list_favorites(user: CurrentUser = Depends(get_current_user_or_api_key)):
    favs = [d.to_dict() for d in user_col(user.user_id, "favorites").stream()]
    return {"success": True, "user_email": user.email, "favorites": favs}


@router.post("/favorites")
async def add_favorite(body: FavoriteBody, user: CurrentUser = Depends(get_current_user_or_api_key)):
    # dedup
    existing = [d for d in user_col(user.user_id, "favorites").where("keyword", "==", body.keyword).stream()]
    if existing:
        return {"success": True, "msg": "already exists", "keyword": body.keyword}
    user_col(user.user_id, "favorites").add({
        "user_email": user.email, "keyword": body.keyword,
        "frequency": body.frequency, "added_at": time.time(),
    })
    return {"success": True, "keyword": body.keyword, "frequency": body.frequency}


@router.delete("/favorites/{keyword}")
async def remove_favorite(keyword: str, user: CurrentUser = Depends(get_current_user_or_api_key)):
    docs = list(user_col(user.user_id, "favorites").where("keyword", "==", keyword).stream())
    for d in docs:
        # delete via document path
        from app.services.firestore_client import db
        db().document(f"users/{user.user_id}/favorites/{d.id}").delete()
    return {"success": True, "deleted": len(docs), "keyword": keyword}
