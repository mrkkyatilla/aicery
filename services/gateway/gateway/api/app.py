from contextlib import asynccontextmanager

from fastapi import FastAPI

from gateway.api.routes import admin, billing, health, internal, proxy, ui, webhooks
from gateway.config import Settings
from gateway.observability.middleware import otel_proxy_middleware
from gateway.observability.otel_setup import init_otel, shutdown_otel


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    init_otel(settings)
    yield
    shutdown_otel()


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title="Aicery Gateway",
        version=settings.api_version,
        lifespan=lifespan,
    )
    app.middleware("http")(otel_proxy_middleware)
    app.include_router(health.router)
    app.include_router(ui.router)
    app.include_router(admin.router)
    app.include_router(internal.router)
    app.include_router(billing.router)
    app.include_router(webhooks.router)
    app.include_router(proxy.router)
    return app


app = create_app()
