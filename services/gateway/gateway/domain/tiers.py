from __future__ import annotations

from typing import Literal

TierName = Literal["free", "pro", "team", "past_due"]

TIER_LIMITS: dict[str, dict[str, int]] = {
    "free": {"agent_run": 100, "llm_tokens_out": 50_000},
    "pro": {"agent_run": 2_000, "llm_tokens_out": 2_000_000},
    "team": {"agent_run": 20_000, "llm_tokens_out": 20_000_000},
    "past_due": {"agent_run": 100, "llm_tokens_out": 50_000},
}


def normalize_tier(tier: str | None) -> TierName:
    if tier in TIER_LIMITS:
        return tier  # type: ignore[return-value]
    return "free"
