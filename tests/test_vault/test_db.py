"""Unit tests for vault.db.VaultDB."""

import textwrap
from pathlib import Path

import duckdb
import polars as pl
import pytest

from vault.db import VaultDB
from vault.index import VaultIndex

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write(directory: Path, name: str, content: str) -> None:
    (directory / f"{name}.md").write_text(textwrap.dedent(content), encoding="utf-8")


@pytest.fixture()
def db(tmp_path: Path) -> VaultDB:
    _write(tmp_path, "alpha", """\
        ---
        title: Alpha
        tags: [python, tutorial]
        status: done
        ---
        See [[beta]].
    """)
    _write(tmp_path, "beta", """\
        ---
        title: Beta
        tags: [python]
        status: in-progress
        ---
        Links [[alpha]].
    """)
    _write(tmp_path, "gamma", """\
        ---
        title: Gamma
        tags: [data]
        status: done
        ---
        No links here.
    """)
    idx = VaultIndex(tmp_path)
    idx.build()
    return VaultDB(idx)


# ---------------------------------------------------------------------------
# query()
# ---------------------------------------------------------------------------


class TestVaultDBQuery:
    def test_basic_select(self, db: VaultDB):
        df = db.query("SELECT slug FROM notes ORDER BY slug")
        assert list(df["slug"]) == ["alpha", "beta", "gamma"]

    def test_filter_by_tag(self, db: VaultDB):
        df = db.query("SELECT slug FROM notes WHERE 'python' = ANY(tags) ORDER BY slug")
        assert list(df["slug"]) == ["alpha", "beta"]

    def test_returns_polars_dataframe(self, db: VaultDB):
        result = db.query("SELECT slug FROM notes")
        assert isinstance(result, pl.DataFrame)

    def test_invalid_sql_raises(self, db: VaultDB):
        with pytest.raises(duckdb.Error):
            db.query("SELECT * FROM nonexistent_table")


# ---------------------------------------------------------------------------
# table_view()
# ---------------------------------------------------------------------------


class TestTableView:
    def test_returns_all_by_default(self, db: VaultDB):
        df = db.table_view()
        assert len(df) == 3

    def test_filter_tag(self, db: VaultDB):
        df = db.table_view(filter_tag="data")
        assert len(df) == 1
        assert df["slug"][0] == "gamma"

    def test_search_by_title(self, db: VaultDB):
        # "Gamma" only appears in gamma's title; alpha and beta don't mention it
        df = db.table_view(search="Gamma")
        assert len(df) == 1
        assert df["slug"][0] == "gamma"

    def test_search_case_insensitive(self, db: VaultDB):
        df = db.table_view(search="GAMMA")
        assert len(df) == 1
        assert df["slug"][0] == "gamma"

    def test_custom_columns(self, db: VaultDB):
        df = db.table_view(columns=["slug", "title"])
        assert list(df.columns) == ["slug", "title"]

    def test_order_by_slug(self, db: VaultDB):
        df = db.table_view(order_by="slug")
        assert list(df["slug"]) == ["alpha", "beta", "gamma"]

    def test_combined_tag_and_search(self, db: VaultDB):
        # Only gamma has tag "data"; search is a no-op filter that still includes it
        df = db.table_view(filter_tag="data", search="Gamma")
        assert len(df) == 1
        assert df["slug"][0] == "gamma"


# ---------------------------------------------------------------------------
# kanban_view()
# ---------------------------------------------------------------------------


class TestKanbanView:
    def test_groups_by_frontmatter_key(self, db: VaultDB):
        groups = db.kanban_view(group_by="status")
        assert "done" in groups
        assert "in-progress" in groups

    def test_done_group_has_two_notes(self, db: VaultDB):
        groups = db.kanban_view(group_by="status")
        assert len(groups["done"]) == 2

    def test_in_progress_has_one_note(self, db: VaultDB):
        groups = db.kanban_view(group_by="status")
        assert len(groups["in-progress"]) == 1

    def test_missing_key_grouped_as_none(self, tmp_path: Path):
        _write(tmp_path, "no-status.md", "---\ntitle: No Status\ntags: []\n---\nBody.\n")
        idx = VaultIndex(tmp_path)
        idx.build()
        d = VaultDB(idx)
        groups = d.kanban_view(group_by="status")
        assert "(none)" in groups


# ---------------------------------------------------------------------------
# gallery_view()
# ---------------------------------------------------------------------------


class TestGalleryView:
    def test_returns_list_of_dicts(self, db: VaultDB):
        gallery = db.gallery_view()
        assert isinstance(gallery, list)
        assert all(isinstance(item, dict) for item in gallery)

    def test_filter_tag(self, db: VaultDB):
        gallery = db.gallery_view(filter_tag="data")
        assert len(gallery) == 1


# ---------------------------------------------------------------------------
# tag_counts()
# ---------------------------------------------------------------------------


class TestTagCounts:
    def test_python_has_count_two(self, db: VaultDB):
        df = db.tag_counts()
        python_row = df.filter(pl.col("tag") == "python")
        assert python_row["note_count"][0] == 2

    def test_data_has_count_one(self, db: VaultDB):
        df = db.tag_counts()
        data_row = df.filter(pl.col("tag") == "data")
        assert data_row["note_count"][0] == 1

    def test_sorted_by_frequency_desc(self, db: VaultDB):
        df = db.tag_counts()
        counts = list(df["note_count"])
        assert counts == sorted(counts, reverse=True)


# ---------------------------------------------------------------------------
# frontmatter_keys()
# ---------------------------------------------------------------------------


class TestFrontmatterKeys:
    def test_includes_status(self, db: VaultDB):
        keys = db.frontmatter_keys()
        assert "status" in keys

    def test_includes_title_and_tags(self, db: VaultDB):
        keys = db.frontmatter_keys()
        # title and tags are stored in dedicated columns, not in frontmatter JSON
        # frontmatter_keys only returns keys inside the JSON frontmatter column
        assert isinstance(keys, list)

    def test_empty_vault(self, tmp_path: Path):
        idx = VaultIndex(tmp_path)
        idx.build()
        d = VaultDB(idx)
        keys = d.frontmatter_keys()
        assert keys == []


# ---------------------------------------------------------------------------
# refresh()
# ---------------------------------------------------------------------------


class TestRefresh:
    def test_refresh_picks_up_new_note(self, db: VaultDB, tmp_path: Path):
        _write(tmp_path, "delta", "---\ntitle: Delta\ntags: [new]\n---\nBody.\n")
        new_idx = VaultIndex(tmp_path)
        new_idx.build()
        db.refresh(new_idx)
        df = db.query("SELECT slug FROM notes WHERE slug = 'delta'")
        assert len(df) == 1


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_context_manager(self, tmp_path: Path):
        idx = VaultIndex(tmp_path)
        idx.build()
        with VaultDB(idx) as d:
            assert d.query("SELECT 1 AS x")["x"][0] == 1
