# Context-as-a-Service: Dynamic SDLC Context Delivery via MCP

## Context

Organizations need to deliver organizational context to AI agents working across many repositories and teams. This context exists at multiple levels:

- **Org-wide:** architecture principles, design process, testing strategy, issue tracking conventions
- **Team:** component ownership, team testing patterns, review conventions
- **Repo:** language, framework, directory structure, CI setup

Different audiences need different subsets. Community contributors working on public upstream repos should only see what's in the repo. Employees need the internal organizational context layered on top, without that context being visible in the repo itself.

## The Idea

**An open-source MCP server that resolves hierarchical context on demand. The server is generic infrastructure. The content and config are pluggable and private.**

The server itself knows nothing about any specific organization. It reads a config that defines a hierarchy of named scopes, points at content sources (markdown in git repos, local directories), resolves the hierarchy with "most specific wins" semantics, and serves the merged result via MCP tools. Any organization can use it.

What makes it work for a specific org is the *config*: a private config that maps repos to teams, points at internal standards repos, and defines the hierarchy. This config lives in a private repo or a container image. The server is open. The knowledge is private.

### Why MCP?

MCP is a context protocol. Agents already connect to remote services over MCP to get tools. The Skills Over MCP Working Group (SEP-2640) is standardizing how to serve structured workflow instructions through the same channel.

Building on MCP means the solution works with any MCP-capable agent (not just Claude Code) and aligns with the ecosystem direction.

## Architecture

### Source Layout

```
sdlc-mcp/
  src/sdlc_mcp/
    __main__.py        # CLI entry point (serve command)
    server.py          # FastMCP server, dynamic tool registration
    config.py          # Config loading, include resolution, scope merging
    hierarchy.py       # Hierarchy resolution engine
    repo.py            # Shared git clone/cache helpers
    sources/           # Pluggable content source adapters
      __init__.py      # Source protocol + frontmatter parsing
      local.py         # Read from a local directory or file
      git.py           # Clone a repo, read markdown from a path
    merge.py           # "Most specific wins" content merging
  examples/            # Sample configs and content for testing
  docs/
    design.md          # This file
  pyproject.toml
  README.md
  CLAUDE.md
```

The server is generic. It doesn't know about any specific organization. It knows how to:
1. Load config (a YAML list of named scopes with optional includes)
2. Read content from pluggable sources (git repos, local dirs)
3. Resolve a hierarchy (filter scopes by repo name)
4. Merge content at each level (most specific wins)
5. Serve the result via auto-generated MCP tools

### Config Format

A config file is a YAML list of named scopes, processed top to bottom. Each scope has a `name`, optional `sources`, optional `repos` filter, and optional `include` list. Later scopes override earlier ones for same-name content files.

```yaml
- name: acme
  sources:
    - type: local
      path: content/org/

- name: api
  repos: [api-gateway, api-auth]
  sources:
    - type: local
      path: content/teams/api/

- name: frontend
  repos: [web-app, design-system]
  sources:
    - type: local
      path: content/teams/frontend/
```

Scopes with a `repos` filter only apply when the requested repo matches. The org prefix is stripped during matching, so `acme/api-gateway`, `fork/api-gateway`, and `api-gateway` all match `repos: [api-gateway]`. Scopes also match by name, so `repo: "api"` matches the `api` scope directly.

Includes resolve `file://` (local paths, absolute or relative) and `github://` (clones via git) URIs. Included configs are processed before the including scope, so they provide the base that later scopes override.

### MCP Tools

Content tools are auto-generated from markdown frontmatter at server startup. Each content file with YAML frontmatter (`name`, `description`) becomes a tool:

```markdown
---
name: code-review
description: "How code reviews should be conducted"
---
# Code Review
...
```

This registers as `code_review(repo)` with the description visible in the agent's tool list. The agent sees the full table of contents without a discovery call.

### Content Resolution Flow

```
Agent calls code_review(repo="api-gateway")
  |
  v
Config loaded, includes resolved recursively.
  |
  v
Scope filtering:
  1. repo name = "api-gateway" (org prefix stripped)
  2. Scopes without repos filter: acme (applies to all)
  3. Scopes with matching repos filter: api (repos: [api-gateway])
  4. Scopes with non-matching repos filter: frontend (skipped)
  |
  v
Source reader fetches content from each matching scope, in order:
  - acme: security.md, testing.md, code-review.md
  - api: testing.md, api-conventions.md
  |
  v
Merger combines with "most specific wins":
  - api's testing.md overrides acme's testing.md
  - acme's code-review.md passes through (no api override)
  |
  v
Returns the requested content file to agent
```

## SEP-2640 Compatibility (Skills Over MCP)

The architecture is designed so that SEP-2640 support is an additive layer, not a rewrite. The core logic (load config, resolve hierarchy, merge content) is the same regardless of delivery mechanism.

**Today:** Content is served via auto-generated MCP tools (one per content file).

**When SEP-2640 lands:** The same server could additionally register `skill://` resources. This gives automatic host-side discovery, progressive disclosure, and UI integration for free, without changing the resolution engine.

## Tradeoffs

**Gains:**
- Open-source, org-agnostic server
- No files in public repos
- Central maintenance (update once, apply everywhere)
- Server-side hierarchy resolution (one call, no chain to debug)
- Works with any MCP agent

**Costs:**
- Content pipeline has sync latency (mitigated: `--refresh` pulls latest on session start)
- Someone builds and maintains the content

## Implementation Plan

### Phase 1: Skeleton (done)
- Python project with `uv`, FastMCP server
- Config loading and merging
- Hierarchy resolution engine
- Local directory source adapter
- Sample config and content for testing

### Phase 2: Git source adapter (done)
- Git repo cloning as a content source
- Clone caching with pull-on-reuse

### Phase 3: Config and tool evolution (done)
- Scope-based config model (YAML list of named scopes)
- Config includes (`file://`, `github://`) with recursive resolution
- Dynamic tool registration from markdown frontmatter
- Repo name matching (org prefix stripped, scope name matching)
- Content as individual artifact files with frontmatter

### Phase 4: SEP-2640 skill:// resource layer
- Register `skill://` resources for workflow content
- Same resolution engine, different transport wrapper
- Hosts that support the spec get automatic discovery and UI integration

### Phase 5: Distribution
- Container image integration
- Open-source docs and onboarding
