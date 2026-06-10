from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ProviderKind = Literal["gemini", "openai", "groq", "anthropic", "mock"]


class ModelRef(BaseModel):
    provider: ProviderKind
    model: str | None = None


class ProviderPolicy(BaseModel):
    llm: ModelRef | None = None
    embedding: ModelRef | None = None


def policy_to_dict(policy: ProviderPolicy | None) -> dict | None:
    if policy is None:
        return None
    return policy.model_dump(mode="json", exclude_none=True)


def policy_from_dict(data: dict | None) -> ProviderPolicy | None:
    if not data:
        return None
    return ProviderPolicy.model_validate(data)
