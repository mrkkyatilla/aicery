#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "gate-providers-ext-live SKIP (ANTHROPIC_API_KEY not set)"
  exit 0
fi

python - <<'PY'
import asyncio
import os
import sys

from runtime.adapters.providers.anthropic import AnthropicProvider


async def main() -> None:
    provider = AnthropicProvider(
        os.environ["ANTHROPIC_API_KEY"],
        model=os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
    )
    text = await provider.complete([{"role": "user", "content": "Reply with exactly: live-ok"}])
    assert "live" in text.lower() or len(text) > 0
    chunks: list[str] = []
    async for token in provider.stream([{"role": "user", "content": "Say: stream-ok"}]):
        chunks.append(token)
    assert "".join(chunks).strip()
    print("gate-providers-ext-live OK")


asyncio.run(main())
PY
