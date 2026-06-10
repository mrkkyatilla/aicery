from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from core.domain.provider_policy import ModelRef
from core.ports.provider import ProviderPort
from runtime.adapters.providers.factory import _build_llm_provider
from runtime.config import Settings
from runtime.services.agent_router import RouteResult

ROUTER_SYSTEM_MARKER = "aicery-router-v1"

_GOLDEN_FILE = Path(__file__).resolve().parents[2] / "data" / "router" / "golden_intents.json"


def build_router_messages(input_text: str, candidates: list[str]) -> list[dict]:
    allowed = ", ".join(candidates)
    system = (
        "You are an agent router. Respond with JSON only.\n"
        'Schema: {"agent_id": "<id>", "confidence": <0-1>, "reason": "<short>"}\n'
        f"Pick exactly one agent from the allowed list.\n"
        f"{ROUTER_SYSTEM_MARKER}\n"
        f"Allowed agents: {allowed}"
    )
    user = f"Utterance to route:\n{input_text}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _strip_markdown_fence(raw: str) -> str:
    text = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def parse_router_response(raw: str, candidates: list[str]) -> RouteResult | None:
    try:
        data = json.loads(_strip_markdown_fence(raw))
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    agent_id = data.get("agent_id")
    if not isinstance(agent_id, str) or agent_id not in candidates:
        return None
    confidence = data.get("confidence")
    if not isinstance(confidence, (int, float)):
        return None
    confidence = float(confidence)
    if confidence < 0.0 or confidence > 1.0:
        return None
    reason = data.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        reason = "llm classification"
    return RouteResult(agent_id, confidence, reason)


def get_router_provider(settings: Settings | None = None) -> ProviderPort:
    settings = settings or Settings()
    provider = settings.router_llm_provider
    if settings.use_mock_provider:
        provider = "mock"
    model = settings.router_llm_model
    if model == "mock":
        model = None
    ref = ModelRef(provider=provider, model=model)
    return _build_llm_provider(ref)


async def route_with_llm(
    input_text: str,
    allowed_agents: list[str],
    *,
    settings: Settings | None = None,
) -> RouteResult | None:
    settings = settings or Settings()
    messages = build_router_messages(input_text, allowed_agents)
    provider = get_router_provider(settings)
    raw = await asyncio.wait_for(
        provider.complete(messages),
        timeout=settings.router_llm_timeout_sec,
    )
    return parse_router_response(raw, allowed_agents)


def load_golden_intents() -> list[dict]:
    with _GOLDEN_FILE.open(encoding="utf-8") as f:
        return json.load(f)
