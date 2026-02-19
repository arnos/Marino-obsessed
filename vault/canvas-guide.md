---
title: Canvas Guide
tags: [canvas, tldraw]
---

# Canvas Guide

See also: [[index]], [[sync-guide]]

The canvas tab embeds a **tldraw** infinite canvas with your vault notes
pre-loaded as draggable cards connected by arrows.

## Interaction

| Action | Result |
|---|---|
| Click a note card | Selects the note in the editor panel |
| Drag cards | Reposition notes freely |
| Pan / zoom | Mouse wheel or pinch on trackpad |
| `SELECT_NOTE` postMessage | Pan + zoom to the target card |

## Canvas ↔ Sync

Canvas snapshots are persisted via the sync backend.  When a `DuckLakeSync`
or `CloudflareWorkerClient` is configured the snapshot is stored under the key
`main` (configurable in `plugins/canvas.toml`).

## tldraw version

The canvas loads tldraw **3.8.0** from `esm.sh`.  To pin a different version,
edit `_TLDRAW_VERSION` in `src/vault/canvas.py`.

## Link arrows

WikiLinks between notes become tldraw arrow shapes.  They are bound to the
source and target card shapes so they follow cards when they are dragged.
