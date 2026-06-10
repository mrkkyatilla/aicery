import pytest

from tools.sandbox.jail import PathTraversalError, jail_path


def test_jail_allows_relative_path(tmp_path) -> None:
    f = tmp_path / "readme.txt"
    f.write_text("hi")
    target = jail_path(str(tmp_path), "readme.txt")
    assert target == f.resolve()


def test_jail_blocks_traversal(tmp_path) -> None:
    with pytest.raises(PathTraversalError):
        jail_path(str(tmp_path), "../../etc/passwd")
