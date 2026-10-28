from fastapi import APIRouter, Depends

from backend.config import Settings
from backend.deps import get_repository, get_settings
from backend.services.repository import Repository

router = APIRouter()


@router.get("/health")
def health(deep: bool = False, settings: Settings = Depends(get_settings), repo: Repository = Depends(get_repository)):
    """Fast readiness check (no warehouse round-trip). `?deep=true` also pings Databricks.

    Only non-secret status is returned.
    """
    caps = repo.capabilities()
    body = {
        "status": "healthy",
        "mode": repo.mode,  # live | demo | unconfigured
        "features": {
            **caps.model_dump(exclude={"units", "source_dataset"}),
            "genie": settings.genie_configured and repo.mode != "demo",
            "geocoding": bool(settings.geocoder_url),
        },
        "units": caps.units.model_dump(),
        "source_dataset": caps.source_dataset,
        "warnings": settings.warnings() if repo.mode == "live" else [],
        "min_sample_size": settings.min_sample,
    }
    if repo.mode == "unconfigured":
        body["missing_configuration"] = repo.missing()  # type: ignore[attr-defined]
    if deep:
        body["deep"] = repo.ping()
    return body
