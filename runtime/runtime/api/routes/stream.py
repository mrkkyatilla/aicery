import asyncio
import contextlib
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from runtime.api.auth import require_auth
from runtime.api.deps import RunServiceDep
from runtime.services.run_execution import get_run_execution
from runtime.services.stream_mapper import chunk_to_sse

router = APIRouter(
    prefix="/runs",
    tags=["stream"],
    dependencies=[Depends(require_auth)],
)


def _replay_completed(run) -> list[dict]:
    events: list[dict] = []
    output = (run.output_text or "").strip()
    if output:
        for i in range(0, len(output), 40):
            events.append({"type": "token", "text": output[i : i + 40]})
    events.append({"type": "done", "status": run.status.value, "run_id": run.id})
    return events


async def _disconnect_watcher(
    request: Request,
    service: RunServiceDep,
    run_id: str,
) -> None:
    """Cancel the run when the ASGI server signals http.disconnect."""
    try:
        while True:
            message = await request.receive()
            if message.get("type") == "http.disconnect":
                await service.cancel_run(run_id)
                return
    except asyncio.CancelledError:
        return


async def _sse_generator(run_id: str, service: RunServiceDep, request: Request):
    execution = get_run_execution(run_id)
    watcher: asyncio.Task | None = None
    if execution is not None:
        watcher = asyncio.create_task(_disconnect_watcher(request, service, run_id))

    try:
        async for event in _sse_event_stream(run_id, service, execution):
            yield event
    finally:
        if watcher is not None:
            watcher.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watcher


async def _sse_event_stream(
    run_id: str,
    service: RunServiceDep,
    execution,
):
    if execution is None:
        run, _, _ = await service.get_run_metrics(run_id)
        if run is None:
            yield {
                "event": "error",
                "data": json.dumps({"error_code": "NOT_FOUND", "message": "Run not found"}),
            }
            return
        for chunk in _replay_completed(run):
            yield chunk_to_sse(chunk)
        return

    sent = 0
    while sent < len(execution.history):
        yield chunk_to_sse(execution.history[sent])
        sent += 1
        if execution.history[sent - 1].get("type") in ("done", "error"):
            return

    while True:
        if execution.cancelled:
            yield {
                "event": "done",
                "data": json.dumps({"status": "cancelled", "run_id": run_id}),
            }
            break
        try:
            chunk = await asyncio.wait_for(execution.queue.get(), timeout=1.0)
        except TimeoutError:
            if execution.cancelled:
                yield {
                    "event": "done",
                    "data": json.dumps({"status": "cancelled", "run_id": run_id}),
                }
                break
            run = await service.get_run(run_id)
            if run and run.status.value in ("completed", "failed", "cancelled"):
                yield {
                    "event": "done",
                    "data": json.dumps({"status": run.status.value, "run_id": run_id}),
                }
                break
            continue
        yield chunk_to_sse(chunk)
        if chunk.get("type") in ("done", "error", "suspended"):
            break


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: str,
    request: Request,
    service: RunServiceDep,
) -> EventSourceResponse:
    run = await service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return EventSourceResponse(_sse_generator(run_id, service, request))
