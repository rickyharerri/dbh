from fastapi import APIRouter, Depends

from backend.deps import get_genie
from backend.models import GenieChatRequest, GenieChatResponse
from backend.services.genie import GenieService

router = APIRouter()


@router.post("/genie/chat", response_model=GenieChatResponse)
def genie_chat(req: GenieChatRequest, genie: GenieService = Depends(get_genie)):
    """Start or continue a Genie conversation. The browser never sees Databricks credentials."""
    return genie.ask(req)
