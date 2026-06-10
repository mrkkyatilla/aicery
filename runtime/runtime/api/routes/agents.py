from fastapi import APIRouter, Depends

from agents.registry import list_agent_manifests
from runtime.api.auth import require_auth

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(require_auth)],
)


@router.get("")
def list_agents() -> dict:
    return {"agents": list_agent_manifests()}
