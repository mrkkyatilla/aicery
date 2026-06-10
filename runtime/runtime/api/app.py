import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from runtime.adapters.db.session import get_session_factory
from runtime.adapters.events.factory import get_event_publisher, reset_event_publisher
from runtime.api.problem import register_problem_handlers
from runtime.api.routes import (
    agents,
    health,
    marketplace,
    route,
    runs,
    stream,
    trace,
    usage,
    workspace,
)
from runtime.config import Settings
from runtime.observability.graph_policy_context import (
    reset_max_graph_steps,
    set_max_graph_steps,
)
from runtime.observability.otel_setup import init_otel, shutdown_otel
from runtime.observability.request_context import reset_org_id, set_org_id
from runtime.services.hitl_sweeper import run_hitl_sweeper_loop

logger = logging.getLogger(__name__)


def _register_semantic_search() -> None:
    from runtime.config import Settings
    from tools.builtins.search_workspace import register_semantic_backend

    settings = Settings()
    if not settings.semantic_search_enabled:
        return

    def _backend(query: str, path: str = ".", max_hits: int = 50, *, workspace_root: str = "."):
        from runtime.intelligence.retriever import hybrid_search

        return hybrid_search(
            query,
            path=path,
            max_hits=max_hits,
            workspace_root=workspace_root,
            workspace_id=settings.default_workspace_id,
        )

    register_semantic_backend(_backend)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import tools.builtins.filesystem  # noqa: F401
    import tools.builtins.hitl_probe  # noqa: F401

    settings = Settings()
    from runtime.services.plugin_bootstrap import bootstrap_plugins

    bootstrap_plugins(settings)
    if settings.rate_limit_at_gateway_only:
        logger.warning(
            "RATE_LIMIT_AT_GATEWAY_ONLY=true: runtime rate limiting disabled; enforce at gateway"
        )
    init_otel(settings)
    _register_semantic_search()
    await get_event_publisher()
    sweeper_task: asyncio.Task | None = None
    if settings.hitl_enabled and settings.hitl_sweeper_enabled:
        sweeper_task = asyncio.create_task(
            run_hitl_sweeper_loop(get_session_factory(), settings=settings)
        )
    try:
        yield
    finally:
        if sweeper_task is not None:
            sweeper_task.cancel()
            try:
                await sweeper_task
            except asyncio.CancelledError:
                pass
        reset_event_publisher()
        shutdown_otel()


async def _org_id_middleware(request: Request, call_next):
    settings = Settings()
    org_id = request.headers.get("X-Aicery-Org-Id")
    org_token = set_org_id(org_id) if org_id else None
    steps_token = None
    if settings.trust_gateway_headers:
        raw_steps = request.headers.get("X-Aicery-Max-Steps")
        if raw_steps:
            try:
                steps_token = set_max_graph_steps(int(raw_steps))
            except ValueError:
                pass
    try:
        return await call_next(request)
    finally:
        if steps_token is not None:
            reset_max_graph_steps(steps_token)
        if org_token is not None:
            reset_org_id(org_token)


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title="Aicery Runtime",
        version=settings.api_version,
        lifespan=lifespan,
    )
    app.middleware("http")(_org_id_middleware)
    register_problem_handlers(app)
    app.include_router(health.router)
    app.include_router(runs.router, prefix="/v1")
    app.include_router(trace.router, prefix="/v1")
    app.include_router(usage.router, prefix="/v1")
    app.include_router(stream.router, prefix="/v1")
    app.include_router(agents.router, prefix="/v1")
    app.include_router(workspace.router, prefix="/v1")
    app.include_router(route.router, prefix="/v1")
    app.include_router(marketplace.router, prefix="/v1")
    return app


app = create_app()
