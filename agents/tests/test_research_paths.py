from agents.graphs.research_paths import extract_path


def test_extract_path_prefers_longest_slash_path():
    text = (
        "Read docs/MVP_SCOPE.md or examples/research-docs/docs/MVP_SCOPE.md "
        "for MVP scope."
    )
    assert extract_path(text) == "examples/research-docs/docs/MVP_SCOPE.md"
