from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from runtime.api.auth import require_auth
from runtime.config import Settings
from runtime.services.agent_router import route_input_async

router = APIRouter(
    prefix="/route",
    tags=["route"],
    dependencies=[Depends(require_auth)],
)


class RouteRequest(BaseModel):
    input: str = Field(min_length=1)
    allowed_agents: list[str] | None = None


class RouteResponse(BaseModel):
    agent_id: str
    confidence: float
    reason: str


@router.post("", status_code=status.HTTP_200_OK, response_model=RouteResponse)
async def route_agent(body: RouteRequest) -> RouteResponse:
    settings = Settings()
    result = await route_input_async(
        body.input,
        allowed_agents=body.allowed_agents,
        settings=settings,
    )
    return RouteResponse(
        agent_id=result.agent_id,
        confidence=result.confidence,
        reason=result.reason,
    )
