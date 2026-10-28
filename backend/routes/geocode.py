from fastapi import APIRouter, Depends, Query

from backend.config import Settings
from backend.deps import get_settings
from backend.services.geocode import search_places

router = APIRouter()


@router.get("/geocode")
def geocode(q: str = Query(min_length=2, max_length=100), settings: Settings = Depends(get_settings)):
    return {"results": search_places(settings, q.strip())}
