"""VaultDB — Obsidian Bases-style database view over vault note frontmatter.

Uses DuckDB (in-memory) as a query engine over the notes' frontmatter
properties, body text, tags, and link graph.  Returns :mod:`polars`
DataFrames for seamless integration with Altair charts and Marimo tables.

Usage::

    db = VaultDB(index)

    # Free-form SQL
    df = db.query("SELECT slug, title FROM notes WHERE 'python' = ANY(tags)")

    # Pre-built views
    table   = db.table_view(filter_tag="python", order_by="title")
    kanban  = db.kanban_view(group_by="status")   # groups by frontmatter key

    # Schema introspection
    keys = db.frontmatter_keys()   # all frontmatter property names in the vault
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import duckdb
import polars as pl

if TYPE_CHECKING:
    from vault.index import VaultIndex


class VaultDB:
    """In-memory DuckDB database over vault note metadata and frontmatter."""

    def __init__(self, index: "VaultIndex") -> None:
        self.conn: duckdb.DuckDBPyConnection = duckdb.connect(":memory:")
        self.refresh(index)

    # ------------------------------------------------------------------
    # Build / refresh
    # ------------------------------------------------------------------

    def refresh(self, index: "VaultIndex") -> None:
        """(Re-)populate the database from *index* (call after index rebuild)."""
        self._index = index
        self._create_schema()
        self._load_notes()

    def _create_schema(self) -> None:
        self.conn.execute("""
            CREATE OR REPLACE TABLE notes (
                slug        VARCHAR PRIMARY KEY,
                title       VARCHAR,
                body        TEXT,
                tags        VARCHAR[],
                links       VARCHAR[],
                frontmatter JSON
            )
        """)

    def _load_notes(self) -> None:
        rows = [
            (
                note.slug,
                note.title,
                note.body,
                note.tags,
                note.links,
                json.dumps(note.frontmatter),
            )
            for note in self._index.notes.values()
        ]
        if rows:
            self.conn.executemany("INSERT OR REPLACE INTO notes VALUES (?,?,?,?,?,?)", rows)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(self, sql: str) -> pl.DataFrame:
        """Run a raw SQL query and return a Polars DataFrame."""
        return self.conn.execute(sql).pl()

    # ------------------------------------------------------------------
    # Pre-built views
    # ------------------------------------------------------------------

    def table_view(
        self,
        *,
        filter_tag: str | None = None,
        search: str | None = None,
        columns: list[str] | None = None,
        order_by: str = "title",
    ) -> pl.DataFrame:
        """Return notes as a Polars DataFrame, optionally filtered.

        Parameters
        ----------
        filter_tag:
            Only include notes that have this tag.
        search:
            Case-insensitive substring filter on title or body.
        columns:
            Which columns to include.  Defaults to ``slug, title, tags, links``.
        order_by:
            Column name to sort by.
        """
        cols = ", ".join(columns) if columns else "slug, title, tags, links"
        where_clauses: list[str] = []

        if filter_tag:
            safe = filter_tag.replace("'", "''")
            where_clauses.append(f"'{safe}' = ANY(tags)")
        if search:
            safe = search.replace("'", "''")
            where_clauses.append(f"(title ILIKE '%{safe}%' OR body ILIKE '%{safe}%')")

        where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        safe_order = order_by.replace(";", "").replace("'", "")
        sql = f"SELECT {cols} FROM notes {where} ORDER BY {safe_order}"
        return self.conn.execute(sql).pl()

    def kanban_view(self, group_by: str = "status") -> dict[str, list[dict[str, Any]]]:
        """Group notes by a frontmatter property for a kanban-style view.

        Parameters
        ----------
        group_by:
            Frontmatter key to group by (e.g. ``"status"``, ``"project"``).
            Notes without the field are grouped under ``"(none)"``.

        Returns
        -------
        dict mapping group label → list of note dicts.
        """
        safe_key = group_by.replace("'", "").replace(";", "")
        df = self.conn.execute(
            f"""
            SELECT
                slug, title, tags,
                COALESCE(
                    json_extract_string(frontmatter, '$.{safe_key}'),
                    '(none)'
                ) AS group_val
            FROM notes
            ORDER BY group_val, title
            """
        ).pl()

        groups: dict[str, list[dict[str, Any]]] = {}
        for row in df.to_dicts():
            gv = str(row.pop("group_val"))
            groups.setdefault(gv, []).append(row)
        return groups

    def gallery_view(self, *, filter_tag: str | None = None) -> list[dict[str, Any]]:
        """Return notes as a list of card dicts for a gallery/grid layout."""
        df = self.table_view(
            filter_tag=filter_tag,
            columns=["slug", "title", "tags"],
            order_by="title",
        )
        return df.to_dicts()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def schema_info(self) -> pl.DataFrame:
        """Return DuckDB DESCRIBE output for the notes table."""
        return self.conn.execute("DESCRIBE notes").pl()

    def frontmatter_keys(self) -> list[str]:
        """Return all frontmatter property names present across all notes."""
        rows = self.conn.execute(
            "SELECT DISTINCT unnest(json_keys(frontmatter)) AS k FROM notes ORDER BY k"
        ).fetchall()
        return [r[0] for r in rows]

    def tag_counts(self) -> pl.DataFrame:
        """Return a tag → count table sorted by frequency."""
        return self.conn.execute(
            """
            SELECT tag, COUNT(*) AS note_count
            FROM (SELECT unnest(tags) AS tag FROM notes)
            GROUP BY tag
            ORDER BY note_count DESC, tag
            """
        ).pl()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "VaultDB":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
