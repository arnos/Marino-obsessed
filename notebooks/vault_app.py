import marimo

__generated_with = "0.13.10"
app = marimo.App(width="full", app_title="Marimo-Obsessed")


# ---------------------------------------------------------------------------
# Bootstrap: paths, index, plugins, sub-systems
# ---------------------------------------------------------------------------


@app.cell
def _setup():
    import sys
    from pathlib import Path

    _ROOT = Path(__file__).parent.parent
    _SRC = _ROOT / "src"
    _VAULT_DIR = _ROOT / "vault"
    _PLUGINS_DIR = _ROOT / "plugins"
    _SKILLS_DIR = _ROOT / "skills"

    if str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))

    from vault.db import VaultDB
    from vault.index import VaultIndex
    from vault.plugin import fire_hook, load_all_plugins
    from vault.skills import SkillIndex
    from vault.todos import scan_todos

    _index = VaultIndex(_VAULT_DIR)
    _index.build()

    _plugins = load_all_plugins(_PLUGINS_DIR)
    fire_hook(_plugins, "on_load", index=_index)

    _skill_index = SkillIndex(_SKILLS_DIR)
    _skill_index.build()

    _todo_index = scan_todos(_index)
    _vault_db = VaultDB(_index)

    return (
        _index,
        _plugins,
        _skill_index,
        _todo_index,
        _vault_db,
        _VAULT_DIR,
        fire_hook,
    )


# ---------------------------------------------------------------------------
# Reactive state
# ---------------------------------------------------------------------------


@app.cell
def _state(mo):
    selected_slug = mo.state("")
    active_tab = mo.state("graph")
    return active_tab, selected_slug


# ---------------------------------------------------------------------------
# TK quick-capture command bar
# ---------------------------------------------------------------------------


@app.cell
def _quick_capture(mo, _VAULT_DIR, selected_slug):
    """Typing 'tk <description>' in the command bar appends a todo to todos.md."""
    from vault.todos import append_todo

    cmd_input = mo.ui.text(
        placeholder="tk <description>  —  quick-capture a TK todo",
        label="",
        full_width=True,
    )

    last_captured = mo.state("")
    set_last_captured = last_captured[1]

    raw = cmd_input.value.strip()
    if raw.lower().startswith("tk ") and len(raw) > 3:
        desc = raw[3:].strip()
        source = selected_slug[0]
        append_todo(_VAULT_DIR, desc, source_slug=source)
        set_last_captured(desc)

    feedback = (
        mo.callout(mo.md(f"✓ Added TK: **{last_captured[0]}**"), kind="success")
        if last_captured[0] and raw == ""
        else mo.md("")
    )

    cmd_bar = mo.vstack(
        [
            mo.hstack(
                [mo.md("**⌘**"), cmd_input],
                gap="8px",
                align="center",
            ),
            feedback,
        ],
        gap="2px",
    )
    return (cmd_bar,)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


@app.cell
def _sidebar(mo, _index, active_tab, selected_slug):
    set_slug = selected_slug[1]
    set_tab = active_tab[1]

    search_input = mo.ui.text(placeholder="Search notes…", label="", full_width=True)
    tag_options = sorted(_index.tags.keys())
    tag_filter = mo.ui.dropdown(options=["(all)"] + tag_options, value="(all)", label="Tag")

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

    sidebar = mo.vstack(
        [
            mo.md("## Notes"),
            search_input,
            tag_filter,
            mo.divider(),
            *[_make_link(n) for n in results],
        ],
        gap="4px",
    )
    return (sidebar,)


# ---------------------------------------------------------------------------
# Graph tab
# ---------------------------------------------------------------------------


@app.cell
def _graph_tab(mo, _index, selected_slug):
    from vault.graph import build_graph_spec

    chart = build_graph_spec(
        _index, highlight=selected_slug[0] or None, width=900, height=560
    )
    graph_panel = mo.ui.altair_chart(chart)
    return (graph_panel,)


# ---------------------------------------------------------------------------
# Canvas tab
# ---------------------------------------------------------------------------


@app.cell
def _canvas_tab(mo, _index):
    from vault.canvas import build_canvas_html

    canvas_panel = mo.Html(build_canvas_html(_index, width="100%", height="620px"))
    return (canvas_panel,)


# ---------------------------------------------------------------------------
# Editor tab
# ---------------------------------------------------------------------------


@app.cell
def _editor_tab(mo, _index, _todo_index, selected_slug):
    import re

    from vault.backlinks import backlinks_panel_ui

    slug = selected_slug[0]
    note = _index.notes.get(slug) if slug else None

    if note is None:
        editor_content = mo.md(
            "_Select a note from the sidebar or click a node in the graph._"
        )
        backlinks_content = mo.md("")
        note_todos_content = mo.md("")
    else:
        body_rendered = re.sub(r"\[\[([^\]|]+)\]\]", r"**\1**", note.body)
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
        backlinks_content = (
            mo.vstack(
                [
                    mo.md("---\n### Backlinks"),
                    mo.md(
                        "\n".join(f"- **{b['title']}** (`{b['slug']}`)" for b in bl)
                    ),
                ]
            )
            if bl
            else mo.md("_No backlinks._")
        )

        note_todos = _todo_index.by_note.get(slug, [])
        if note_todos:
            lines = "\n".join(
                f"- {'~~' if t.resolved else ''}TK: {t.description}"
                f"{'~~' if t.resolved else ''} _(line {t.line_no})_"
                for t in note_todos
            )
            note_todos_content = mo.vstack(
                [mo.md("---\n### TK items in this note"), mo.md(lines)]
            )
        else:
            note_todos_content = mo.md("")

    return editor_content, backlinks_content, note_todos_content


# ---------------------------------------------------------------------------
# Todos tab
# ---------------------------------------------------------------------------


@app.cell
def _todos_tab(mo, _todo_index, active_tab, selected_slug):
    set_slug = selected_slug[1]
    set_tab = active_tab[1]

    pending = _todo_index.pending

    if not pending:
        todos_panel = mo.callout(
            mo.md("No pending TK items — vault is clean ✓"), kind="success"
        )
    else:
        rows = []
        for item in pending:
            note_btn = mo.ui.button(
                label=item.source_slug,
                on_click=lambda _, s=item.source_slug: (set_slug(s), set_tab("editor")),
                kind="ghost",
            )
            rows.append(
                mo.hstack(
                    [note_btn, mo.md(f"**{item.description}** _(line {item.line_no})_")],
                    gap="8px",
                    align="center",
                )
            )
        todos_panel = mo.vstack(
            [mo.md(f"### {len(pending)} pending TK items"), *rows], gap="4px"
        )
    return (todos_panel,)


# ---------------------------------------------------------------------------
# Skills tab
# ---------------------------------------------------------------------------


@app.cell
def _skills_tab(mo, _skill_index):
    skill_search = mo.ui.text(placeholder="Search skills…", label="", full_width=True)
    selected_skill = mo.state(None)
    set_selected_skill = selected_skill[1]

    query = skill_search.value.strip()
    skills = _skill_index.search(query) if query else list(_skill_index.skills.values())
    skills = sorted(skills, key=lambda s: s.name)

    def _skill_btn(sk):
        trunc = sk.description[:58] + "…" if len(sk.description) > 58 else sk.description
        return mo.ui.button(
            label=f"{sk.name}  —  {trunc}",
            on_click=lambda _, s=sk: set_selected_skill(s),
            kind="ghost",
            full_width=True,
        )

    current = selected_skill[0]
    if current:
        triggers_md = "  ".join(f"`{t}`" for t in current.triggers)
        tags_md = "  ".join(f"`#{t}`" for t in current.tags)
        detail = mo.vstack(
            [
                mo.md(f"## {current.name}"),
                mo.md(f"**Triggers:** {triggers_md}  ·  **Tags:** {tags_md}"),
                mo.divider(),
                mo.md(current.body),
            ]
        )
    else:
        detail = mo.md(
            "_Select a skill to view its intent, parameters, and steps._"
        )

    skills_panel = mo.hstack(
        [
            mo.vstack(
                [skill_search, mo.divider(), *[_skill_btn(s) for s in skills]],
                style={"width": "320px", "min-width": "240px"},
            ),
            mo.vstack([detail], style={"flex": "1"}),
        ],
        gap="12px",
        align="start",
    )
    return (skills_panel,)


# ---------------------------------------------------------------------------
# Database tab (VaultDB / Bases equivalent)
# ---------------------------------------------------------------------------


@app.cell
def _database_tab(mo, _vault_db, _index):
    # Controls
    db_search = mo.ui.text(placeholder="Filter title/body…", label="Search")
    tag_opts = ["(all)"] + sorted(_index.tags.keys())
    db_tag = mo.ui.dropdown(options=tag_opts, value="(all)", label="Tag")
    fm_keys = _vault_db.frontmatter_keys()
    kanban_key = mo.ui.dropdown(
        options=["(none)"] + fm_keys, value="(none)", label="Kanban group-by"
    )
    sql_input = mo.ui.text_area(
        value="SELECT slug, title, tags FROM notes ORDER BY title",
        label="SQL query",
        full_width=True,
        rows=3,
    )
    run_btn = mo.ui.button(label="Run SQL", kind="neutral")

    # Table view
    tag_filter = db_tag.value if db_tag.value != "(all)" else None
    search_val = db_search.value.strip() or None
    table_df = _vault_db.table_view(filter_tag=tag_filter, search=search_val)
    table_view = mo.ui.table(table_df)

    # Kanban view
    if kanban_key.value and kanban_key.value != "(none)":
        groups = _vault_db.kanban_view(group_by=kanban_key.value)
        cols = []
        for gv, notes in groups.items():
            items = [mo.md(f"**{gv}** ({len(notes)})")]
            items += [mo.md(f"- {n['title']}") for n in notes[:8]]
            if len(notes) > 8:
                items.append(mo.md(f"_… {len(notes) - 8} more_"))
            cols.append(
                mo.vstack(
                    items,
                    style={
                        "border": "1px solid #555",
                        "border-radius": "6px",
                        "padding": "8px",
                        "min-width": "160px",
                    },
                )
            )
        kanban_view = mo.hstack(cols, gap="8px", align="start") if cols else mo.md("_No groups._")
    else:
        kanban_view = mo.md("_Choose a frontmatter key above._")

    # Tag stats
    tag_stats = mo.ui.table(_vault_db.tag_counts())

    # SQL console
    if run_btn.value:
        try:
            result_df = _vault_db.query(sql_input.value)
            sql_output = mo.ui.table(result_df)
        except Exception as exc:
            sql_output = mo.callout(mo.md(f"```\n{exc}\n```"), kind="danger")
    else:
        sql_output = mo.md("_Press **Run SQL** to execute._")

    database_panel = mo.vstack(
        [
            mo.md("## Database  _(VaultDB / Bases)_"),
            mo.hstack([db_search, db_tag, kanban_key], gap="8px"),
            mo.accordion(
                {
                    "Table view": table_view,
                    "Kanban view": kanban_view,
                    "Tag statistics": tag_stats,
                    "SQL console": mo.vstack([sql_input, run_btn, sql_output]),
                }
            ),
        ]
    )
    return (database_panel,)


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------


@app.cell
def _main_layout(
    mo,
    sidebar,
    graph_panel,
    canvas_panel,
    editor_content,
    backlinks_content,
    note_todos_content,
    todos_panel,
    skills_panel,
    database_panel,
    cmd_bar,
    active_tab,
):
    current_tab = active_tab[0]
    tab_map = {
        "graph": "Graph",
        "canvas": "Canvas",
        "editor": "Editor",
        "todos": "Todos",
        "skills": "Skills",
        "database": "Database",
    }

    tabs = mo.ui.tabs(
        {
            "Graph": graph_panel,
            "Canvas": canvas_panel,
            "Editor": mo.vstack(
                [editor_content, backlinks_content, note_todos_content]
            ),
            "Todos": todos_panel,
            "Skills": skills_panel,
            "Database": database_panel,
        },
        value=tab_map.get(current_tab, "Graph"),
    )

    layout = mo.vstack(
        [
            cmd_bar,
            mo.hstack(
                [
                    mo.vstack(
                        [sidebar],
                        style={
                            "width": "220px",
                            "min-width": "180px",
                            "padding": "8px",
                        },
                    ),
                    mo.vstack([tabs], style={"flex": "1", "padding": "8px"}),
                ],
                align="start",
                gap="0",
            ),
        ],
        gap="4px",
    )
    return (layout,)


@app.cell
def _render(layout):
    layout  # noqa: B018  — marimo displays the last expression as cell output
    return


if __name__ == "__main__":
    app.run()
