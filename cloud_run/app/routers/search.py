from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user_or_api_key
from app.services.search_engine import search_market_by_domain

router = APIRouter()


class SearchBody(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    topN: int = Field(10, ge=1, le=100)


@router.post("/search")
async def search(body: SearchBody, user: CurrentUser = Depends(get_current_user_or_api_key)):
    return search_market_by_domain(user.user_id, body.keyword, body.topN)
