"""Backlinks panel plugin for Marimo-Obsessed.

Shows every note that links *to* the currently-selected note.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vault.index import VaultIndex
    from vault.plugin import PluginDescriptor


def backlinks_panel_ui(index: "VaultIndex", slug: str) -> list[dict[str, str]]:
    """Return a list of ``{slug, title}`` dicts for notes that link to *slug*."""
    sources = index.backlinks.get(slug, [])
    return [
        {"slug": s, "title": index.notes[s].title}
        for s in sources
        if s in index.notes
    ]


class _BacklinksPlugin:
    def __init__(self, descriptor: "PluginDescriptor") -> None:
        self.descriptor = descriptor
        self._index: "VaultIndex | None" = None
        self._current_slug: str | None = None

    def on_load(self, index: "VaultIndex") -> None:
        self._index = index

    def on_index_update(self, index: "VaultIndex") -> None:
        self._index = index

    def on_note_select(self, slug: str, index: "VaultIndex") -> None:
        self._index = index
        self._current_slug = slug

    def render(self, slug: str | None = None) -> list[dict[str, str]]:
        if self._index is None:
            raise RuntimeError("Plugin not loaded — call on_load first.")
        target = slug or self._current_slug or ""
        return backlinks_panel_ui(self._index, target)


def create_plugin(descriptor: "PluginDescriptor") -> "_BacklinksPlugin":
    return _BacklinksPlugin(descriptor)
