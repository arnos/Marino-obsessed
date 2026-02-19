"""tldraw canvas integration for Marimo-Obsessed.

Generates a self-contained HTML page (suitable for ``mo.Html()``) that
renders a tldraw canvas pre-populated with note cards and link arrows.

Architecture
------------
* Python computes the initial TLDraw document (JSON) from the vault index.
* The JSON is embedded into an HTML template that bootstraps tldraw via
  CDN (esm.sh + React).
* Two-way communication between the Marimo cell and the canvas uses
  ``window.postMessage``:

  - Parent → canvas: ``{ type: "SELECT_NOTE", slug }``
  - Canvas → parent: ``{ type: "CANVAS_CHANGE", snapshot }``

The canvas plugin also exposes ``canvas_state_to_dict`` / ``dict_to_canvas``
helpers so the sync layer (:mod:`vault.sync`) can persist snapshots.
"""

from __future__ import annotations

import json
import math
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vault.index import VaultIndex
    from vault.plugin import PluginDescriptor

# tldraw CDN — pinned minor version for reproducibility
_TLDRAW_VERSION = "3.8.0"
_REACT_VERSION = "18.3.1"

# ---------------------------------------------------------------------------
# TLDraw document builder
# ---------------------------------------------------------------------------

_CARD_W = 220
_CARD_H = 140
_COL_SPACING = 300
_ROW_SPACING = 200


def _make_id() -> str:
    return f"shape:{uuid.uuid4().hex[:12]}"


def _position_notes(slugs: list[str]) -> dict[str, tuple[float, float]]:
    """Arrange note cards in a simple grid (columns of 4)."""
    cols = max(1, math.ceil(math.sqrt(len(slugs))))
    positions: dict[str, tuple[float, float]] = {}
    for i, slug in enumerate(slugs):
        col = i % cols
        row = i // cols
        positions[slug] = (col * _COL_SPACING, row * _ROW_SPACING)
    return positions


def build_tldraw_snapshot(index: "VaultIndex") -> dict[str, Any]:
    """Build a TLDraw document snapshot from a :class:`VaultIndex`.

    Returns a dict that matches the TLDraw ``StoreSnapshot`` shape and can be
    passed directly to the ``initialState`` prop in the HTML template.
    """
    slugs = list(index.notes.keys())
    positions = _position_notes(slugs)

    slug_to_id: dict[str, str] = {slug: _make_id() for slug in slugs}

    records: list[dict[str, Any]] = []

    # Page
    page_id = "page:main"
    records.append(
        {
            "typeName": "page",
            "id": page_id,
            "name": "Vault",
            "index": "a1",
            "meta": {},
        }
    )

    # Note cards (geo shapes with text)
    for slug, note in index.notes.items():
        x, y = positions[slug]
        shape_id = slug_to_id[slug]
        records.append(
            {
                "typeName": "shape",
                "id": shape_id,
                "type": "geo",
                "parentId": page_id,
                "index": f"a{slug_to_id[slug][-4:]}",
                "x": x,
                "y": y,
                "rotation": 0,
                "isLocked": False,
                "opacity": 1,
                "meta": {"slug": slug},
                "props": {
                    "geo": "rectangle",
                    "w": _CARD_W,
                    "h": _CARD_H,
                    "text": f"**{note.title}**\n\n{', '.join(f'#{t}' for t in note.tags[:3])}",
                    "richText": None,
                    "font": "sans",
                    "align": "start",
                    "verticalAlign": "start",
                    "size": "s",
                    "color": "violet",
                    "fill": "semi",
                    "dash": "draw",
                    "labelColor": "black",
                },
            }
        )

    # Arrows for each link
    for src_slug, tgt_slug in index.edges():
        if src_slug not in slug_to_id or tgt_slug not in slug_to_id:
            continue
        arrow_id = _make_id()
        records.append(
            {
                "typeName": "shape",
                "id": arrow_id,
                "type": "arrow",
                "parentId": page_id,
                "index": f"a{arrow_id[-4:]}",
                "x": 0,
                "y": 0,
                "rotation": 0,
                "isLocked": False,
                "opacity": 0.7,
                "meta": {},
                "props": {
                    "dash": "draw",
                    "size": "s",
                    "fill": "none",
                    "color": "grey",
                    "labelColor": "black",
                    "bend": 0,
                    "start": {
                        "type": "binding",
                        "boundShapeId": slug_to_id[src_slug],
                        "normalizedAnchor": {"x": 0.5, "y": 1.0},
                        "isExact": False,
                        "isPrecise": False,
                    },
                    "end": {
                        "type": "binding",
                        "boundShapeId": slug_to_id[tgt_slug],
                        "normalizedAnchor": {"x": 0.5, "y": 0.0},
                        "isExact": False,
                        "isPrecise": False,
                    },
                    "arrowheadStart": "none",
                    "arrowheadEnd": "arrow",
                    "text": "",
                },
            }
        )

    return {
        "store": {r["id"]: r for r in records},
        "schema": {"schemaVersion": 2, "sequences": {}},
    }


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Marimo-Obsessed Canvas</title>
  <style>
    html, body, #root {{
      margin: 0; padding: 0;
      width: 100%; height: 100%;
      overflow: hidden;
      background: #1a1a2e;
    }}
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="module">
    import React from 'https://esm.sh/react@{react_version}';
    import {{ createRoot }} from 'https://esm.sh/react-dom@{react_version}/client';
    import {{ Tldraw }} from 'https://esm.sh/tldraw@{tldraw_version}?bundle-deps&css-bundle';

    const INITIAL_SNAPSHOT = {snapshot_json};

    function App() {{
      const handleMount = (editor) => {{
        // Apply the pre-built snapshot
        try {{
          editor.store.loadSnapshot(INITIAL_SNAPSHOT);
          editor.zoomToFit({{ duration: 0 }});
        }} catch (e) {{
          console.warn('[canvas] Could not apply snapshot:', e);
        }}

        // Canvas → parent: broadcast changes
        editor.store.listen(() => {{
          try {{
            const snapshot = editor.store.getSnapshot();
            window.parent.postMessage({{ type: 'CANVAS_CHANGE', snapshot }}, '*');
          }} catch (_) {{}}
        }}, {{ source: 'user', scope: 'all' }});

        // Parent → canvas: react to SELECT_NOTE messages
        window.addEventListener('message', (evt) => {{
          if (evt.data?.type === 'SELECT_NOTE') {{
            const targetSlug = evt.data.slug;
            const allShapes = editor.getCurrentPageShapes();
            const match = allShapes.find(s => s.meta?.slug === targetSlug);
            if (match) {{
              editor.select(match.id);
              editor.zoomToSelection({{ duration: 400 }});
            }}
          }}
        }});
      }};

      return React.createElement(Tldraw, {{ onMount: handleMount }});
    }}

    createRoot(document.getElementById('root')).render(React.createElement(App));
  </script>
</body>
</html>"""


def build_canvas_html(
    index: "VaultIndex",
    *,
    snapshot: dict[str, Any] | None = None,
    width: str = "100%",
    height: str = "600px",
) -> str:
    """Return a complete HTML string for a tldraw canvas.

    Parameters
    ----------
    index:
        Populated :class:`VaultIndex`; used to build note-card shapes when no
        *snapshot* is supplied.
    snapshot:
        An existing TLDraw store snapshot (e.g. loaded from the sync backend).
        If ``None``, a fresh layout is computed from *index*.
    width / height:
        Dimensions of the containing ``<iframe>`` element (CSS strings).
    """
    doc = snapshot if snapshot is not None else build_tldraw_snapshot(index)
    html = _HTML_TEMPLATE.format(
        react_version=_REACT_VERSION,
        tldraw_version=_TLDRAW_VERSION,
        snapshot_json=json.dumps(doc),
    )
    # Wrap in an iframe using srcdoc so Marimo can embed it directly
    escaped = html.replace("&", "&amp;").replace('"', "&quot;")
    return (
        f'<iframe srcdoc="{escaped}" '
        f'style="border:none;width:{width};height:{height};border-radius:8px;" '
        f'sandbox="allow-scripts allow-same-origin"></iframe>'
    )


def canvas_state_to_dict(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Serialise a TLDraw snapshot for persistence (pass-through, for symmetry)."""
    return snapshot


def dict_to_canvas(data: dict[str, Any]) -> dict[str, Any]:
    """Deserialise a snapshot from the sync backend."""
    return data


# ---------------------------------------------------------------------------
# Plugin interface
# ---------------------------------------------------------------------------


class _CanvasPlugin:
    def __init__(self, descriptor: "PluginDescriptor") -> None:
        self.descriptor = descriptor
        self._index: "VaultIndex | None" = None
        self._snapshot: dict[str, Any] | None = None

    def on_load(self, index: "VaultIndex") -> None:
        self._index = index

    def on_index_update(self, index: "VaultIndex") -> None:
        self._index = index
        self._snapshot = None  # invalidate cached snapshot

    def on_note_select(self, slug: str, index: "VaultIndex") -> None:
        self._index = index

    def render(self, snapshot: dict[str, Any] | None = None) -> str:
        if self._index is None:
            raise RuntimeError("Plugin not loaded — call on_load first.")
        return build_canvas_html(self._index, snapshot=snapshot or self._snapshot)


def create_plugin(descriptor: "PluginDescriptor") -> "_CanvasPlugin":
    return _CanvasPlugin(descriptor)
