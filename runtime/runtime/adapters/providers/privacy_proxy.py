from __future__ import annotations

import re
from collections.abc import AsyncIterator

from core.ports.provider import ProviderPort

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    ("tc_kimlik", re.compile(r"\b\d{11}\b")),
    ("wallet", re.compile(r"0x[a-fA-F0-9]{40}\b")),
    (
        "api_key",
        re.compile(
            r"(?:sk-[a-zA-Z0-9]{20,}|api[_-]?key[=:\s]+[a-zA-Z0-9_\-]{16,})",
            re.IGNORECASE,
        ),
    ),
]


class PrivacyViolationError(RuntimeError):
    """Outbound message still contains detectable PII after masking."""


class PrivacyVault:
    """Run-scoped placeholder map; not persisted to trace."""

    def __init__(self) -> None:
        self._map: dict[str, str] = {}
        self._counter = 0

    def placeholder(self, kind: str, value: str) -> str:
        token = f"[[PII_{kind.upper()}_{self._counter}]]"
        self._counter += 1
        self._map[token] = value
        return token

    def items(self) -> list[tuple[str, str]]:
        return list(self._map.items())


def contains_pii(text: str) -> bool:
    return any(pattern.search(text) for _, pattern in _PATTERNS)


def mask_text(text: str, vault: PrivacyVault) -> str:
    result = text
    for kind, pattern in _PATTERNS:
        result = pattern.sub(lambda m, k=kind: vault.placeholder(k, m.group(0)), result)
    return result


def unmask_text(text: str, vault: PrivacyVault) -> str:
    result = text
    for token, value in vault.items():
        result = result.replace(token, value)
    return result


def mask_messages(messages: list[dict], vault: PrivacyVault) -> list[dict]:
    masked: list[dict] = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            masked.append({**msg, "content": mask_text(content, vault)})
        else:
            masked.append(dict(msg))
    return masked


def _assert_outbound_safe(messages: list[dict], *, fail_closed: bool) -> None:
    if not fail_closed:
        return
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str) and contains_pii(content):
            raise PrivacyViolationError("residual PII detected in outbound LLM messages")


class PrivacyProxyProvider:
    """ProviderPort wrapper: mask outbound messages, unmask LLM responses."""

    def __init__(self, inner: ProviderPort, *, fail_closed: bool = True) -> None:
        self._inner = inner
        self._fail_closed = fail_closed

    async def complete(self, messages: list[dict], **kwargs) -> str:
        vault = PrivacyVault()
        masked = mask_messages(messages, vault)
        _assert_outbound_safe(masked, fail_closed=self._fail_closed)
        raw = await self._inner.complete(masked, **kwargs)
        return unmask_text(raw, vault)

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        vault = PrivacyVault()
        masked = mask_messages(messages, vault)
        _assert_outbound_safe(masked, fail_closed=self._fail_closed)
        parts: list[str] = []
        async for token in self._inner.stream(masked, **kwargs):
            parts.append(token)
            yield token
        full = unmask_text("".join(parts), vault)
        if full != "".join(parts):
            correction = full[len("".join(parts)) :] if len(full) > len("".join(parts)) else ""
            if correction:
                yield correction
