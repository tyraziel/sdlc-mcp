# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

sdlc-context: an open-source MCP server that serves hierarchical organizational context to AI agents. The server resolves a configurable hierarchy (company > org > team > repo), reads content from pluggable sources (local directories, git repos), merges with "most specific wins" semantics, and serves the result via MCP tools.

See [docs/design.md](docs/design.md) for the full design document.

## Commands

```bash
# Dependencies
uv sync

# Run the server
uv run sdlc-context serve

# Lint
uvx ruff check .
uvx ruff format .

# Tests
uv run pytest
```

## Architecture

**Config loading:** Three levels merged in order (system + user + repo). System config from `/etc/sdlc-context/config.yml` or `$SDLC_CONTEXT_CONFIG`. User config from `~/.config/sdlc-context/config.yml`. Repo config from `.sdlc/config.yml` (optional). Each level can add content sources, override settings, or extend the hierarchy.

**Hierarchy resolution:** Given a repo identifier, walk the config to find: repo -> team -> org -> company. Gather content sources at each level. The team/repo mapping is defined in the config's `teams` section.

**Content sources:** Pluggable adapters that read markdown files. `local` reads from a directory. `git` clones a repo and reads from a path within it.

**Merging:** "Most specific wins." If the team level has `testing.md` and the org level also has `testing.md`, the team version is used. Content that only exists at one level passes through unchanged. Merging is by filename within a category, not by concatenation.

**MCP tools:** `get_context(repo, task)` returns merged context. `get_conventions(repo, category)` returns a specific category. `get_hierarchy(repo)` shows the resolution chain for debugging.

**Source layout:**

```
src/sdlc_context/
  __main__.py        # CLI entry point
  server.py          # FastMCP server + MCP tool definitions
  config.py          # Config loading + merging
  hierarchy.py       # Hierarchy resolution engine
  sources/           # Pluggable content source adapters
    __init__.py      # Source protocol
    local.py         # Local directory source
    git.py           # Git repo source
  merge.py           # Content merging logic
```

## Conventions

- Use `uv` for all Python package management
- Use proper `logging` module, never `print()`
- Source code under `src/sdlc_context/`
- Examples under `examples/`
- The server must be org-agnostic. No hardcoded references to any specific company, org, or tool (Jira, AWX, etc.). All org-specific knowledge comes from config and content.
- Config format is YAML
- Content sources are markdown files
- Use `fastmcp` (https://gofastmcp.com) for the MCP server, not the low-level `mcp` SDK. Import as `from fastmcp import FastMCP`. See https://gofastmcp.com/llms-full.txt for full API reference.

## Implementation Status

Phase 1 (skeleton) is the current focus. See docs/design.md "Implementation Plan" for all phases.
