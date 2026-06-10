from __future__ import annotations

from core.domain.provider_policy import ModelRef, ProviderPolicy
from core.ports.provider import ProviderPort
from runtime.adapters.providers.anthropic import AnthropicProvider
from runtime.adapters.providers.gemini import GeminiProvider
from runtime.adapters.providers.groq import GroqProvider
from runtime.adapters.providers.metering import MeteringProvider
from runtime.adapters.providers.mock import MockProvider
from runtime.adapters.providers.openai import OpenAIProvider
from runtime.adapters.providers.router import ProviderRouter
from runtime.config import Settings
from runtime.services.policy_resolver import resolve_provider_policy, validate_resolved_policy


def get_provider(
    *,
    policy: ProviderPolicy | None = None,
    agent_id: str | None = None,
) -> ProviderPort:
    resolved = resolve_provider_policy(request_policy=policy, agent_id=agent_id)
    validate_resolved_policy(resolved)
    assert resolved.llm is not None
    return _build_llm_provider(resolved.llm)


def get_embedder(
    *,
    policy: ProviderPolicy | None = None,
    agent_id: str | None = None,
):
    from runtime.intelligence.embeddings import get_embedder as _build_embedder_from_ref

    resolved = resolve_provider_policy(request_policy=policy, agent_id=agent_id)
    validate_resolved_policy(resolved)
    assert resolved.embedding is not None
    return _build_embedder_from_ref(resolved.embedding)


def _metering_model(ref: ModelRef) -> str:
    settings = Settings()
    if ref.model:
        return ref.model
    if ref.provider == "openai":
        return settings.openai_model
    if ref.provider == "groq":
        return settings.groq_model
    if ref.provider == "anthropic":
        return settings.anthropic_model
    if ref.provider == "gemini":
        return settings.gemini_model
    return "mock"


def _wrap_metered(inner: ProviderPort, ref: ModelRef) -> ProviderPort:
    return MeteringProvider(inner, provider=ref.provider, model=_metering_model(ref))


def _wrap_privacy(inner: ProviderPort) -> ProviderPort:
    settings = Settings()
    if not settings.privacy_proxy_enabled:
        return inner
    from runtime.adapters.providers.privacy_proxy import PrivacyProxyProvider

    return PrivacyProxyProvider(inner, fail_closed=settings.privacy_proxy_fail_closed)


def _finalize_provider(inner: ProviderPort, ref: ModelRef) -> ProviderPort:
    return _wrap_privacy(_wrap_metered(inner, ref))


def _build_llm_provider(ref: ModelRef) -> ProviderPort:
    settings = Settings()
    if ref.provider == "mock":
        return _finalize_provider(MockProvider(), ref)
    if ref.provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        primary = OpenAIProvider(
            settings.openai_api_key,
            model=ref.model or settings.openai_model,
        )
        fallback = MockProvider()
        inner: ProviderPort = (
            ProviderRouter(primary, fallback)
            if settings.provider_failover_enabled
            else primary
        )
        return _finalize_provider(inner, ref)
    if ref.provider == "groq":
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")
        primary = GroqProvider(
            settings.groq_api_key,
            model=ref.model or settings.groq_model,
        )
        fallback = MockProvider()
        inner = (
            ProviderRouter(primary, fallback)
            if settings.provider_failover_enabled
            else primary
        )
        return _finalize_provider(inner, ref)
    if ref.provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        primary = AnthropicProvider(
            settings.anthropic_api_key,
            model=ref.model or settings.anthropic_model,
        )
        fallback = MockProvider()
        inner = (
            ProviderRouter(primary, fallback)
            if settings.provider_failover_enabled
            else primary
        )
        return _finalize_provider(inner, ref)
    if ref.provider == "gemini":
        if settings.use_mock_provider or not settings.gemini_api_key:
            return _finalize_provider(MockProvider(), ref)
        primary = GeminiProvider(
            settings.gemini_api_key,
            model=ref.model or settings.gemini_model,
        )
        fallback = MockProvider()
        inner = (
            ProviderRouter(primary, fallback)
            if settings.provider_failover_enabled
            else primary
        )
        return _finalize_provider(inner, ref)
    raise ValueError(f"Unknown LLM provider: {ref.provider}")
