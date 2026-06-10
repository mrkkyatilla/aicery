from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

import httpx

from tools.registry import tool

BLOCKED_METADATA_IPS = frozenset(
    {
        "169.254.169.254",
        "127.0.0.1",
        "0.0.0.0",
        "localhost",
    }
)


class SSRFBlocked(Exception):
    error_code = "SSRF_BLOCKED"


class HostNotAllowed(Exception):
    error_code = "HOST_NOT_ALLOWED"


def _allowed_hosts() -> set[str]:
    raw = os.environ.get("ALLOWED_HTTP_HOSTS", "api.github.com,httpbin.org")
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def _resolve_ips(hostname: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise HostNotAllowed(f"Cannot resolve host: {hostname}") from exc
    return [info[4][0] for info in infos]


def _assert_host_allowed(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HostNotAllowed(f"Unsupported scheme: {parsed.scheme}")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise HostNotAllowed("Missing hostname")
    if hostname in BLOCKED_METADATA_IPS:
        raise SSRFBlocked(f"Blocked host: {hostname}")
    for ip_str in _resolve_ips(hostname):
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or str(ip) in BLOCKED_METADATA_IPS
        ):
            raise SSRFBlocked(f"Blocked IP for host {hostname}: {ip}")
    if hostname not in _allowed_hosts():
        raise HostNotAllowed(f"Host not in allowlist: {hostname}")


HTTP_REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string"},
        "method": {"type": "string"},
        "headers": {"type": "object"},
        "body": {"type": "string"},
    },
    "required": ["url"],
}


@tool("http_request", HTTP_REQUEST_SCHEMA)
def http_request(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    body: str | None = None,
    *,
    workspace_root: str = ".",  # noqa: ARG001
) -> dict:
    _assert_host_allowed(url)
    with httpx.Client(timeout=30.0, follow_redirects=False) as client:
        response = client.request(
            method.upper(),
            url,
            headers=headers or {},
            content=body.encode() if body else None,
        )
    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": response.text[:8000],
    }
