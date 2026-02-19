"""DuckDB / DuckLake sync backend.

Uses DuckDB as the local query engine and the ``ducklake`` extension to
attach a DuckLake catalog whose Parquet data files live on Cloudflare R2
(or any S3-compatible object store).

Sync flow
---------
1. On startup ``DuckLakeSync.__init__`` creates a local DuckDB connection and
   attaches (or creates) the DuckLake catalog.
2. ``push_note`` / ``push_canvas`` write records into the attached catalog;
   DuckLake automatically writes Parquet to R2.
3. ``pull_*`` methods run SQL queries through DuckDB, which reads Parquet
   directly from R2 — no intermediate download step needed.

The ``ducklake`` DuckDB extension ships as of DuckDB ≥ 1.2.  The extension
is installed and loaded lazily inside ``_setup``.

Environment variables (all optional; direct kwargs take precedence):
    VAULT_R2_ENDPOINT    – https://<account>.r2.cloudflarestorage.com
    VAULT_R2_ACCESS_KEY  – R2 access key ID
    VAULT_R2_SECRET_KEY  – R2 secret access key
    VAULT_R2_BUCKET      – bucket name (default: ``marimo-obsessed``)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from vault.note import Note


class DuckLakeSync:
    """Local-first sync backend backed by DuckDB + DuckLake on Cloudflare R2."""

    _CATALOG = "vault"

    def __init__(
        self,
        db_path: Path | str = ":memory:",
        *,
        r2_endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
    ) -> None:
        import duckdb

        self._db_path = str(db_path)
        self._r2_endpoint = r2_endpoint or os.getenv("VAULT_R2_ENDPOINT", "")
        self._access_key = access_key or os.getenv("VAULT_R2_ACCESS_KEY", "")
        self._secret_key = secret_key or os.getenv("VAULT_R2_SECRET_KEY", "")
        self._bucket = bucket or os.getenv("VAULT_R2_BUCKET", "marimo-obsessed")

        self.conn: duckdb.DuckDBPyConnection = duckdb.connect(self._db_path)
        self._setup()

    # ------------------------------------------------------------------
    # Internal setup
    # ------------------------------------------------------------------

    def _setup(self) -> None:
        self.conn.execute("INSTALL ducklake; LOAD ducklake;")

        if self._r2_endpoint:
            # Configure S3-compatible credentials for R2
            self.conn.execute(f"""
                CREATE SECRET IF NOT EXISTS r2_secret (
                    TYPE s3,
                    ENDPOINT '{self._r2_endpoint}',
                    KEY_ID '{self._access_key}',
                    SECRET '{self._secret_key}',
                    REGION 'auto'
                );
            """)
            data_path = f"s3://{self._bucket}/data/"
            catalog_uri = f"ducklake:s3://{self._bucket}/vault.ducklake"
        else:
            # Fall back to local filesystem (useful for tests / offline dev)
            data_path = str(Path(self._db_path).parent / "ducklake_data" / "")
            catalog_uri = f"ducklake:{Path(self._db_path).parent / 'vault.ducklake'}"

        self.conn.execute(f"""
            ATTACH IF NOT EXISTS '{catalog_uri}' AS {self._CATALOG}
            (DATA_PATH '{data_path}');
        """)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        c = self._CATALOG
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {c}.notes (
                slug        VARCHAR PRIMARY KEY,
                title       VARCHAR NOT NULL,
                body        TEXT    NOT NULL,
                tags        VARCHAR[],
                links       VARCHAR[],
                updated_at  TIMESTAMPTZ DEFAULT now()
            );
        """)
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {c}.canvas_state (
                canvas_id  VARCHAR PRIMARY KEY,
                state      JSON    NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT now()
            );
        """)

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def push_note(self, note: Note) -> None:
        c = self._CATALOG
        self.conn.execute(
            f"""
            INSERT INTO {c}.notes (slug, title, body, tags, links, updated_at)
            VALUES (?, ?, ?, ?, ?, now())
            ON CONFLICT (slug) DO UPDATE SET
                title      = excluded.title,
                body       = excluded.body,
                tags       = excluded.tags,
                links      = excluded.links,
                updated_at = now();
            """,
            [note.slug, note.title, note.body, note.tags, note.links],
        )

    def pull_note(self, slug: str) -> dict[str, Any] | None:
        c = self._CATALOG
        row = self.conn.execute(
            f"SELECT slug, title, body, tags, links FROM {c}.notes WHERE slug = ?",
            [slug],
        ).fetchone()
        if row is None:
            return None
        return dict(zip(["slug", "title", "body", "tags", "links"], row))

    def list_notes(self) -> list[str]:
        c = self._CATALOG
        rows = self.conn.execute(f"SELECT slug FROM {c}.notes ORDER BY slug").fetchall()
        return [r[0] for r in rows]

    def pull_all_notes(self) -> list[dict[str, Any]]:
        c = self._CATALOG
        df = self.conn.execute(
            f"SELECT slug, title, body, tags, links FROM {c}.notes ORDER BY slug"
        ).df()
        return df.to_dict("records")

    # ------------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------------

    def push_canvas(self, canvas_id: str, state: dict[str, Any]) -> None:
        c = self._CATALOG
        self.conn.execute(
            f"""
            INSERT INTO {c}.canvas_state (canvas_id, state, updated_at)
            VALUES (?, ?, now())
            ON CONFLICT (canvas_id) DO UPDATE SET
                state      = excluded.state,
                updated_at = now();
            """,
            [canvas_id, json.dumps(state)],
        )

    def pull_canvas(self, canvas_id: str) -> dict[str, Any] | None:
        c = self._CATALOG
        row = self.conn.execute(
            f"SELECT state FROM {c}.canvas_state WHERE canvas_id = ?",
            [canvas_id],
        ).fetchone()
        if row is None:
            return None
        raw = row[0]
        return json.loads(raw) if isinstance(raw, str) else raw

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "DuckLakeSync":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
