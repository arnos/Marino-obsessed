---
title: Plugin System
tags: [plugins, architecture]
---

# Plugin System

See also: [[index]], [[getting-started]]

Each plugin is a pair of files:

1. A **TOML descriptor** in `plugins/` that declares the plugin's identity,
   hooks it listens to, and the UI callables it exposes.
2. A **Python module** (the `entry` field) that implements a `create_plugin()`
   factory and the declared hooks.

## Descriptor schema

```toml
[plugin]
id      = "my-plugin"
name    = "My Plugin"
version = "0.1.0"
entry   = "vault.my_plugin"      # importable Python module
hooks   = ["on_load", "on_index_update", "on_note_select"]

[plugin.ui]
sidebar_panel = "my_panel_ui"    # callable name in the entry module
```

## Hooks

| Hook | When it fires |
|---|---|
| `on_load` | After the vault index is first built |
| `on_index_update` | After the index is rebuilt (e.g. file saved) |
| `on_note_select` | When the user clicks a note |

## Built-in plugins

- [[graph-view plugin|graph-view]] — force-directed link graph
- [[canvas plugin|canvas]] — tldraw infinite canvas
- [[backlinks plugin|backlinks]] — backlinks bottom panel
