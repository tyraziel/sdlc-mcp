"""Content merging with "most specific wins" semantics.

When the same filename exists at multiple hierarchy levels, the most specific
level's version is used. Content that only exists at one level passes through
unchanged. Merging is by filename, not by concatenation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .config import SourceConfig
from .hierarchy import ResolvedHierarchy
from .sources import ContentItem, get_source_class

logger = logging.getLogger(__name__)


@dataclass
class MergedContent:
    items: dict[str, ContentItem] = field(default_factory=dict)
    provenance: dict[str, str] = field(default_factory=dict)

    def get(self, filename: str) -> ContentItem | None:
        return self.items.get(filename)

    def filenames(self) -> list[str]:
        return sorted(self.items.keys())


def _read_sources(sources: list[SourceConfig]) -> list[ContentItem]:
    items = []
    for source_config in sources:
        try:
            source_cls = get_source_class(source_config.type)
        except ValueError:
            logger.warning("Skipping unknown source type: %s", source_config.type)
            continue

        source = source_cls(source_config)
        items.extend(source.read())
    return items


def merge_content(hierarchy: ResolvedHierarchy) -> MergedContent:
    """Merge content from all hierarchy levels.

    Levels are processed from most general to most specific. When the same
    filename appears at multiple levels, the most specific version wins.
    """
    merged = MergedContent()

    for level in hierarchy.levels:
        items = _read_sources(level.sources)
        for item in items:
            merged.items[item.filename] = item
            merged.provenance[item.filename] = f"{level.level}:{level.name}"

    return merged


def merge_content_for_category(hierarchy: ResolvedHierarchy, category: str) -> ContentItem | None:
    """Get a single content item by category (filename without .md extension)."""
    merged = merge_content(hierarchy)

    filename = category if category.endswith(".md") else f"{category}.md"
    return merged.get(filename)


