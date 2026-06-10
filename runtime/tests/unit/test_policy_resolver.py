from core.domain.provider_policy import ModelRef, ProviderPolicy
from runtime.services.policy_resolver import resolve_provider_policy


def test_resolve_request_overrides_manifest(monkeypatch):
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    request = ProviderPolicy(
        llm=ModelRef(provider="openai", model="gpt-4o-mini"),
        embedding=ModelRef(provider="mock"),
    )
    resolved = resolve_provider_policy(request_policy=request, agent_id="research")
    assert resolved.llm is not None
    assert resolved.llm.provider == "openai"
    assert resolved.llm.model == "gpt-4o-mini"
    assert resolved.embedding is not None
    assert resolved.embedding.provider == "mock"


def test_resolve_anthropic_request(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    request = ProviderPolicy(
        llm=ModelRef(provider="anthropic", model="claude-3-5-haiku-20241022")
    )
    resolved = resolve_provider_policy(request_policy=request, agent_id="research")
    assert resolved.llm is not None
    assert resolved.llm.provider == "anthropic"


def test_resolve_groq_request(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    request = ProviderPolicy(llm=ModelRef(provider="groq", model="llama-3.3-70b-versatile"))
    resolved = resolve_provider_policy(request_policy=request, agent_id="research")
    assert resolved.llm is not None
    assert resolved.llm.provider == "groq"
    assert resolved.llm.model == "llama-3.3-70b-versatile"


def test_resolve_manifest_when_no_request(monkeypatch):
    monkeypatch.setenv("USE_MOCK_PROVIDER", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    resolved = resolve_provider_policy(request_policy=None, agent_id="research")
    assert resolved.llm is not None
    assert resolved.llm.provider == "gemini"
