from __future__ import annotations

import json

from runtime.config import Settings


class RedisHotMemory:
    def __init__(self, *, redis_url: str | None = None, ttl_sec: int | None = None) -> None:
        settings = Settings()
        self._redis_url = redis_url or settings.redis_url
        self._ttl_sec = ttl_sec if ttl_sec is not None else settings.hot_memory_ttl_sec
        self._client = None

    def _get_client(self):
        if self._client is None:
            import redis

            self._client = redis.from_url(self._redis_url, decode_responses=True)
        return self._client

    @staticmethod
    def _key(run_id: str) -> str:
        return f"hot:{run_id}"

    async def append_turn(self, run_id: str, role: str, content: str) -> None:
        client = self._get_client()
        key = self._key(run_id)
        turn = json.dumps({"role": role, "content": content})
        client.rpush(key, turn)
        client.expire(key, self._ttl_sec)

    async def get_recent_turns(self, run_id: str, limit: int = 20) -> list[dict]:
        client = self._get_client()
        key = self._key(run_id)
        raw_items = client.lrange(key, -limit, -1)
        turns: list[dict] = []
        for item in raw_items:
            try:
                turns.append(json.loads(item))
            except json.JSONDecodeError:
                continue
        return turns

    async def clear(self, run_id: str) -> None:
        client = self._get_client()
        client.delete(self._key(run_id))
        client.delete(f"{self._key(run_id)}:compacted")

    async def get_compacted_state(self, run_id: str) -> dict | None:
        client = self._get_client()
        raw = client.get(f"{self._key(run_id)}:compacted")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set_compacted_state(self, run_id: str, state: dict) -> None:
        client = self._get_client()
        key = f"{self._key(run_id)}:compacted"
        client.set(key, json.dumps(state), ex=self._ttl_sec)

    async def replace_turns_with_compacted(self, run_id: str, state: dict) -> None:
        client = self._get_client()
        key = self._key(run_id)
        payload = json.dumps(state, ensure_ascii=False)
        client.delete(key)
        client.rpush(key, json.dumps({"role": "assistant", "content": f"[compacted] {payload}"}))
        client.expire(key, self._ttl_sec)
        await self.set_compacted_state(run_id, state)
