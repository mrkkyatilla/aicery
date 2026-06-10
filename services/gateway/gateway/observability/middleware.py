from __future__ import annotations

from opentelemetry import trace
from opentelemetry.propagate import extract
from starlette.requests import Request

from gateway.observability.otel_setup import get_tracer, is_otel_active


async def otel_proxy_middleware(request: Request, call_next):
    if not is_otel_active():
        return await call_next(request)

    ctx = extract(dict(request.headers))
    tracer = get_tracer()
    route = request.url.path
    with tracer.start_as_current_span(
        "gateway.proxy",
        context=ctx,
        attributes={"http.route": route, "http.method": request.method},
    ):
        response = await call_next(request)
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("http.status_code", response.status_code)
        return response
