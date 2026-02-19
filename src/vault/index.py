"""VaultIndex: in-memory index of all notes and their relationships."""

from __future__ import annotations

from pathlib import Path

from vault.note import Note
from vault.parser import parse_note


class VaultIndex:
    """Scans a vault directory and builds backlink, tag, and graph indexes."""

    def __init__(self, vault_dir: Path) -> None:
        self.vault_dir = Path(vault_dir)
        self.notes: dict[str, Note] = {}
        self.backlinks: dict[str, list[str]] = {}
        self.tags: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Build / refresh
    # ------------------------------------------------------------------

    def build(self) -> None:
        """(Re-)scan the vault and rebuild all indexes."""
        self.notes = {}
        for path in sorted(self.vault_dir.glob("**/*.md")):
            note = parse_note(path)
            self.notes[note.slug] = note
        self._build_backlinks()
        self._build_tags()

    def _build_backlinks(self) -> None:
        self.backlinks = {slug: [] for slug in self.notes}
        for slug, note in self.notes.items():
            for link in note.links:
                target = self._normalise_link(link)
                self.backlinks.setdefault(target, [])
                if slug not in self.backlinks[target]:
                    self.backlinks[target].append(slug)

    def _build_tags(self) -> None:
        self.tags = {}
        for slug, note in self.notes.items():
            for tag in note.tags:
                self.tags.setdefault(tag, [])
                if slug not in self.tags[tag]:
                    self.tags[tag].append(slug)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_link(link: str) -> str:
        """Convert a wikilink target to a slug (strip path / extension)."""
        return Path(link).stem if ("/" in link or link.endswith(".md")) else link

    def edges(self) -> list[tuple[str, str]]:
        """Return ``(source_slug, target_slug)`` pairs for every wikilink."""
        result: list[tuple[str, str]] = []
        for slug, note in self.notes.items():
            for link in note.links:
                result.append((slug, self._normalise_link(link)))
        return result

    def search(self, query: str) -> list[Note]:
        """Case-insensitive full-text search across title and body."""
        q = query.lower()
        return [n for n in self.notes.values() if q in n.title.lower() or q in n.body.lower()]

    def notes_with_tag(self, tag: str) -> list[Note]:
        slugs = self.tags.get(tag, [])
        return [self.notes[s] for s in slugs if s in self.notes]
