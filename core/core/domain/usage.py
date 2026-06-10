from __future__ import annotations

from pydantic import BaseModel, Field


class LlmUsage(BaseModel):
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0


class UsageLine(BaseModel):
    step_id: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0


class RunUsageSummary(BaseModel):
    run_id: str
    tokens_in: int = 0
    tokens_out: int = 0
    llm_calls: int = 0
    lines: list[UsageLine] = Field(default_factory=list)
