from __future__ import annotations

import httpx
from opentelemetry.propagate import inject

from gateway.config import Settings
from gateway.observability.otel_setup import is_otel_active


class AiceryRuntimeClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._settings.aicery_service_api_key}

    def _merge_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        headers = self._headers()
        if extra_headers:
            headers.update(extra_headers)
        if is_otel_active():
            inject(headers)
        return headers

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        url = f"{self._settings.aicery_runtime_url.rstrip('/')}{path}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            return await client.request(
                method,
                url,
                headers=self._merge_headers(extra_headers),
                json=json,
                params=params,
            )

    async def stream(self, path: str) -> httpx.AsyncClient:
        """Returns an async context manager for streaming (caller manages lifecycle)."""
        raise NotImplementedError("Use stream_request on routes")

    async def stream_request(
        self,
        path: str,
        *,
        extra_headers: dict[str, str] | None = None,
    ):
        url = f"{self._settings.aicery_runtime_url.rstrip('/')}{path}"
        client = httpx.AsyncClient(timeout=None)
        request = client.build_request("GET", url, headers=self._merge_headers(extra_headers))
        response = await client.send(request, stream=True)
        return client, response
