# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

sdlc-mcp: an open-source MCP server that serves hierarchical organizational context to AI agents. The server resolves a configurable hierarchy of named scopes, reads content from pluggable sources (local directories, git repos), merges with "most specific wins" semantics, and serves the result via MCP tools.

See [docs/design.md](docs/design.md) for the full design document.

## Commands

```bash
# Dependencies
uv sync

# Run the server
uv run sdlc-mcp serve

# Lint
uvx ruff check .
uvx ruff format .

# Tests
uv run pytest
```

## Architecture

**Config loading:** A config file is a YAML list of named scopes. Each scope has a `name`, optional `sources`, optional `repos` filter, and optional `include` list of `file://` or `github://` URIs. Scopes are processed top to bottom. Includes are resolved recursively before the including scope, so included content is the base and later scopes override.

**Hierarchy resolution:** Given a repo identifier, filter scopes to those that apply (no `repos` filter, or repo name matches). The org prefix is stripped, so `ansible/awx` and `shanemcd/awx` both match a scope with `repos: [awx]`.

**Content sources:** Pluggable adapters that read markdown files. `local` reads from a directory. `git` clones a repo and reads from a path within it.

**Merging:** "Most specific wins." If the team level has `testing.md` and the org level also has `testing.md`, the team version is used. Content that only exists at one level passes through unchanged. Merging is by filename within a category, not by concatenation.

**MCP tools:** Content tools are auto-generated from markdown frontmatter (one tool per artifact). `get_workflows(repo)` returns available workflows. `get_hierarchy(repo)` shows the resolution chain for debugging.

**Source layout:**

```
src/sdlc_mcp/
  __main__.py        # CLI entry point
  server.py          # FastMCP server + dynamic tool registration
  config.py          # Config loading, include resolution, scope merging
  hierarchy.py       # Hierarchy resolution engine
  repo.py            # Shared git clone/cache helpers
  workflows.py       # Workflow loading and merging
  sources/           # Pluggable content source adapters
    __init__.py      # Source protocol + frontmatter parsing
    local.py         # Local directory source
    git.py           # Git repo source
  merge.py           # Content merging logic
```

## Conventions

- Use `uv` for all Python package management
- Use proper `logging` module, never `print()`
- Source code under `src/sdlc_mcp/`
- Examples under `examples/`
- The server must be org-agnostic. No hardcoded references to any specific organization or tool. All org-specific knowledge comes from config and content.
- Config format is YAML
- Content sources are markdown files
- Use `fastmcp` (https://gofastmcp.com) for the MCP server, not the low-level `mcp` SDK. Import as `from fastmcp import FastMCP`. See https://gofastmcp.com/llms-full.txt for full API reference.

## Implementation Status

Phases 1-3 are complete (skeleton, git source, real content). Config includes, dynamic tool registration from frontmatter, workflow routing, and the scope-based config model are all implemented. See docs/design.md for the full design.
