"""Abstract sync backend protocol."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from vault.note import Note


@runtime_checkable
class SyncBackend(Protocol):
    """Common interface shared by all sync backends.

    Implementations (DuckLake, Cloudflare Workers, …) must satisfy this
    protocol so the vault app can swap backends without changing call sites.
    """

    # ------------------------------------------------------------------ notes

    def push_note(self, note: Note) -> None:
        """Upsert *note* in the remote store."""
        ...

    def pull_note(self, slug: str) -> dict[str, Any] | None:
        """Fetch a single note by *slug*, or ``None`` when not found."""
        ...

    def list_notes(self) -> list[str]:
        """Return all known note slugs in the remote store."""
        ...

    def pull_all_notes(self) -> list[dict[str, Any]]:
        """Fetch every note from the remote store."""
        ...

    # ----------------------------------------------------------------- canvas

    def push_canvas(self, canvas_id: str, state: dict[str, Any]) -> None:
        """Persist a tldraw canvas snapshot under *canvas_id*."""
        ...

    def pull_canvas(self, canvas_id: str) -> dict[str, Any] | None:
        """Retrieve a canvas snapshot, or ``None`` when not found."""
        ...
