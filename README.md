# sdlc-mcp

An MCP server that serves hierarchical organizational context to AI agents.

Organizations have standards, conventions, and process knowledge at multiple levels: org, team, and repo. This server resolves those layers on demand, merges them with "most specific wins" semantics, and serves the result via MCP tools. The server is generic. The content and config are yours.

## Quick Start

```bash
uv sync
uv run sdlc-mcp serve --config path/to/config.yml
```

Register with Claude Code:

```bash
claude mcp add --transport stdio --scope user sdlc-mcp \
  -- uv run --project /path/to/sdlc-mcp sdlc-mcp serve \
  --config /path/to/your/config.yml
```

## How It Works

The server reads a config that defines named scopes with content sources. Each scope can optionally filter by repo name. When an agent calls a tool, the server:

1. Filters scopes to those applicable to the repo (org prefix is ignored)
2. Reads content from sources at each scope
3. Merges with "most specific wins" (later scopes override earlier ones)
4. Returns the result

### Config

A config file is a YAML list of named scopes:

```yaml
- name: acme
  sources:
    - type: local
      path: content/org/

- name: platform
  sources:
    - type: local
      path: content/org/

- name: api
  repos: [api-gateway, api-auth]
  sources:
    - type: local
      path: content/teams/api/
```

Scopes can include external configs via `file://` or `github://` URIs:

```yaml
- name: org
  include:
    - file://base.yml
    - github://myorg/standards
  sources:
    - type: local
      path: content/
```

Config is also loaded from standard paths (each overrides the previous):

| Level | Path | Purpose |
|---|---|---|
| System | `/etc/sdlc-mcp/config.yml` or `$SDLC_MCP_CONFIG` | Org defaults |
| User | `~/.config/sdlc-mcp/config.yml` | Personal overrides |
| Repo | `.sdlc/config.yml` (optional) | Repo-specific sources |

### MCP Tools

Content tools are **auto-generated** from markdown frontmatter. Each content file with frontmatter becomes its own tool:

```markdown
---
name: code-review
description: "Code review methodology: 3-lens scoring, evidence gate"
---

# Code Review
...
```

This registers as `get_code_review` with the description visible in the agent's tool list. The agent sees the full table of contents without making a discovery call.

Static tools:

| Tool | Purpose |
|---|---|
| `get_workflows(repo)` | Available workflows for a repo |
| `get_hierarchy(repo)` | Show the resolved hierarchy (for debugging) |

### Content Sources

| Type | Description |
|---|---|
| `local` | Read markdown from a local directory or file |
| `git` | Clone a repo and read from a path within it |

## Design

See [docs/design.md](docs/design.md) for the full design document.
