"""Config loading and merging.

A config file is a YAML list of named scopes, processed top to bottom.
Each scope has a name, optional sources, optional repo filter, and
optional includes (external file/repo references). Later scopes override
earlier ones. The hierarchy is the list order.

Example:
    - name: aap
      sources:
        - type: local
          path: content/org/

    - name: controller
      repos: [awx, controller]
      sources:
        - type: local
          path: content/teams/controller/
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import yaml

logger = logging.getLogger(__name__)

SYSTEM_CONFIG_PATH = Path("/etc/sdlc-mcp/config.yml")
USER_CONFIG_PATH = Path.home() / ".config" / "sdlc-mcp" / "config.yml"
CONFIG_FILENAME = "config.yml"
SDLC_DIR = ".sdlc"


@dataclass
class SourceConfig:
    type: str
    path: str = ""
    url: str = ""
    ref: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceConfig:
        return cls(
            type=data["type"],
            path=data.get("path", ""),
            url=data.get("url", ""),
            ref=data.get("ref", ""),
        )


@dataclass
class Scope:
    name: str
    sources: list[SourceConfig] = field(default_factory=list)
    repos: list[str] = field(default_factory=list)


@dataclass
class Config:
    scopes: list[Scope] = field(default_factory=list)

    def scopes_for_repo(self, repo: str) -> list[Scope]:
        name = repo.rsplit("/", 1)[-1]
        return [s for s in self.scopes if not s.repos or name in s.repos or name == s.name]


def _parse_sources(data: dict[str, Any]) -> list[SourceConfig]:
    return [SourceConfig.from_dict(s) for s in data.get("sources", [])]


def _resolve_source_paths(sources: list[SourceConfig], base_dir: Path) -> None:
    for source in sources:
        if source.type == "local" and source.path and not Path(source.path).is_absolute():
            source.path = str(base_dir / source.path)


def _parse_scope(data: dict[str, Any]) -> Scope:
    return Scope(
        name=data.get("name", ""),
        sources=_parse_sources(data),
        repos=data.get("repos", []),
    )


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    logger.debug("Loading config from %s", path)
    with open(path) as f:
        return yaml.safe_load(f)


class IncludeError(Exception):
    pass


def _resolve_include_uri(uri: str, base_dir: Path) -> tuple[Path, Path]:
    """Resolve an include URI to (config_file_path, base_dir_for_paths).

    Raises IncludeError if the include cannot be resolved.
    """
    if uri.startswith("file://"):
        raw_path = uri[7:]
        path = Path(raw_path)
        if not path.is_absolute():
            path = base_dir / path
        path = path.resolve()

        if path.is_file():
            return path, path.parent
        config_file = path / CONFIG_FILENAME
        sdlc_config = path / SDLC_DIR / CONFIG_FILENAME
        if config_file.exists():
            return config_file, path
        if sdlc_config.exists():
            return sdlc_config, path
        raise IncludeError(f"Include {uri}: no config.yml found at {path}")

    if uri.startswith("git+"):
        from .repo import CACHE_DIR, cache_key, ensure_cloned

        raw = uri[4:]
        qmark = raw.find("?")
        if qmark >= 0:
            repo_url = raw[:qmark]
            params = parse_qs(raw[qmark + 1 :])
        else:
            repo_url = raw
            params = {}

        ref = params.get("ref", [""])[0]
        config_path = params.get("path", [""])[0]

        key = cache_key(repo_url, ref)
        dest = CACHE_DIR / key

        ensure_cloned(repo_url, ref, dest)

        if not dest.exists():
            raise IncludeError(f"Include {uri}: clone failed")

        config_dir = dest / config_path if config_path else dest

        config_file = config_dir / CONFIG_FILENAME
        sdlc_config = config_dir / SDLC_DIR / CONFIG_FILENAME
        if config_file.exists():
            return config_file, config_dir
        if sdlc_config.exists():
            return sdlc_config, config_dir
        raise IncludeError(f"Include {uri}: no config.yml found in cloned repo")

    raise IncludeError(f"Unknown include scheme: {uri}")


def _load_scopes(
    path: Path,
    base_dir: Path,
    seen: set[str] | None = None,
) -> list[Scope]:
    """Load scopes from a config file, resolving includes recursively."""
    if seen is None:
        seen = set()

    canonical = str(path.resolve())
    if canonical in seen:
        logger.warning("Circular include detected: %s", path)
        return []
    seen.add(canonical)

    raw = _load_yaml(path)
    if raw is None:
        return []

    if isinstance(raw, dict):
        entries = [raw]
    elif isinstance(raw, list):
        entries = raw
    else:
        return []

    scopes: list[Scope] = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        for include_uri in entry.get("include", []):
            inc_path, inc_base = _resolve_include_uri(include_uri, base_dir)
            scopes.extend(_load_scopes(inc_path, inc_base, seen))

        scope = _parse_scope(entry)
        _resolve_source_paths(scope.sources, base_dir)
        if scope.name or scope.sources:
            scopes.append(scope)

    return scopes


def load_config(
    repo_path: Path | None = None,
    config_paths: list[Path] | None = None,
) -> Config:
    """Load config from files.

    Each config file is a YAML list of named scopes. Scopes are collected
    in order. Each scope can include external configs via the `include` key.
    """
    all_scopes: list[Scope] = []

    if config_paths:
        for path in config_paths:
            all_scopes.extend(_load_scopes(path, path.parent.resolve()))
    else:
        env_path = os.environ.get("SDLC_MCP_CONFIG")
        system_path = Path(env_path) if env_path else SYSTEM_CONFIG_PATH
        all_scopes.extend(_load_scopes(system_path, system_path.parent.resolve()))
        all_scopes.extend(_load_scopes(USER_CONFIG_PATH, USER_CONFIG_PATH.parent.resolve()))

    if repo_path is not None:
        repo_config_path = repo_path / SDLC_DIR / CONFIG_FILENAME
        all_scopes.extend(_load_scopes(repo_config_path, repo_path))

    return Config(scopes=all_scopes)
