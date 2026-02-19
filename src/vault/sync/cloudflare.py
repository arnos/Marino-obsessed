"""Cloudflare Workers + R2 sync backend.

A thin HTTP client that talks to a Cloudflare Worker acting as a sync API
gateway.  The Worker writes note content and canvas snapshots to R2, and
optionally fans out real-time updates via Durable Objects (for tldraw sync).

Expected Worker routes
----------------------
PUT  /notes/{slug}           – upsert a note
GET  /notes/{slug}           – retrieve a note
GET  /notes                  – list all slugs
PUT  /canvas/{canvas_id}     – upsert canvas snapshot
GET  /canvas/{canvas_id}     – retrieve canvas snapshot

All endpoints accept/return JSON.  The Worker authenticates callers by
inspecting the ``Authorization: Bearer <token>`` header.

Environment variables (all optional; direct kwargs take precedence):
    VAULT_CF_WORKER_URL   – base URL of the worker (e.g. https://vault.example.workers.dev)
    VAULT_CF_API_TOKEN    – Cloudflare API token / shared secret
"""

from __future__ import annotations

import os
from typing import Any

from vault.note import Note


class CloudflareWorkerClient:
    """HTTP sync backend backed by a Cloudflare Worker + R2."""

    def __init__(
        self,
        worker_url: str | None = None,
        *,
        api_token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        import httpx

        self._base_url = (worker_url or os.getenv("VAULT_CF_WORKER_URL", "")).rstrip("/")
        self._token = api_token or os.getenv("VAULT_CF_API_TOKEN", "")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def push_note(self, note: Note) -> None:
        self._client.put(
            f"/notes/{note.slug}",
            json={
                "title": note.title,
                "body": note.body,
                "tags": note.tags,
                "links": note.links,
            },
        ).raise_for_status()

    def pull_note(self, slug: str) -> dict[str, Any] | None:
        r = self._client.get(f"/notes/{slug}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def list_notes(self) -> list[str]:
        r = self._client.get("/notes")
        r.raise_for_status()
        return r.json().get("slugs", [])

    def pull_all_notes(self) -> list[dict[str, Any]]:
        slugs = self.list_notes()
        notes = []
        for slug in slugs:
            note = self.pull_note(slug)
            if note is not None:
                notes.append(note)
        return notes

    # ------------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------------

    def push_canvas(self, canvas_id: str, state: dict[str, Any]) -> None:
        self._client.put(f"/canvas/{canvas_id}", json=state).raise_for_status()

    def pull_canvas(self, canvas_id: str) -> dict[str, Any] | None:
        r = self._client.get(f"/canvas/{canvas_id}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "CloudflareWorkerClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
