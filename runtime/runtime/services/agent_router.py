from __future__ import annotations

import re
from dataclasses import dataclass

from agents.registry import list_agent_manifests
from runtime.config import Settings


@dataclass
class RouteResult:
    agent_id: str
    confidence: float
    reason: str


_ECHO_PATTERNS = (
    r"^hello\b",
    r"^hi\b",
    r"^hey\b",
    r"^test\b",
    r"^ping\b",
)

_RESEARCH_KEYWORDS = (
    "summarize",
    "summary",
    "read",
    "search",
    "docs",
    "document",
    "file",
    "mvp",
    "research",
    "workspace",
    ".md",
)


def route_input(input_text: str, *, allowed_agents: list[str] | None = None) -> RouteResult:
    text = (input_text or "").strip()
    lower = text.lower()
    known = {a["id"] for a in list_agent_manifests()}
    candidates = [a for a in known if not allowed_agents or a in allowed_agents]
    if not candidates:
        candidates = list(known) or ["research"]

    if len(text) < 40 and not any(k in lower for k in _RESEARCH_KEYWORDS):
        for pattern in _ECHO_PATTERNS:
            if re.search(pattern, lower):
                if "echo" in candidates:
                    return RouteResult("echo", 0.85, f"short greeting matched {pattern}")
        if len(text.split()) <= 4 and "echo" in candidates:
            return RouteResult("echo", 0.7, "short input default to echo")

    score = 0.0
    reasons: list[str] = []
    for kw in _RESEARCH_KEYWORDS:
        if kw in lower:
            score += 0.15
            reasons.append(kw)
    if score > 0 and "research" in candidates:
        conf = min(0.95, 0.55 + score)
        return RouteResult("research", conf, "keywords: " + ", ".join(reasons[:5]))

    agent_id = "research" if "research" in candidates else candidates[0]
    return RouteResult(agent_id, 0.5, "default agent")


def _resolve_candidates(allowed_agents: list[str] | None) -> list[str]:
    known = {a["id"] for a in list_agent_manifests()}
    candidates = [a for a in known if not allowed_agents or a in allowed_agents]
    return candidates or list(known) or ["research"]


async def route_input_async(
    input_text: str,
    *,
    allowed_agents: list[str] | None = None,
    settings: Settings | None = None,
) -> RouteResult:
    settings = settings or Settings()
    rule = route_input(input_text, allowed_agents=allowed_agents)
    if not settings.router_llm_enabled:
        return rule
    if rule.confidence >= settings.router_rule_short_circuit:
        return RouteResult(rule.agent_id, rule.confidence, f"rule:{rule.reason}")
    try:
        from runtime.services.llm_router import route_with_llm

        candidates = _resolve_candidates(allowed_agents)
        llm = await route_with_llm(input_text, candidates, settings=settings)
        if llm and llm.confidence >= settings.router_llm_confidence_threshold:
            return RouteResult(llm.agent_id, llm.confidence, f"llm:{llm.reason}")
    except Exception:
        pass
    return RouteResult(rule.agent_id, rule.confidence, f"fallback:{rule.reason}")
