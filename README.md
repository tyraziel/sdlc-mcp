# sdlc-mcp

An open-source MCP server that gives AI agents a table of contents for your entire platform.

## Why

AI agents need organizational knowledge to do real work: how to write a Jira story, how code reviews are conducted, what the testing standards are. This knowledge exists at different levels (org-wide, team-specific, repo-specific) and some of it can't live in public repos.

Putting everything in CLAUDE.md doesn't scale across repos. Loading everything upfront wastes the context window. And when the agent sees both an org-level and team-level version of the same thing, it has to guess which one wins.

This server solves all three problems. Content is served on demand (the agent pulls only what it needs), managed centrally (update once, every agent gets it), and merged with a clear hierarchy (later scopes override earlier ones, so the agent only ever sees the winning version).

## How the Hierarchy Works

The config is a YAML list of named scopes, processed top to bottom. Each scope points at content sources. Scopes without a `repos` filter apply to all repos. Scopes with `repos` only apply when the requested repo matches.

```yaml
- name: platform                      # org-wide, applies to all repos
  sources:
    - type: local
      path: content/org/

- name: api                           # only applies to api-gateway, api-auth
  repos: [api-gateway, api-auth]
  sources:
    - type: local
      path: content/teams/api/
```

If both `platform` and `api` have a `testing.md`, the `api` version wins for matching repos. Everything else inherits from the org level. The merge happens server-side. The agent never sees conflicting content, just the right answer.

Scopes can also include external configs via `file://` or `github://` URIs, so content can be spread across multiple repos, public and private.

## How Content Becomes Tools

Content is markdown with YAML frontmatter. Each file automatically becomes an MCP tool:

```markdown
---
name: org-structure
description: "How the organization is structured"
---

# Organization Structure
...
```

The agent sees the full table of contents the moment it connects. No CLAUDE.md hints needed. It calls the tool it needs and gets just that content.

## Quick Start

The simplest way to use this is through a content package that bundles your config and content together as a Python package. The content package depends on `sdlc-mcp`, so a single `uvx` command starts the server with everything included.

To run directly:

```bash
uv run sdlc-mcp serve --config path/to/config.yml
```

To register with Claude Code:

```bash
claude mcp add --transport stdio --scope project sdlc-mcp \
  -- uv run --project /path/to/sdlc-mcp sdlc-mcp serve \
  --config /path/to/config.yml
```

## Design

See [docs/design.md](docs/design.md) for the full design document.
