"""Tests for MCP server tools."""

import asyncio

from sdlc_mcp.config import Config, Scope, SourceConfig
from sdlc_mcp.server import get_hierarchy, init_config, mcp, register_content_tools
from sdlc_mcp.sources import local as _local  # noqa: F401


def _list_tools():
    return asyncio.run(mcp._list_tools())


def _clear_dynamic_tools():
    static_tools = {"get_hierarchy", "get_workflows"}
    for tool in _list_tools():
        if tool.name not in static_tools:
            mcp.local_provider.remove_tool(tool.name)


def _setup_config(tmp_path):
    _clear_dynamic_tools()

    company_dir = tmp_path / "company"
    company_dir.mkdir()
    (company_dir / "security.md").write_text(
        '---\nname: security\ndescription: "Security standards"\n---\n'
        "# Security Standards\nPin all dependencies."
    )

    org_dir = tmp_path / "org"
    org_dir.mkdir()
    (org_dir / "testing.md").write_text(
        '---\nname: testing\ndescription: "Testing strategy and coverage"\n---\n'
        "# Testing Strategy\n80% coverage minimum."
    )

    team_dir = tmp_path / "team"
    team_dir.mkdir()
    (team_dir / "testing.md").write_text(
        '---\nname: testing\ndescription: "API testing conventions"\n---\n'
        "# API Testing\n90% coverage minimum."
    )

    config = Config(
        scopes=[
            Scope(
                name="acme",
                sources=[SourceConfig(type="local", path=str(company_dir))],
            ),
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(org_dir))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                sources=[SourceConfig(type="local", path=str(team_dir))],
            ),
        ]
    )
    init_config(config)
    return config


def test_dynamic_tools_registered(tmp_path):
    _setup_config(tmp_path)
    register_content_tools()

    tool_names = [t.name for t in _list_tools()]
    assert "security" in tool_names
    assert "testing" in tool_names


def test_dynamic_tool_uses_frontmatter_description(tmp_path):
    _setup_config(tmp_path)
    register_content_tools()

    tools = {t.name: t for t in _list_tools()}
    assert "API testing" in tools["testing"].description


def test_most_specific_description_wins(tmp_path):
    _setup_config(tmp_path)
    register_content_tools()

    tools = {t.name: t for t in _list_tools()}
    assert "API testing" in tools["testing"].description
    assert "Testing strategy" not in tools["testing"].description


def test_get_hierarchy_shows_chain(tmp_path):
    _setup_config(tmp_path)
    result = get_hierarchy(repo="acme/api-gateway")

    assert "acme" in result
    assert "platform" in result
    assert "api" in result


def test_get_hierarchy_unknown_repo(tmp_path):
    _setup_config(tmp_path)
    result = get_hierarchy(repo="unknown/repo")

    assert "acme" in result
    assert "platform" in result
    assert "api" not in result
