from __future__ import annotations

import logging
from typing import Any

import httpx

from core.domain.run import Run
from core.domain.trace import TraceStep, TraceStepType
from core.domain.usage import LlmUsage, RunUsageSummary, UsageLine
from runtime.config import Settings

logger = logging.getLogger(__name__)


def usage_from_step_metadata(step: TraceStep) -> LlmUsage | None:
    raw = (step.metadata or {}).get("usage")
    if not isinstance(raw, dict):
        return None
    try:
        return LlmUsage.model_validate(raw)
    except Exception:
        return None


def summarize_run_usage(run_id: str, steps: list[TraceStep]) -> RunUsageSummary:
    lines: list[UsageLine] = []
    tokens_in = 0
    tokens_out = 0
    for step in steps:
        if step.type != TraceStepType.LLM:
            continue
        usage = usage_from_step_metadata(step)
        if usage is None:
            continue
        lines.append(
            UsageLine(
                step_id=step.step_id,
                provider=usage.provider,
                model=usage.model,
                tokens_in=usage.tokens_in,
                tokens_out=usage.tokens_out,
            )
        )
        tokens_in += usage.tokens_in
        tokens_out += usage.tokens_out
    return RunUsageSummary(
        run_id=run_id,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        llm_calls=len(lines),
        lines=lines,
    )


def build_run_completed_usage_payload(summary: RunUsageSummary) -> dict[str, Any]:
    if summary.llm_calls == 0:
        return {}
    return {
        "tokens_in_total": summary.tokens_in,
        "tokens_out_total": summary.tokens_out,
        "llm_calls": summary.llm_calls,
    }


async def export_run_usage(run: Run, summary: RunUsageSummary) -> None:
    settings = Settings()
    if not settings.usage_export_enabled or summary.llm_calls == 0:
        return
    if not settings.usage_webhook_url:
        return
    payload = {
        "run_id": run.id,
        "workspace_id": run.workspace_id,
        "agent_id": run.agent_id,
        "tokens_in": summary.tokens_in,
        "tokens_out": summary.tokens_out,
        "llm_calls": summary.llm_calls,
        "lines": [line.model_dump() for line in summary.lines],
    }
    headers = {}
    internal_secret = getattr(settings, "usage_webhook_secret", None)
    if internal_secret:
        headers["X-Internal-Secret"] = internal_secret
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.usage_webhook_url, json=payload, headers=headers
            )
            response.raise_for_status()
    except Exception:
        logger.warning("usage.webhook_failed", extra={"run_id": run.id}, exc_info=True)
