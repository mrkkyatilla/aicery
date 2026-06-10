from __future__ import annotations

from core.domain.provider_policy import ModelRef, ProviderKind, ProviderPolicy
from runtime.config import Settings


def resolve_provider_policy(
    *,
    request_policy: ProviderPolicy | None,
    agent_id: str | None,
) -> ProviderPolicy:
    """Merge request > manifest > settings defaults."""
    llm = _resolve_llm(request_policy, agent_id)
    embedding = _resolve_embedding(request_policy, agent_id)
    return ProviderPolicy(llm=llm, embedding=embedding)


def _resolve_llm(request_policy: ProviderPolicy | None, agent_id: str | None) -> ModelRef:
    if request_policy and request_policy.llm:
        return request_policy.llm
    manifest = _manifest_policy(agent_id)
    if manifest and manifest.llm:
        return manifest.llm
    return _settings_default_llm()


def _resolve_embedding(
    request_policy: ProviderPolicy | None, agent_id: str | None
) -> ModelRef:
    if request_policy and request_policy.embedding:
        return request_policy.embedding
    manifest = _manifest_policy(agent_id)
    if manifest and manifest.embedding:
        return manifest.embedding
    return _settings_default_embedding()


def _manifest_policy(agent_id: str | None) -> ProviderPolicy | None:
    if not agent_id:
        return None
    try:
        from agents.manifest import get_model_policy

        return get_model_policy(agent_id)
    except Exception:
        return None


def _settings_default_llm() -> ModelRef:
    settings = Settings()
    if settings.use_mock_provider or not settings.gemini_api_key:
        return ModelRef(provider="mock", model=None)
    return ModelRef(provider="gemini", model=settings.gemini_model)


def _settings_default_embedding() -> ModelRef:
    settings = Settings()
    if settings.use_mock_provider or not settings.gemini_api_key:
        return ModelRef(provider="mock", model=None)
    return ModelRef(provider="gemini", model=settings.embedding_model)


def validate_resolved_policy(policy: ProviderPolicy) -> None:
    settings = Settings()
    for ref in (policy.llm, policy.embedding):
        if ref is None:
            continue
        if ref.provider == "openai" and not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY required for openai provider")
        if ref.provider == "groq" and not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY required for groq provider")
        if ref.provider == "anthropic" and not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY required for anthropic provider")
        if ref.provider == "gemini" and not settings.gemini_api_key and not settings.use_mock_provider:
            raise ValueError("GEMINI_API_KEY required for gemini provider")


def normalize_provider(provider: str) -> ProviderKind:
    p = provider.lower().strip()
    if p not in ("gemini", "openai", "groq", "anthropic", "mock"):
        raise ValueError(f"Unknown provider: {provider}")
    return p  # type: ignore[return-value]
