---
skill: add-plugin
name: Add Plugin
description: Scaffold a new Marimo-Obsessed plugin (TOML descriptor + Python module)
triggers: [plugin, add plugin, new plugin, scaffold plugin]
tags: [plugins, development]
---

## Intent

Create the two files needed for a new vault plugin:

1. `plugins/<id>.toml` — descriptor (id, name, version, entry, hooks, ui)
2. `src/vault/<module>.py` — Python module with `create_plugin()` factory

## Parameters

| Name | Required | Description |
|------|----------|-------------|
| `id` | yes | Unique plugin identifier (kebab-case, e.g. `word-count`) |
| `name` | yes | Human-readable display name |
| `hooks` | no | Comma-separated hooks to subscribe to (default: `on_load`) |
| `module` | no | Python module name under `src/vault/` (default: derived from id) |

## Plugin descriptor template

```toml
[plugin]
id      = "<id>"
name    = "<name>"
version = "0.1.0"
entry   = "vault.<module>"
hooks   = [<hooks>]

[plugin.ui]
sidebar_panel = "<render_fn>"
```

## Python module template

```python
from __future__ import annotations
from vault.plugin import PluginDescriptor
from vault.index import VaultIndex

class _<Name>Plugin:
    def __init__(self, descriptor: PluginDescriptor) -> None:
        self.descriptor = descriptor

    def on_load(self, index: VaultIndex) -> None: ...
    def on_index_update(self, index: VaultIndex) -> None: ...
    def on_note_select(self, slug: str, index: VaultIndex) -> None: ...

def create_plugin(descriptor: PluginDescriptor) -> _<Name>Plugin:
    return _<Name>Plugin(descriptor)
```

## Steps

1. Write the TOML descriptor to `plugins/<id>.toml`
2. Write the Python module to `src/vault/<module>.py`
3. Add `load_plugin(Path("plugins/<id>.toml"))` in `vault_app.py` setup cell
   (or let `load_all_plugins` pick it up automatically)
4. Run `uv run pytest` to confirm existing tests still pass
