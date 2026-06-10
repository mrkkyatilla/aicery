from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(prefix="/ui", tags=["ui"])

_STATIC = Path(__file__).resolve().parents[3] / "static" / "billing"


def _read_html(name: str) -> str:
    return (_STATIC / name).read_text(encoding="utf-8")


@router.get("/billing", response_class=HTMLResponse)
def billing_dashboard() -> HTMLResponse:
    return HTMLResponse(_read_html("index.html"))


@router.get("/billing/success", response_class=HTMLResponse)
def billing_success() -> HTMLResponse:
    return HTMLResponse(_read_html("success.html"))


@router.get("/billing/cancel", response_class=HTMLResponse)
def billing_cancel() -> HTMLResponse:
    return HTMLResponse(_read_html("cancel.html"))


@router.get("/billing/{asset_name}")
def billing_asset(asset_name: str) -> FileResponse:
    path = _STATIC / asset_name
    if not path.is_file() or asset_name not in {"app.js", "styles.css"}:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not found")
    media = "text/css" if asset_name.endswith(".css") else "application/javascript"
    return FileResponse(path, media_type=media)
