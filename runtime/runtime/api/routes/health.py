from fastapi import APIRouter

from runtime.api.deps import SettingsDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    return {"status": "ok", "version": settings.api_version}
