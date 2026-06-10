from __future__ import annotations

from core.domain.usage import LlmUsage


def estimate_tokens(text: str) -> int:
    """Rough token estimate when provider does not return usage."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def usage_from_openai_response(data: dict, *, provider: str, model: str) -> LlmUsage | None:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None
    return LlmUsage(
        provider=provider,
        model=model,
        tokens_in=int(usage.get("prompt_tokens", 0) or 0),
        tokens_out=int(usage.get("completion_tokens", 0) or 0),
    )


def usage_from_gemini_metadata(meta, *, provider: str, model: str) -> LlmUsage | None:
    if meta is None:
        return None
    prompt = getattr(meta, "prompt_token_count", None)
    candidates = getattr(meta, "candidates_token_count", None)
    if prompt is None and candidates is None:
        return None
    return LlmUsage(
        provider=provider,
        model=model,
        tokens_in=int(prompt or 0),
        tokens_out=int(candidates or 0),
    )


def estimate_usage(
    messages: list[dict],
    output: str,
    *,
    provider: str,
    model: str,
) -> LlmUsage:
    prompt_text = " ".join(str(m.get("content", "")) for m in messages)
    return LlmUsage(
        provider=provider,
        model=model,
        tokens_in=estimate_tokens(prompt_text),
        tokens_out=estimate_tokens(output),
    )
