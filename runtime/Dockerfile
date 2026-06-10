# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Slow/unstable PyPI during build → longer timeouts + retries (uv exit code 2).
ENV UV_HTTP_TIMEOUT=300 \
    UV_CONNECT_TIMEOUT=120 \
    UV_RETRIES=5 \
    PIP_DEFAULT_TIMEOUT=300

RUN pip install --no-cache-dir uv

COPY core /app/core
COPY agents /app/agents
COPY tools /app/tools
COPY runtime /app/runtime
COPY README.md /app/README.md

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e /app/core -e /app/agents -e /app/tools -e /app/runtime

WORKDIR /app/runtime

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "runtime.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
