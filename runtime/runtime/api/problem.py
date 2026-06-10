from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from core.domain.errors import InvalidStateTransitionError
from runtime.api.rate_limit import RateLimitedError


def problem_response(
    *,
    status: int,
    title: str,
    detail: str,
    error_code: str | None = None,
) -> JSONResponse:
    body: dict = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
    }
    if error_code:
        body["error_code"] = error_code
    return JSONResponse(status_code=status, content=body, media_type="application/problem+json")


def register_problem_handlers(app) -> None:
    @app.exception_handler(InvalidStateTransitionError)
    async def invalid_transition_handler(
        _request: Request, exc: InvalidStateTransitionError
    ) -> JSONResponse:
        return problem_response(
            status=409,
            title="Conflict",
            detail=str(exc),
            error_code=exc.error_code,
        )

    @app.exception_handler(RateLimitedError)
    async def rate_limited_handler(
        _request: Request, exc: RateLimitedError
    ) -> JSONResponse:
        return problem_response(
            status=429,
            title="Too Many Requests",
            detail=str(exc),
            error_code=exc.error_code,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        error_code = "RATE_LIMITED" if exc.status_code == 429 else None
        return problem_response(
            status=exc.status_code,
            title="Error",
            detail=detail,
            error_code=error_code,
        )
