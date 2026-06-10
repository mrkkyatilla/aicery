import pytest

from tools.builtins.http_request import (
    HostNotAllowed,
    SSRFBlocked,
    _assert_host_allowed,
)


def test_ssrf_metadata_ip_blocked() -> None:
    with pytest.raises(SSRFBlocked):
        _assert_host_allowed("http://169.254.169.254/latest/meta-data/")


def test_host_not_in_allowlist() -> None:
    with pytest.raises(HostNotAllowed):
        _assert_host_allowed("http://evil.example/")
