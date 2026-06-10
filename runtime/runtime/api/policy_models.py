from __future__ import annotations

from pydantic import BaseModel

from core.domain.provider_policy import ModelRef, ProviderPolicy
from runtime.services.policy_resolver import normalize_provider


class ModelRefBody(BaseModel):
    provider: str
    model: str | None = None


class ProviderPolicyBody(BaseModel):
    llm: ModelRefBody | None = None
    embedding: ModelRefBody | None = None


def to_domain_policy(body: ProviderPolicyBody | None) -> ProviderPolicy | None:
    if body is None:
        return None
    llm = None
    embedding = None
    if body.llm:
        llm = ModelRef(provider=normalize_provider(body.llm.provider), model=body.llm.model)
    if body.embedding:
        embedding = ModelRef(
            provider=normalize_provider(body.embedding.provider),
            model=body.embedding.model,
        )
    if llm is None and embedding is None:
        return None
    return ProviderPolicy(llm=llm, embedding=embedding)
