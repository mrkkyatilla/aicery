from __future__ import annotations

import hashlib
import json


def _sha256_hex(payload: dict | str) -> str:
    if isinstance(payload, dict):
        raw = json.dumps(payload, sort_keys=True, default=str).encode()
    else:
        raw = payload.encode()
    return hashlib.sha256(raw).hexdigest()


def hash_messages(messages: list[dict], *, model: str = "") -> str:
    return _sha256_hex({"model": model, "messages": messages})


def hash_tool_input(tool_name: str, arguments: dict) -> str:
    return _sha256_hex({"tool": tool_name, "arguments": arguments})


def hash_text(text: str) -> str:
    return _sha256_hex(text)


def preview_text(text: str, *, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
