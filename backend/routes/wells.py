from fastapi import APIRouter, Depends, HTTPException, Path

from backend.deps import SearchParams, get_repository, limit_param, search_params
from backend.models import NearbyResponse, WellDetails
from backend.services.repository import Repository

router = APIRouter()


@router.get("/wells/nearby", response_model=NearbyResponse)
def nearby_wells(p: SearchParams = Depends(search_params), limit: int = Depends(limit_param),
                 repo: Repository = Depends(get_repository)):
    """Wells within radius_km (great-circle). total_wells counts ALL matches; wells is capped at `limit`."""
    return repo.nearby(p.lat, p.lon, p.radius_km, limit)


@router.get("/wells/{well_id}", response_model=WellDetails)
def well_details(well_id: str = Path(min_length=1, max_length=64), repo: Repository = Depends(get_repository)):
    details = repo.well_details(well_id)
    if details is None:
        raise HTTPException(status_code=404, detail="No well with that identifier was found.")
    return details
