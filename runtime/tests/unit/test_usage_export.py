from datetime import UTC, datetime

import pytest

from core.domain.run import Run, RunStatus
from core.domain.trace import TraceStep, TraceStepType
from core.domain.usage import LlmUsage
from runtime.services.usage_service import (
    build_run_completed_usage_payload,
    export_run_usage,
    summarize_run_usage,
)


def test_summarize_run_usage_sums_llm_steps():
    step = TraceStep(
        run_id="r1",
        type=TraceStepType.LLM,
        name="provider.stream",
        metadata={"usage": LlmUsage(provider="mock", model="mock", tokens_in=5, tokens_out=3).model_dump()},
        ended_at=datetime.now(UTC),
    )
    summary = summarize_run_usage("r1", [step])
    assert summary.tokens_in == 5
    assert summary.tokens_out == 3
    assert summary.llm_calls == 1


def test_build_run_completed_usage_payload_empty_when_no_llm():
    summary = summarize_run_usage("r1", [])
    assert build_run_completed_usage_payload(summary) == {}


@pytest.mark.asyncio
async def test_export_run_usage_posts_webhook(monkeypatch):
    calls: list[dict] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json=None, headers=None):
            calls.append({"url": url, "json": json, "headers": headers or {}})
            return FakeResponse()

    monkeypatch.setenv("USAGE_WEBHOOK_URL", "http://example.com/hook")
    monkeypatch.setenv("USAGE_EXPORT_ENABLED", "true")
    monkeypatch.setattr("runtime.services.usage_service.httpx.AsyncClient", FakeClient)

    run = Run(
        id="r1",
        status=RunStatus.COMPLETED,
        agent_id="echo",
        input_text="hi",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    summary = summarize_run_usage(
        "r1",
        [
            TraceStep(
                run_id="r1",
                type=TraceStepType.LLM,
                name="x",
                metadata={
                    "usage": LlmUsage(provider="mock", model="mock", tokens_in=1, tokens_out=2).model_dump()
                },
                ended_at=datetime.now(UTC),
            )
        ],
    )
    await export_run_usage(run, summary)
    assert calls[0]["url"] == "http://example.com/hook"
    assert calls[0]["json"]["tokens_in"] == 1
