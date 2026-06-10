from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.util._once import Once

if TYPE_CHECKING:
    from gateway.config import Settings

logger = logging.getLogger(__name__)

_provider: TracerProvider | None = None
_test_exporter: InMemorySpanExporter | None = None
_active = False


def is_otel_active() -> bool:
    return _active


def get_tracer(name: str = "aicery.gateway"):
    return trace.get_tracer(name)


def _set_provider(provider: TracerProvider) -> None:
    trace._TRACER_PROVIDER = provider  # type: ignore[attr-defined]
    trace._TRACER_PROVIDER_SET_ONCE = Once()  # type: ignore[attr-defined]


def _parse_resource_attributes(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    attrs: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        attrs[key.strip()] = value.strip()
    return attrs


def _build_otlp_exporter(settings: Settings) -> SpanExporter:
    endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/")
    protocol = settings.otel_exporter_otlp_protocol.lower()
    if protocol in ("grpc", "grpc/protobuf"):
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        return OTLPSpanExporter(endpoint=endpoint, insecure=True)
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    traces_path = "/v1/traces"
    if not endpoint.endswith(traces_path):
        endpoint = f"{endpoint}{traces_path}"
    return OTLPSpanExporter(endpoint=endpoint)


def init_otel(
    settings: Settings,
    *,
    test_exporter: InMemorySpanExporter | None = None,
) -> None:
    global _provider, _test_exporter, _active

    if _provider is not None:
        if test_exporter is None:
            return
        shutdown_otel()

    if test_exporter is not None:
        resource = Resource.create({"service.name": settings.otel_service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(SimpleSpanProcessor(test_exporter))
        _set_provider(provider)
        _provider = provider
        _test_exporter = test_exporter
        _active = True
        return

    if not settings.otel_enabled:
        return

    if not settings.otel_exporter_otlp_endpoint:
        logger.warning("OTEL_ENABLED=true but OTEL_EXPORTER_OTLP_ENDPOINT is unset; skipping OTEL init")
        return

    resource_attrs = {"service.name": settings.otel_service_name}
    resource_attrs.update(_parse_resource_attributes(settings.otel_resource_attributes))
    resource = Resource.create(resource_attrs)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(_build_otlp_exporter(settings)))
    _set_provider(provider)
    _provider = provider
    _active = True
    logger.info("Gateway OpenTelemetry initialized for %s", settings.otel_service_name)


def shutdown_otel() -> None:
    global _provider, _test_exporter, _active
    if _provider is not None:
        _provider.shutdown()
    trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]
    trace._TRACER_PROVIDER_SET_ONCE = Once()  # type: ignore[attr-defined]
    _provider = None
    _test_exporter = None
    _active = False


def get_test_exporter() -> InMemorySpanExporter | None:
    return _test_exporter
