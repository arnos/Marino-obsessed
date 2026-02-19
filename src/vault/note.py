"""Core Note dataclass."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Note:
    """A single markdown note in the vault."""

    path: Path
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    #: Titles/slugs that this note links to via [[WikiLinks]]
    links: list[str] = field(default_factory=list)
    frontmatter: dict[str, Any] = field(default_factory=dict)

    @property
    def slug(self) -> str:
        """Filesystem-stable identifier derived from the filename stem."""
        return self.path.stem

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "title": self.title,
            "body": self.body,
            "tags": self.tags,
            "links": self.links,
            "frontmatter": self.frontmatter,
        }
