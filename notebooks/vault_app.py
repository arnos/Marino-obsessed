import marimo

__generated_with = "0.13.10"
app = marimo.App(width="full", app_title="Marimo-Obsessed")


@app.cell
def _setup():
    """Bootstrap: resolve paths and load the vault index + plugins."""
    import sys
    from pathlib import Path

    _ROOT = Path(__file__).parent.parent
    _SRC = _ROOT / "src"
    _VAULT_DIR = _ROOT / "vault"
    _PLUGINS_DIR = _ROOT / "plugins"

    if str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))

    from vault.index import VaultIndex
    from vault.plugin import fire_hook, load_all_plugins

    _index = VaultIndex(_VAULT_DIR)
    _index.build()

    _plugins = load_all_plugins(_PLUGINS_DIR)
    fire_hook(_plugins, "on_load", index=_index)

    return _index, _plugins, _VAULT_DIR, _PLUGINS_DIR, fire_hook


@app.cell
def _state(mo):
    """Reactive state: currently-selected note slug and active tab."""
    selected_slug = mo.state("")
    active_tab = mo.state("graph")
    return active_tab, selected_slug


@app.cell
def _sidebar(mo, _index, selected_slug, active_tab):
    """Left sidebar: search, note list, tag filter."""
    set_slug = selected_slug[1]
    set_tab = active_tab[1]

    search_input = mo.ui.text(placeholder="Search notes…", label="", full_width=True)
    tag_options = sorted(_index.tags.keys())
    tag_filter = mo.ui.dropdown(options=["(all)"] + tag_options, value="(all)", label="Tag")

    return search_input, tag_filter, set_slug, set_tab


@app.cell
def _sidebar_results(mo, _index, selected_slug, search_input, tag_filter, set_slug, set_tab):
    """Compute filtered note list and render sidebar links."""
    query = search_input.value.strip()
    tag = tag_filter.value

    if query:
        results = _index.search(query)
    elif tag and tag != "(all)":
        results = _index.notes_with_tag(tag)
    else:
        results = list(_index.notes.values())

    results = sorted(results, key=lambda n: n.title)

    def _make_link(note):
        return mo.ui.button(
            label=note.title,
            on_click=lambda _: (set_slug(note.slug), set_tab("editor")),
            kind="ghost",
            full_width=True,
        )

    note_links = [_make_link(n) for n in results]

    sidebar = mo.vstack(
        [
            mo.md("## Notes"),
            search_input,
            tag_filter,
            mo.divider(),
            *note_links,
        ],
        gap="4px",
    )
    return sidebar, results


@app.cell
def _graph_tab(mo, _index, selected_slug, _plugins, fire_hook):
    """Graph view panel."""
    import altair as alt

    current_slug = selected_slug[0]

    from vault.graph import build_graph_spec

    chart = build_graph_spec(_index, highlight=current_slug or None, width=900, height=560)
    graph_panel = mo.ui.altair_chart(chart)
    return (graph_panel,)


@app.cell
def _canvas_tab(mo, _index, _plugins, selected_slug, fire_hook):
    """tldraw canvas panel."""
    from vault.canvas import build_canvas_html

    canvas_html = build_canvas_html(_index, width="100%", height="620px")
    canvas_panel = mo.Html(canvas_html)
    return (canvas_panel,)


@app.cell
def _editor_tab(mo, _index, selected_slug, set_slug):
    """Note editor + backlinks panel."""
    from vault.backlinks import backlinks_panel_ui

    slug = selected_slug[0]
    note = _index.notes.get(slug) if slug else None

    if note is None:
        editor_content = mo.md(
            "_Select a note from the sidebar or click a node in the graph._"
        )
        backlinks_content = mo.md("")
    else:
        # Render WikiLinks as clickable elements
        import re

        body = note.body
        # Replace [[Target]] with bold text for now (full routing via set_slug
        # would require a custom mo.Html component)
        body_rendered = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", r"**\2**" if r"\2" else r"**\1**", body)
        body_rendered = re.sub(r"\[\[([^\]|]+)\]\]", r"**\1**", body_rendered)

        tags_md = " ".join(f"`#{t}`" for t in note.tags)
        editor_content = mo.vstack(
            [
                mo.md(f"# {note.title}"),
                mo.md(tags_md) if note.tags else mo.md(""),
                mo.divider(),
                mo.md(body_rendered),
            ]
        )

        bl = backlinks_panel_ui(_index, slug)
        if bl:
            bl_items = "\n".join(f"- [[{b['slug']}]] — {b['title']}" for b in bl)
            backlinks_content = mo.vstack(
                [
                    mo.md("---\n### Backlinks"),
                    mo.md(bl_items),
                ]
            )
        else:
            backlinks_content = mo.md("_No backlinks yet._")

    return editor_content, backlinks_content


@app.cell
def _main_layout(mo, sidebar, graph_panel, canvas_panel, editor_content, backlinks_content, active_tab, set_tab):
    """Assemble the full app layout."""
    current_tab = active_tab[0]

    tabs = mo.ui.tabs(
        {
            "Graph": graph_panel,
            "Canvas": canvas_panel,
            "Editor": mo.vstack([editor_content, backlinks_content]),
        },
        value={"graph": "Graph", "canvas": "Canvas", "editor": "Editor"}.get(current_tab, "Graph"),
    )

    layout = mo.hstack(
        [
            mo.vstack([sidebar], style={"width": "220px", "min-width": "180px", "padding": "8px"}),
            mo.vstack([tabs], style={"flex": "1", "padding": "8px"}),
        ],
        align="start",
        gap="0",
    )

    return layout


@app.cell
def _render(layout):
    layout
    return


if __name__ == "__main__":
    app.run()
