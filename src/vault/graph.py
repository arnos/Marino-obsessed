"""Graph-view plugin: builds an Altair force-directed link graph.

Uses :mod:`networkx` for spring layout and :mod:`altair` for rendering.
The resulting chart can be embedded directly in a Marimo cell.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import altair as alt

    from vault.index import VaultIndex
    from vault.plugin import PluginDescriptor


# ---------------------------------------------------------------------------
# Graph spec builder
# ---------------------------------------------------------------------------


def build_graph_spec(
    index: "VaultIndex",
    *,
    highlight: str | None = None,
    width: int = 640,
    height: int = 480,
    seed: int = 42,
) -> "alt.LayerChart":
    """Return an Altair chart showing the inter-note link graph.

    Parameters
    ----------
    index:
        A populated :class:`VaultIndex`.
    highlight:
        Slug of the currently-selected note (rendered in a distinct colour).
    width / height:
        Canvas dimensions in pixels.
    seed:
        Random seed passed to ``networkx.spring_layout`` for reproducible
        positioning.
    """
    import altair as alt
    import networkx as nx
    import polars as pl

    G: nx.DiGraph = nx.DiGraph()
    for slug in index.notes:
        G.add_node(slug, title=index.notes[slug].title)
    for src, tgt in index.edges():
        if src in G and tgt in G:
            G.add_edge(src, tgt)

    # Compute layout
    pos: dict[str, tuple[float, float]] = nx.spring_layout(G, seed=seed, k=2.0)

    nodes_df = pl.DataFrame(
        [
            {
                "slug": slug,
                "title": index.notes[slug].title if slug in index.notes else slug,
                "x": float(pos[slug][0]),
                "y": float(pos[slug][1]),
                "degree": int(G.degree(slug)),
                "highlighted": slug == highlight,
            }
            for slug in G.nodes()
        ]
        or [{"slug": "", "title": "", "x": 0.0, "y": 0.0, "degree": 0, "highlighted": False}]
    )

    edges_rows: list[dict[str, Any]] = []
    for src, tgt in G.edges():
        if src in pos and tgt in pos:
            edges_rows.append(
                {
                    "x": float(pos[src][0]),
                    "y": float(pos[src][1]),
                    "x2": float(pos[tgt][0]),
                    "y2": float(pos[tgt][1]),
                    "source": src,
                    "target": tgt,
                }
            )
    edges_df = pl.DataFrame(
        edges_rows
        if edges_rows
        else [{"x": 0.0, "y": 0.0, "x2": 0.0, "y2": 0.0, "source": "", "target": ""}]
    )
    has_edges = len(edges_rows) > 0

    base_props = {
        "width": width,
        "height": height,
    }

    # Edge layer
    if not has_edges:
        edge_layer = alt.Chart(
            pl.DataFrame({"x": [0.0], "y": [0.0], "x2": [0.0], "y2": [0.0]})
        ).mark_rule(opacity=0)
    else:
        edge_layer = (
            alt.Chart(edges_df)
            .mark_rule(color="#888", strokeWidth=1, opacity=0.55)
            .encode(
                x=alt.X("x:Q", axis=None),
                y=alt.Y("y:Q", axis=None),
                x2="x2:Q",
                y2="y2:Q",
                tooltip=[alt.Tooltip("source:N", title="from"), alt.Tooltip("target:N", title="to")],
            )
        )

    # Node layer
    node_layer = (
        alt.Chart(nodes_df)
        .mark_circle(opacity=0.9)
        .encode(
            x=alt.X("x:Q", axis=None),
            y=alt.Y("y:Q", axis=None),
            size=alt.Size("degree:Q", scale=alt.Scale(range=[80, 400]), legend=None),
            color=alt.condition(
                alt.datum["highlighted"],
                alt.value("#7C3AED"),  # violet for selected note
                alt.value("#4B90D9"),
            ),
            tooltip=[alt.Tooltip("title:N", title="note"), alt.Tooltip("slug:N", title="slug")],
        )
    )

    label_layer = (
        alt.Chart(nodes_df)
        .mark_text(dy=-12, fontSize=11, fontWeight="bold")
        .encode(
            x=alt.X("x:Q", axis=None),
            y=alt.Y("y:Q", axis=None),
            text="slug:N",
            opacity=alt.condition(alt.datum["highlighted"], alt.value(1.0), alt.value(0.65)),
        )
    )

    return (
        (edge_layer + node_layer + label_layer)
        .properties(**base_props)
        .configure_view(strokeWidth=0)
    )


# ---------------------------------------------------------------------------
# Plugin interface
# ---------------------------------------------------------------------------


def graph_panel_ui(index: "VaultIndex", highlight: str | None = None) -> Any:  # noqa: ANN401
    """Return an Altair chart object suitable for ``mo.ui.altair_chart()``."""
    return build_graph_spec(index, highlight=highlight)


class _GraphViewPlugin:
    def __init__(self, descriptor: "PluginDescriptor") -> None:
        self.descriptor = descriptor
        self._index: "VaultIndex | None" = None

    def on_load(self, index: "VaultIndex") -> None:
        self._index = index

    def on_index_update(self, index: "VaultIndex") -> None:
        self._index = index

    def on_note_select(self, slug: str, index: "VaultIndex") -> None:
        self._index = index

    def render(self, highlight: str | None = None) -> Any:  # noqa: ANN401
        if self._index is None:
            raise RuntimeError("Plugin not loaded — call on_load first.")
        return graph_panel_ui(self._index, highlight=highlight)


def create_plugin(descriptor: "PluginDescriptor") -> "_GraphViewPlugin":
    return _GraphViewPlugin(descriptor)
