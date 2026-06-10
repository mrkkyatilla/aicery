FROM python:3.12-slim

WORKDIR /app
COPY core /app/core
COPY services/gateway/pyproject.toml services/gateway/
COPY services/gateway/gateway services/gateway/gateway
COPY services/gateway/static services/gateway/static
COPY services/gateway/alembic services/gateway/alembic
COPY services/gateway/alembic.ini services/gateway/

RUN pip install --no-cache-dir -e ./core "./services/gateway[dev]"

WORKDIR /app/services/gateway
ENV PYTHONPATH=/app/services/gateway

EXPOSE 8081
CMD ["uvicorn", "gateway.api.app:app", "--host", "0.0.0.0", "--port", "8081"]
