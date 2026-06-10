from tools.registry import tool

HITL_PROBE_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string"},
        "target": {"type": "string"},
    },
    "required": ["action"],
}


@tool("hitl_probe", HITL_PROBE_SCHEMA)
def hitl_probe(action: str, target: str = "", *, workspace_root: str = ".") -> dict:
    del workspace_root
    return {"status": "ok", "action": action, "target": target}
