from pathlib import Path

from tools.builtins.search_workspace import search_workspace


def test_search_workspace_finds_readme(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Aicery runtime MVP\n")
    result = search_workspace("Aicery", path=".", workspace_root=str(tmp_path))
    assert result["hits"]
    assert any("README" in hit["file"] for hit in result["hits"])
