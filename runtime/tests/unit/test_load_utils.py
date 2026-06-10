from tests.load.load_utils import stream_first_token_ms


class _FakeStream:
    def __init__(self, lines: list[str]) -> None:
        self._lines = iter(lines)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self):
        yield from self._lines


class _FakeClient:
    def stream(self, method: str, url: str, **kwargs):
        assert method == "GET"
        return _FakeStream(
            [
                "event: token",
                'data: {"type":"token","text":"hi"}',
            ]
        )


def test_stream_first_token_ms_parses_token_event() -> None:
    ms = stream_first_token_ms(_FakeClient(), "run-1")  # type: ignore[arg-type]
    assert ms >= 0.0
