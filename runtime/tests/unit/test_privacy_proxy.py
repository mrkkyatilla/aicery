import json
from pathlib import Path

import pytest

from runtime.adapters.providers.mock import MockProvider
from runtime.adapters.providers.privacy_proxy import (
    PrivacyProxyProvider,
    PrivacyVault,
    PrivacyViolationError,
    contains_pii,
    mask_text,
    unmask_text,
)

GOLDEN = Path(__file__).resolve().parents[2] / "data" / "privacy" / "golden_pii.json"


class _CaptureProvider:
    def __init__(self) -> None:
        self.last_messages: list[dict] | None = None

    async def complete(self, messages: list[dict], **kwargs) -> str:
        self.last_messages = messages
        content = messages[-1].get("content", "")
        return f"echo:{content}"

    async def stream(self, messages: list[dict], **kwargs):
        text = await self.complete(messages, **kwargs)
        yield text


@pytest.fixture
def golden_cases():
    return json.loads(GOLDEN.read_text())


def test_mask_golden_cases(golden_cases):
    for case in golden_cases:
        vault = PrivacyVault()
        masked = mask_text(case["input"], vault)
        for forbidden in case.get("must_not_contain", []):
            assert forbidden not in masked, case["id"]
        for required in case.get("must_contain", []):
            assert required in masked, case["id"]


def test_unmask_roundtrip(golden_cases):
    case = next(c for c in golden_cases if c["id"] == "roundtrip")
    vault = PrivacyVault()
    mask_text(case["input"], vault)
    unmasked = unmask_text(case["response_with_placeholder"], vault)
    assert unmasked == case["expected_unmasked"]


def test_vault_isolation():
    v1 = PrivacyVault()
    v2 = PrivacyVault()
    m1 = mask_text("a@b.co", v1)
    m2 = mask_text("c@d.co", v2)
    assert "[[PII_EMAIL_0]]" in m1
    assert "[[PII_EMAIL_0]]" in m2
    assert unmask_text(m1, v1) == "a@b.co"
    assert unmask_text(m2, v2) == "c@d.co"


@pytest.mark.asyncio
async def test_proxy_masks_outbound():
    inner = _CaptureProvider()
    proxy = PrivacyProxyProvider(inner, fail_closed=True)
    await proxy.complete([{"role": "user", "content": "Email me at x@y.co"}])
    assert inner.last_messages is not None
    outbound = inner.last_messages[-1]["content"]
    assert "x@y.co" not in outbound
    assert "[[PII_EMAIL_0]]" in outbound


@pytest.mark.asyncio
async def test_proxy_fail_closed_blocks_residual():
    inner = MockProvider()
    proxy = PrivacyProxyProvider(inner, fail_closed=True)

    class _LeakyMask:
        @staticmethod
        def bad_messages(messages, vault):
            return messages

    import runtime.adapters.providers.privacy_proxy as mod

    original = mod.mask_messages
    mod.mask_messages = _LeakyMask.bad_messages  # type: ignore[assignment]
    try:
        with pytest.raises(PrivacyViolationError):
            await proxy.complete([{"role": "user", "content": "a@b.co"}])
    finally:
        mod.mask_messages = original


def test_contains_pii():
    assert contains_pii("reach me at a@b.co")
    assert not contains_pii("no secrets here")
