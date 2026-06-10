from __future__ import annotations

from collections.abc import AsyncIterator

from langgraph.types import Command

from agents.registry import UnknownAgentError, get_graph_builder, resolve_run_target
from core.domain.provider_policy import ModelRef
from core.domain.replay import ReplayContext
from core.domain.run import Run, RunStatus
from core.domain.usage import LlmUsage
from core.ports.provider import ProviderPort
from runtime.adapters.db.approval_repository import ApprovalRepository
from runtime.adapters.langgraph.checkpointer import get_checkpointer
from runtime.adapters.langgraph.graph_run_driver import GraphRunDriver
from runtime.adapters.tools.factory import build_tool_executor
from runtime.config import Settings
from runtime.errors import GraphStepLimitError, HitlApprovalPending
from runtime.services.hitl_coordinator import HitlCoordinator
from runtime.services.hot_memory_hooks import (
    build_messages_with_history_async,
    memory_key_for_run,
)
from runtime.services.trace_recorder import TraceRecorder
from tools.registry.executor import ToolNotFound, ToolPermissionDenied, ToolTimeout


class LangGraphOrchestrator:
    def __init__(
        self,
        provider: ProviderPort,
        *,
        llm_ref: ModelRef | None = None,
        replay_ctx: ReplayContext | None = None,
        trace_recorder: TraceRecorder | None = None,
        trace_session=None,
        chain_resume: dict | None = None,
    ) -> None:
        self._provider = provider
        self._llm_ref = llm_ref
        self._replay_ctx = replay_ctx or ReplayContext()
        self._trace = trace_recorder
        self._trace_session = trace_session
        self._settings = Settings()
        self._chain_resume = chain_resume

    def _coordinator(self) -> HitlCoordinator:
        if self._trace_session is None:
            raise RuntimeError("trace_session required for graph HITL")
        return HitlCoordinator(
            self._trace_session,
            settings=self._settings,
            trace_recorder=self._trace,
        )

    def _resolved_model(self) -> str:
        if self._llm_ref and self._llm_ref.model:
            return self._llm_ref.model
        if self._llm_ref and self._llm_ref.provider == "openai":
            return self._settings.openai_model
        return self._settings.gemini_model

    def _pop_provider_usage(self) -> LlmUsage | None:
        pop = getattr(self._provider, "pop_usage", None)
        if callable(pop):
            return pop()
        return getattr(self._provider, "last_usage", None)

    async def execute(self, run: Run) -> Run:
        parts: list[str] = []
        async for chunk in self.stream(run):
            if chunk.get("type") == "token":
                parts.append(chunk.get("text", ""))
            elif chunk.get("type") == "error":
                run.status = RunStatus.FAILED
                run.error_code = chunk.get("error_code", "RUN_FAILED")
                run.error_message = chunk.get("message", "Run failed")
                return run
        run.output_text = "".join(parts).strip()
        if run.status not in (RunStatus.FAILED, RunStatus.CANCELLED):
            run.status = RunStatus.COMPLETED
        return run

    async def stream(self, run: Run) -> AsyncIterator[dict]:
        try:
            agent_id, pipeline = resolve_run_target(run)
            builder = get_graph_builder(agent_id, pipeline=pipeline)
        except UnknownAgentError as exc:
            yield {
                "type": "error",
                "error_code": exc.error_code,
                "message": str(exc),
            }
            return

        tools = build_tool_executor(
            agent_id,
            pipeline_id=pipeline,
            replay_ctx=self._replay_ctx,
            trace_recorder=self._trace,
            trace_session=self._trace_session,
        )
        run = run.model_copy(update={"agent_id": agent_id})

        if pipeline == "research-chain":
            async for event in self._stream_chain(run, tools, builder):
                yield event
            return

        if agent_id == "hitl-demo":
            async for event in self._stream_hitl_demo_graph(run, tools, builder):
                yield event
            return

        if agent_id == "echo":
            async for event in self._stream_echo(run):
                yield event
            return

        if agent_id == "research":
            async for event in self._stream_research(run, tools):
                yield event
            return

        if agent_id == "inventory-advisor":
            async for event in self._stream_inventory_advisor(run, tools, builder):
                yield event
            return

        yield {
            "type": "error",
            "error_code": "UNKNOWN_AGENT",
            "message": f"No stream handler for {agent_id}",
        }

    async def _stream_graph(
        self,
        run: Run,
        tools,
        builder,
        *,
        graph_name: str,
        initial_state: dict,
    ) -> AsyncIterator[dict]:
        checkpointer = await get_checkpointer(self._settings)
        graph = builder(
            self._provider,
            tools,
            run,
            checkpointer=checkpointer,
            replay_ctx=self._replay_ctx,
        )
        config = {"configurable": {"thread_id": run.id}}
        coordinator = self._coordinator()
        driver = GraphRunDriver(coordinator)

        if self._chain_resume is not None:
            graph_input: dict | Command = Command(resume=self._chain_resume)
        else:
            snapshot = await graph.aget_state(config)
            if snapshot.next:
                yield {
                    "type": "error",
                    "error_code": "GRAPH_CHECKPOINT_PENDING",
                    "message": "Graph has pending checkpoint; resume required",
                }
                return
            graph_input = initial_state

        async def on_node(node_name: str, update: dict) -> None:
            if self._trace:
                prefix = "chain" if graph_name == "research-chain" else run.agent_id
                self._trace.record_agent_step(
                    run_id=run.id,
                    name=f"{prefix}.{node_name}",
                    node=node_name,
                    step_index=update.get("step_index", 0),
                )

        try:
            async for event in driver.stream(
                run,
                graph,
                config=config,
                graph_input=graph_input,
                graph_name=graph_name,
                on_node=on_node,
                on_complete=self._make_on_complete(run, graph_name),
            ):
                yield event
        except GraphStepLimitError as exc:
            yield {"type": "error", "error_code": exc.error_code, "message": str(exc)}
        except (ToolPermissionDenied, ToolTimeout, ToolNotFound) as exc:
            yield {"type": "error", "error_code": exc.error_code, "message": str(exc)}

    def _make_on_complete(self, run: Run, graph_name: str):
        async def on_complete(final: dict) -> AsyncIterator[dict]:
            messages = final.get("messages", [])
            assistant = next(
                (m for m in reversed(messages) if m.get("role") == "assistant"),
                None,
            )
            if not assistant:
                return
            text = assistant.get("content", "")
            chunk_size = 40 if graph_name == "research-chain" else 20
            for i in range(0, len(text), chunk_size):
                yield {"type": "token", "text": text[i : i + chunk_size]}
            if graph_name == "research-chain" and self._trace:
                usage = self._pop_provider_usage()
                llm_messages = [
                    {"role": "system", "content": "Summarize for the user."},
                    {
                        "role": "user",
                        "content": str(final.get("artifacts", {}).get("content", run.input_text))[:8000],
                    },
                ]
                self._trace.record_llm(
                    run_id=run.id,
                    name="chain.summarizer",
                    messages=llm_messages,
                    output=text,
                    model=self._resolved_model(),
                    usage=usage,
                )

        return on_complete

    async def _stream_chain(self, run: Run, tools, builder) -> AsyncIterator[dict]:
        async for event in self._stream_graph(
            run,
            tools,
            builder,
            graph_name="research-chain",
            initial_state={
                "messages": [{"role": "user", "content": run.input_text}],
                "artifacts": {},
                "step_index": 0,
            },
        ):
            yield event

    async def _stream_hitl_demo_graph(self, run: Run, tools, builder) -> AsyncIterator[dict]:
        async for event in self._stream_graph(
            run,
            tools,
            builder,
            graph_name="hitl-demo",
            initial_state={
                "messages": [{"role": "user", "content": run.input_text}],
                "step_index": 0,
            },
        ):
            yield event

    async def _stream_inventory_advisor(self, run: Run, tools, builder) -> AsyncIterator[dict]:
        async for event in self._stream_graph(
            run,
            tools,
            builder,
            graph_name="inventory-advisor",
            initial_state={
                "messages": [{"role": "user", "content": run.input_text}],
                "step_index": 0,
            },
        ):
            yield event

    async def _stream_echo(self, run: Run) -> AsyncIterator[dict]:
        messages = await build_messages_with_history_async(
            memory_key_for_run(run),
            system="You are a helpful assistant.",
            user_content=run.input_text,
        )
        yield {"type": "step", "node": "llm", "index": 0}
        if self._trace:
            self._trace.record_agent_step(
                run_id=run.id,
                name="echo.llm",
                node="llm",
                step_index=0,
            )
        output_parts: list[str] = []
        async for token in self._provider.stream(messages):
            output_parts.append(token)
            yield {"type": "token", "text": token}
        if self._trace:
            self._trace.record_llm(
                run_id=run.id,
                name="provider.stream",
                messages=messages,
                output="".join(output_parts),
                model=self._resolved_model(),
                usage=self._pop_provider_usage(),
            )

    async def _stream_research(self, run: Run, tools) -> AsyncIterator[dict]:
        yield {"type": "step", "node": "research", "index": 0}
        if self._trace:
            self._trace.record_agent_step(
                run_id=run.id,
                name="research.main",
                node="research",
                step_index=0,
            )
        try:
            from agents.graphs.research_paths import resolve_research_file_path

            path = await resolve_research_file_path(
                run.input_text or "",
                tools,
                run_id=run.id,
                agent_id=run.agent_id,
            )
            outcome = await tools.invoke(
                "read_file",
                {"path": path},
                run_id=run.id,
                agent_id=run.agent_id,
            )
            content = outcome["result"]["content"]
            messages = [
                {"role": "system", "content": "Summarize the file briefly."},
                {"role": "user", "content": content[:8000]},
            ]
            output_parts: list[str] = []
            async for token in self._provider.stream(messages):
                output_parts.append(token)
                yield {"type": "token", "text": token}
            if self._trace:
                self._trace.record_llm(
                    run_id=run.id,
                    name="provider.stream",
                    messages=messages,
                    output="".join(output_parts),
                    model=self._resolved_model(),
                    usage=self._pop_provider_usage(),
                )
        except HitlApprovalPending as exc:
            repo = ApprovalRepository(self._trace_session)
            pending = repo.get_by_id(exc.approval_id)
            if pending is not None:
                yield HitlCoordinator.build_approval_chunk(pending)
            else:
                yield {
                    "type": "approval_required",
                    "status": "awaiting_human_approval",
                    "approval_id": exc.approval_id,
                    "tool_name": exc.tool_name,
                    "arguments": exc.arguments,
                    "expires_at": exc.expires_at,
                    "hitl_mode": "executor",
                }
        except (ToolPermissionDenied, ToolTimeout, ToolNotFound) as exc:
            yield {"type": "error", "error_code": exc.error_code, "message": str(exc)}
        except FileNotFoundError as exc:
            yield {"type": "error", "error_code": "TOOL_FILE_NOT_FOUND", "message": str(exc)}

    async def cancel(self, run_id: str) -> None:
        from runtime.services.run_execution import request_cancel

        request_cancel(run_id)
