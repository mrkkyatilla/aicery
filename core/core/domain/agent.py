from pydantic import BaseModel, Field


class AgentRef(BaseModel):
    id: str
    version: str = "1.0.0"
    tools_allowed: list[str] = Field(default_factory=list)
