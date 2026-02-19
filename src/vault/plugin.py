"""Plugin descriptor loader for Marimo-Obsessed.

Each plugin is described by a TOML file::

    [plugin]
    id      = "graph-view"
    name    = "Graph View"
    version = "0.1.0"
    entry   = "vault.graph"        # Python module that implements the plugin
    hooks   = ["on_index_update"]

    [plugin.ui]
    sidebar_panel = "graph_panel_ui"   # callable name exported by `entry`

Plugins are loaded by :func:`load_all_plugins` which scans a ``plugins/``
directory for ``*.toml`` files.
"""

from __future__ import annotations

import importlib
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from vault.index import VaultIndex


# ---------------------------------------------------------------------------
# Descriptor
# ---------------------------------------------------------------------------


@dataclass
class PluginDescriptor:
    id: str
    name: str
    version: str
    entry: str  # dotted Python module path
    hooks: list[str] = field(default_factory=list)
    ui: dict[str, str] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PluginDescriptor":
        plugin = data.get("plugin", data)
        return cls(
            id=plugin["id"],
            name=plugin["name"],
            version=plugin.get("version", "0.1.0"),
            entry=plugin["entry"],
            hooks=plugin.get("hooks", []),
            ui=plugin.get("ui", {}),
            meta={k: v for k, v in plugin.items() if k not in {"id", "name", "version", "entry", "hooks", "ui"}},
        )


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class VaultPlugin(Protocol):
    descriptor: PluginDescriptor

    def on_load(self, index: VaultIndex) -> None: ...
    def on_index_update(self, index: VaultIndex) -> None: ...
    def on_note_select(self, slug: str, index: VaultIndex) -> None: ...


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_plugin(descriptor_path: Path) -> VaultPlugin:
    """Load a single plugin from a ``.toml`` descriptor file."""
    with open(descriptor_path, "rb") as fh:
        data = tomllib.load(fh)

    desc = PluginDescriptor.from_dict(data)

    # Ensure src/ is on the path so vault.* modules are importable
    src_dir = descriptor_path.parent.parent / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    module = importlib.import_module(desc.entry)

    if not hasattr(module, "create_plugin"):
        raise AttributeError(f"Plugin module '{desc.entry}' must expose a 'create_plugin(descriptor)' factory.")

    plugin: VaultPlugin = module.create_plugin(desc)
    return plugin


def load_all_plugins(plugins_dir: Path) -> list[VaultPlugin]:
    """Load every ``*.toml`` plugin descriptor found in *plugins_dir*."""
    plugins_dir = Path(plugins_dir)
    plugins: list[VaultPlugin] = []
    for toml_path in sorted(plugins_dir.glob("*.toml")):
        try:
            plugins.append(load_plugin(toml_path))
        except Exception as exc:  # noqa: BLE001
            # Log but don't hard-crash so remaining plugins still load
            print(f"[warn] Failed to load plugin {toml_path.name}: {exc}", file=sys.stderr)
    return plugins


def fire_hook(plugins: list[VaultPlugin], hook: str, **kwargs: Any) -> None:
    """Call *hook* on every plugin that declares it."""
    for plugin in plugins:
        if hook in plugin.descriptor.hooks and hasattr(plugin, hook):
            getattr(plugin, hook)(**kwargs)
