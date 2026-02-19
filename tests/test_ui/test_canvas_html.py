"""Unit-level tests for the tldraw canvas HTML builder (no browser required).

These tests verify that :func:`vault.canvas.build_canvas_html` and
:func:`vault.canvas.build_tldraw_snapshot` produce valid HTML/JSON without
needing a live Playwright browser.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest


@pytest.fixture()
def small_index(tmp_path: Path):
    from vault.index import VaultIndex

    (tmp_path / "home.md").write_text(
        textwrap.dedent("---\ntitle: Home\n---\nSee [[notes]].\n"),
        encoding="utf-8",
    )
    (tmp_path / "notes.md").write_text(
        textwrap.dedent("---\ntitle: Notes\ntags: [todo]\n---\nBack to [[home]].\n"),
        encoding="utf-8",
    )
    idx = VaultIndex(tmp_path)
    idx.build()
    return idx


class TestBuildTldrawSnapshot:
    def test_returns_dict_with_store(self, small_index):
        from vault.canvas import build_tldraw_snapshot

        snap = build_tldraw_snapshot(small_index)
        assert "store" in snap
        assert "schema" in snap

    def test_contains_page(self, small_index):
        from vault.canvas import build_tldraw_snapshot

        snap = build_tldraw_snapshot(small_index)
        records = list(snap["store"].values())
        page_records = [r for r in records if r.get("typeName") == "page"]
        assert len(page_records) == 1

    def test_contains_note_shapes(self, small_index):
        from vault.canvas import build_tldraw_snapshot

        snap = build_tldraw_snapshot(small_index)
        records = list(snap["store"].values())
        geo_shapes = [r for r in records if r.get("type") == "geo"]
        # One shape per note
        assert len(geo_shapes) == len(small_index.notes)

    def test_contains_arrow_for_link(self, small_index):
        from vault.canvas import build_tldraw_snapshot

        snap = build_tldraw_snapshot(small_index)
        records = list(snap["store"].values())
        arrow_shapes = [r for r in records if r.get("type") == "arrow"]
        # Two bi-directional links (home→notes, notes→home)
        assert len(arrow_shapes) >= 1

    def test_shape_slugs_in_meta(self, small_index):
        from vault.canvas import build_tldraw_snapshot

        snap = build_tldraw_snapshot(small_index)
        records = list(snap["store"].values())
        geo_slugs = {r["meta"]["slug"] for r in records if r.get("type") == "geo"}
        assert geo_slugs == set(small_index.notes.keys())

    def test_empty_index(self, tmp_path: Path):
        from vault.canvas import build_tldraw_snapshot
        from vault.index import VaultIndex

        idx = VaultIndex(tmp_path)
        idx.build()
        snap = build_tldraw_snapshot(idx)
        # Only the page record should be present
        assert len(snap["store"]) == 1


class TestBuildCanvasHtml:
    def test_returns_iframe_string(self, small_index):
        from vault.canvas import build_canvas_html

        html = build_canvas_html(small_index)
        assert "<iframe" in html
        assert "srcdoc=" in html

    def test_contains_tldraw_import(self, small_index):
        from vault.canvas import build_canvas_html

        html = build_canvas_html(small_index)
        assert "tldraw" in html.lower()

    def test_snapshot_json_embedded(self, small_index):
        from vault.canvas import build_canvas_html, build_tldraw_snapshot

        snap = build_tldraw_snapshot(small_index)
        html = build_canvas_html(small_index, snapshot=snap)
        # The page id should be encoded in the HTML
        assert "page:main" in html

    def test_custom_height(self, small_index):
        from vault.canvas import build_canvas_html

        html = build_canvas_html(small_index, height="800px")
        assert "800px" in html

    def test_roundtrip_serialisation(self, small_index):
        from vault.canvas import (
            build_tldraw_snapshot,
            canvas_state_to_dict,
            dict_to_canvas,
        )

        original = build_tldraw_snapshot(small_index)
        serialised = canvas_state_to_dict(original)
        restored = dict_to_canvas(serialised)
        assert restored == original
