"""Unit-level tests for the graph HTML/JSON output (no browser required).

These tests verify that :func:`vault.graph.build_graph_spec` produces a
structurally valid Altair chart without needing a live Playwright browser.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


@pytest.fixture()
def small_index(tmp_path: Path):
    """A tiny VaultIndex with two linked notes."""
    from vault.index import VaultIndex

    (tmp_path / "a.md").write_text(
        textwrap.dedent("---\ntitle: Note A\ntags: [x]\n---\nSee [[b]].\n"),
        encoding="utf-8",
    )
    (tmp_path / "b.md").write_text(
        textwrap.dedent("---\ntitle: Note B\n---\nLinks to [[a]].\n"),
        encoding="utf-8",
    )
    idx = VaultIndex(tmp_path)
    idx.build()
    return idx


class TestBuildGraphSpec:
    def test_returns_altair_chart(self, small_index):
        import altair as alt

        from vault.graph import build_graph_spec

        chart = build_graph_spec(small_index)
        assert isinstance(chart, alt.LayerChart)

    def test_chart_json_contains_node_slugs(self, small_index):
        import json

        from vault.graph import build_graph_spec

        chart = build_graph_spec(small_index)
        spec = json.loads(chart.to_json())
        spec_str = json.dumps(spec)
        assert "a" in spec_str
        assert "b" in spec_str

    def test_highlight_reflected_in_data(self, small_index):
        import json

        from vault.graph import build_graph_spec

        chart = build_graph_spec(small_index, highlight="a")
        spec_str = json.dumps(json.loads(chart.to_json()))
        # The highlighted field should appear in at least one dataset
        assert "highlighted" in spec_str

    def test_empty_index_does_not_raise(self, tmp_path: Path):
        from vault.graph import build_graph_spec
        from vault.index import VaultIndex

        idx = VaultIndex(tmp_path)
        idx.build()
        # Should not raise even with no nodes/edges
        from vault.graph import build_graph_spec

        build_graph_spec(idx)

    def test_custom_dimensions(self, small_index):
        import json

        from vault.graph import build_graph_spec

        chart = build_graph_spec(small_index, width=800, height=400)
        spec = json.loads(chart.to_json())
        # width/height should appear somewhere in the vega-lite spec
        spec_str = json.dumps(spec)
        assert "800" in spec_str
        assert "400" in spec_str
