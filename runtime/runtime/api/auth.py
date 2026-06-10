from fastapi import Header, HTTPException, status

from runtime.api.jwt_auth import decode_token
from runtime.api.rate_limit import RateLimitedError, check_rate_limit
from runtime.config import Settings


async def _check_rate_for_principal(principal: str) -> None:
    try:
        await check_rate_limit(principal)
    except RateLimitedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc


async def require_auth(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    settings = Settings()

    if settings.jwt_enabled and authorization:
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header",
            )
        token = authorization[7:].strip()
        try:
            claims = decode_token(token, settings=settings)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from None
        principal = str(claims.get("sub", "jwt-user"))
        await _check_rate_for_principal(principal)
        return principal

    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
        )
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    await _check_rate_for_principal(x_api_key)
    return x_api_key


async def require_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> str:
    """Backward-compatible alias; prefer require_auth on new routes."""
    return await require_auth(x_api_key=x_api_key)
