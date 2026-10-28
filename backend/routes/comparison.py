from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends

from backend.config import Settings
from backend.deps import get_repository, get_settings
from backend.models import CompareRequest, CompareResponse
from backend.services import statistics as st
from backend.services.repository import Repository

router = APIRouter()
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="compare")


@router.post("/properties/compare", response_model=CompareResponse)
def compare_properties(req: CompareRequest, repo: Repository = Depends(get_repository),
                       settings: Settings = Depends(get_settings)):
    """Runs the identical summary for both properties (in parallel) and builds a template summary."""
    a, b = req.property_a, req.property_b
    fa = _pool.submit(repo.summary, round(a.latitude, 5), round(a.longitude, 5), req.radius_km)
    fb = _pool.submit(repo.summary, round(b.latitude, 5), round(b.longitude, 5), req.radius_km)
    sa, sb = fa.result(), fb.result()
    caps = repo.capabilities()
    return CompareResponse(
        radius_km=req.radius_km, property_a=sa, property_b=sb,
        rows=st.build_rows(sa, sb, caps),
        summary_text=st.build_comparison_text(sa, sb, caps, req.radius_km, settings.min_sample),
        data_source=sa.data_source,
    )
