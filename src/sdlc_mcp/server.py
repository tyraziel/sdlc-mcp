"""FastMCP server with MCP tool definitions."""

from __future__ import annotations

import logging
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.tools import Tool

from .config import Config, load_config
from .hierarchy import resolve_hierarchy
from .merge import merge_content, merge_content_for_category, merge_workflows_for_hierarchy
from .workflows import format_workflow_list

# Ensure source adapters are registered
from .sources import git as _git, local as _local  # noqa: F401

logger = logging.getLogger(__name__)

mcp = FastMCP("sdlc-mcp")

_config: Config | None = None



def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def init_config(config: Config) -> None:
    global _config
    _config = config


def init_config_from_path(
    config_paths: list[Path] | None = None,
    repo_path: Path | None = None,
) -> None:
    global _config
    _config = load_config(repo_path=repo_path, config_paths=config_paths)
    register_content_tools()


def _scope_has_category(scope, category: str) -> bool:
    filename = f"{category}.md"
    for source in scope.sources:
        if source.type == "local" and source.path:
            path = Path(source.path)
            if path.is_dir() and (path / filename).exists():
                return True
            if path.is_file() and path.name == filename:
                return True
    return False


def _make_content_tool(category: str, description: str):
    """Create a tool function that returns content for a specific category."""

    def tool_fn(repo: str | None = None) -> str:
        config = get_config()

        hierarchy = resolve_hierarchy(config, repo or "")
        item = merge_content_for_category(hierarchy, category)

        if item is None:
            available = [
                s.name for s in config.scopes
                if s.repos and _scope_has_category(s, category)
            ]
            if available:
                return (
                    f"No matching content for {category!r}."
                    f" Available for: {', '.join(available)}"
                )
            return f"No content found for {category!r}"

        return item.content

    tool_fn.__name__ = f"{category.replace('-', '_')}"
    tool_fn.__qualname__ = tool_fn.__name__
    return tool_fn


def register_content_tools() -> None:
    """Scan all content sources and register a tool per artifact."""
    config = get_config()

    if not config.scopes:
        return

    first_repo = ""
    for scope in config.scopes:
        if scope.repos:
            first_repo = scope.repos[0]
            break

    hierarchy = resolve_hierarchy(config, first_repo)
    merged = merge_content(hierarchy)

    for filename in merged.filenames():
        item = merged.items[filename]
        category = filename.removesuffix(".md")
        tool_name = f"{category.replace('-', '_')}"

        description = item.tool_description
        if not description:
            first_line = item.content.strip().split("\n", 1)[0].lstrip("# ").strip()
            description = first_line

        fn = _make_content_tool(category, description)
        tool = Tool.from_function(fn, name=tool_name, description=description)
        mcp.add_tool(tool)

    logger.info("Registered %d content tools", len(merged.items))


@mcp.tool()
def get_hierarchy(repo: str | None = None) -> str:
    """Show the resolved hierarchy for a repo.

    Useful for debugging: 'why did the agent get this context?'

    Args:
        repo: Repository name (e.g., "awx"). Optional.
    """
    config = get_config()

    hierarchy = resolve_hierarchy(config, repo or "")

    lines = [f"Hierarchy for {repo!r}:", ""]
    for level in hierarchy.levels:
        lines.append(f"  {level.level}: {level.name}")
        for source in level.sources:
            if source.url:
                lines.append(f"    - {source.type}: {source.url} ({source.path})")
            else:
                lines.append(f"    - {source.type}: {source.path}")

    if not hierarchy.levels:
        lines.append("  (no hierarchy levels matched)")

    return "\n".join(lines)


@mcp.tool()
def get_workflows(repo: str | None = None) -> str:
    """Get available workflows for a repo.

    Returns all workflows defined for this repo's hierarchy, including
    triggers, Jira issue types, required capabilities, and descriptions.
    The caller (human or AI) decides which workflow to use.

    Args:
        repo: Repository name (e.g., "awx"). Optional.
    """
    config = get_config()

    hierarchy = resolve_hierarchy(config, repo or "")
    workflows = merge_workflows_for_hierarchy(hierarchy)

    if not workflows:
        return f"No workflows defined for repo {repo!r}"

    return format_workflow_list(workflows)
