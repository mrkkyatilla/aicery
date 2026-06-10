from fastapi import APIRouter, Depends

from runtime.api.auth import require_auth
from runtime.services.marketplace_registry import PluginListResponse, load_plugins

router = APIRouter(
    prefix="/marketplace",
    tags=["marketplace"],
    dependencies=[Depends(require_auth)],
)


@router.get("/plugins")
def list_plugins() -> PluginListResponse:
    return PluginListResponse(plugins=load_plugins())
