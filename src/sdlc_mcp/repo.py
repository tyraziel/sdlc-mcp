"""Shared git repository helpers for cloning and caching."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import git

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".cache" / "sdlc-mcp" / "repos"


def cache_key(url: str, ref: str = "") -> str:
    slug = hashlib.sha256(f"{url}:{ref}".encode()).hexdigest()[:12]
    name = url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    return f"{name}-{slug}"


def ensure_cloned(url: str, ref: str, dest: Path) -> None:
    if dest.exists():
        logger.debug("Pulling updates for %s", url)
        try:
            repo = git.Repo(dest)
            repo.remotes.origin.fetch()
            target = f"origin/{ref}" if ref else "origin/HEAD"
            repo.head.reset(target, working_tree=True)
        except git.GitCommandError as exc:
            logger.warning("git update failed for %s: %s", url, exc)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Cloning %s to %s", url, dest)
        try:
            kwargs: dict = {"depth": 1}
            if ref:
                kwargs["branch"] = ref
            git.Repo.clone_from(url, str(dest), **kwargs)
        except git.GitCommandError as exc:
            logger.error("git clone failed for %s: %s", url, exc)
