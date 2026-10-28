from fastapi import APIRouter, Depends

from backend.deps import SearchParams, get_repository, search_params
from backend.models import SummaryResponse
from backend.services.repository import Repository

router = APIRouter()


@router.get("/groundwater/summary", response_model=SummaryResponse)
def groundwater_summary(p: SearchParams = Depends(search_params), repo: Repository = Depends(get_repository)):
    """Medians (nulls ignored), sample counts, units and histogram buckets for the radius."""
    return repo.summary(p.lat, p.lon, p.radius_km)
