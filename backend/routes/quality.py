from fastapi import APIRouter, Depends

from backend.deps import SearchParams, get_repository, search_params
from backend.models import QualityResponse
from backend.services.repository import Repository

router = APIRouter()


@router.get("/water-quality", response_model=QualityResponse)
def water_quality(p: SearchParams = Depends(search_params), repo: Repository = Depends(get_repository)):
    """Observed measurements only. Empty data comes back with an explanation, never invented values."""
    return repo.water_quality(p.lat, p.lon, p.radius_km)
