from __future__ import annotations

import asyncio
import logging
import queue
import threading
from collections.abc import AsyncIterator, Iterator

logger = logging.getLogger(__name__)


from core.domain.usage import LlmUsage
from runtime.adapters.providers.errors import ProviderError, TransientProviderError
from runtime.adapters.providers.usage_helpers import estimate_usage, usage_from_gemini_metadata

__all__ = ["GeminiProvider", "ProviderError", "TransientProviderError"]


class GeminiProvider:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self._api_key = api_key
        self._model = model
        self.last_usage: LlmUsage | None = None

    async def complete(self, messages: list[dict], **kwargs) -> str:
        for attempt in range(3):
            try:
                return await asyncio.to_thread(self._generate_sync, messages, **kwargs)
            except TransientProviderError:
                if attempt == 2:
                    raise
                await asyncio.sleep(2**attempt)
        raise ProviderError("Provider failed after retries")

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        for attempt in range(3):
            try:
                async for token in self._stream_once(messages, **kwargs):
                    yield token
                return
            except TransientProviderError:
                if attempt == 2:
                    raise
                await asyncio.sleep(2**attempt)

    async def _stream_once(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        event_queue: queue.Queue[tuple[str, str | BaseException | None]] = queue.Queue()

        def producer() -> None:
            try:
                for token in self._stream_sync(messages, **kwargs):
                    event_queue.put(("token", token))
                event_queue.put(("done", None))
            except BaseException as exc:
                event_queue.put(("error", exc))

        thread = threading.Thread(target=producer, daemon=True)
        thread.start()
        while True:
            kind, payload = await asyncio.to_thread(event_queue.get)
            if kind == "done":
                break
            if kind == "error":
                raise self._wrap_error(payload)  # type: ignore[arg-type]
            yield payload  # type: ignore[misc]

    def _client(self):
        from google import genai

        return genai.Client(api_key=self._api_key)

    @staticmethod
    def _contents(messages: list[dict]) -> str:
        return "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
        )

    def _generate_sync(self, messages: list[dict], **kwargs) -> str:
        client = self._client()
        try:
            response = client.models.generate_content(
                model=self._model,
                contents=self._contents(messages),
            )
            text = response.text or ""
            meta = getattr(response, "usage_metadata", None)
            self.last_usage = usage_from_gemini_metadata(
                meta, provider="gemini", model=self._model
            ) or estimate_usage(messages, text, provider="gemini", model=self._model)
            return text
        except Exception as exc:
            raise self._wrap_error(exc) from exc

    def _stream_sync(self, messages: list[dict], **kwargs) -> Iterator[str]:
        client = self._client()
        try:
            output_parts: list[str] = []
            last_meta = None
            for chunk in client.models.generate_content_stream(
                model=self._model,
                contents=self._contents(messages),
            ):
                last_meta = getattr(chunk, "usage_metadata", None) or last_meta
                if chunk.text:
                    output_parts.append(chunk.text)
                    yield chunk.text
            text = "".join(output_parts)
            self.last_usage = usage_from_gemini_metadata(
                last_meta, provider="gemini", model=self._model
            ) or estimate_usage(messages, text, provider="gemini", model=self._model)
        except Exception as exc:
            raise self._wrap_error(exc) from exc

    def _wrap_error(self, exc: BaseException) -> ProviderError:
        try:
            from google.genai.errors import APIError, ClientError, ServerError
        except ImportError:
            return ProviderError(str(exc))

        if isinstance(exc, (ServerError, APIError)):
            code = getattr(exc, "code", None)
            if code in (429, 503, "429", "503", "UNAVAILABLE"):
                return TransientProviderError(str(exc))
        if isinstance(exc, ClientError):
            code = getattr(exc, "code", None)
            if code in (429, 503, "429", "503", "UNAVAILABLE"):
                return TransientProviderError(str(exc))
        message = str(exc)
        if "503" in message or "429" in message or "UNAVAILABLE" in message:
            return TransientProviderError(message)
        return ProviderError(str(exc))
