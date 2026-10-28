"""FastAPI dependencies. Tests override these via app.dependency_overrides."""
from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, Query

from backend.config import DEFAULT_RADIUS_KM, DEFAULT_WELL_LIMIT, MAX_WELL_LIMIT, Settings, get_settings as _get_settings
from backend.models import Point, validate_radius
from backend.services.genie import GenieService
from backend.services.repository import Repository, build_repository


def get_settings() -> Settings:
    return _get_settings()


@lru_cache(maxsize=1)
def _repo() -> Repository:
    return build_repository(_get_settings())


def get_repository() -> Repository:
    return _repo()


@lru_cache(maxsize=1)
def _genie() -> GenieService:
    return GenieService(_get_settings())


def get_genie() -> GenieService:
    return _genie()


class SearchParams:
    """Validated lat/lon/radius shared by every location endpoint."""

    def __init__(self, point: Point, radius_km: float):
        self.lat, self.lon, self.radius_km = point.latitude, point.longitude, radius_km


def search_params(
    latitude: float = Query(..., ge=-90, le=90, allow_inf_nan=False, description="Degrees north"),
    longitude: float = Query(..., ge=-180, le=180, allow_inf_nan=False, description="Degrees east (negative = west)"),
    radius_km: float = Query(DEFAULT_RADIUS_KM, description="One of 1, 2, 5, 10, 20"),
) -> SearchParams:
    try:
        radius = validate_radius(radius_km)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # 5 decimal places ≈ 1 m: normalising makes the response cache effective
    return SearchParams(Point(latitude=round(latitude, 5), longitude=round(longitude, 5)), radius)


def limit_param(limit: int = Query(DEFAULT_WELL_LIMIT, ge=1, le=MAX_WELL_LIMIT)) -> int:
    return limit
