from agents.registry import list_agent_manifests


def test_list_agent_manifests_includes_research_tools() -> None:
    agents = list_agent_manifests()
    research = next((a for a in agents if a["id"] == "research"), None)
    assert research is not None
    assert "search_workspace" in research["tools"]
    assert "research-chain" in research.get("pipelines", [])
