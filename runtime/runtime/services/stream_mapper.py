import json


def chunk_to_sse(chunk: dict) -> dict[str, str]:
    """Map orchestrator chunk to SSE event dict for EventSourceResponse."""
    chunk_type = chunk.get("type", "step")
    if chunk_type == "token":
        return {"event": "token", "data": json.dumps({"text": chunk.get("text", "")})}
    if chunk_type == "step":
        return {
            "event": "step",
            "data": json.dumps(
                {
                    "node": chunk.get("node", ""),
                    "index": chunk.get("index", 0),
                }
            ),
        }
    if chunk_type == "done":
        return {
            "event": "done",
            "data": json.dumps(
                {
                    "status": chunk.get("status", "completed"),
                    "run_id": chunk.get("run_id", ""),
                }
            ),
        }
    if chunk_type == "error":
        return {
            "event": "error",
            "data": json.dumps(
                {
                    "error_code": chunk.get("error_code", "RUN_FAILED"),
                    "message": chunk.get("message", ""),
                }
            ),
        }
    if chunk_type == "approval_required":
        return {
            "event": "approval_required",
            "data": json.dumps(
                {
                    "status": chunk.get("status", "awaiting_human_approval"),
                    "approval_id": chunk.get("approval_id", ""),
                    "tool_name": chunk.get("tool_name", ""),
                    "arguments": chunk.get("arguments", {}),
                    "expires_at": chunk.get("expires_at", ""),
                    "hitl_mode": chunk.get("hitl_mode", ""),
                    "interrupt_node": chunk.get("interrupt_node", ""),
                }
            ),
        }
    if chunk_type == "suspended":
        return {
            "event": "suspended",
            "data": json.dumps(
                {
                    "status": chunk.get("status", "suspended"),
                    "run_id": chunk.get("run_id", ""),
                    "approval_id": chunk.get("approval_id", ""),
                }
            ),
        }
    return {"event": chunk_type, "data": json.dumps(chunk)}
