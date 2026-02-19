"""Unit tests for vault.plugin (descriptor loading + hook dispatch)."""

import textwrap
from pathlib import Path

import pytest

from vault.plugin import PluginDescriptor, fire_hook, load_all_plugins, load_plugin


# ---------------------------------------------------------------------------
# PluginDescriptor.from_dict
# ---------------------------------------------------------------------------


class TestPluginDescriptor:
    def test_basic_construction(self):
        data = {
            "plugin": {
                "id": "test-plugin",
                "name": "Test Plugin",
                "version": "1.2.3",
                "entry": "vault.graph",
                "hooks": ["on_load"],
                "ui": {"sidebar_panel": "render_fn"},
            }
        }
        desc = PluginDescriptor.from_dict(data)
        assert desc.id == "test-plugin"
        assert desc.name == "Test Plugin"
        assert desc.version == "1.2.3"
        assert desc.entry == "vault.graph"
        assert desc.hooks == ["on_load"]
        assert desc.ui == {"sidebar_panel": "render_fn"}

    def test_defaults(self):
        data = {"plugin": {"id": "x", "name": "X", "entry": "vault.graph"}}
        desc = PluginDescriptor.from_dict(data)
        assert desc.version == "0.1.0"
        assert desc.hooks == []
        assert desc.ui == {}

    def test_flat_dict_without_plugin_key(self):
        """Descriptor can also be passed without the wrapping ``[plugin]`` key."""
        data = {"id": "flat", "name": "Flat", "entry": "vault.graph"}
        desc = PluginDescriptor.from_dict(data)
        assert desc.id == "flat"


# ---------------------------------------------------------------------------
# load_plugin (from a real TOML file)
# ---------------------------------------------------------------------------


@pytest.fixture()
def graph_toml(tmp_path: Path) -> Path:
    toml = tmp_path / "graph-view.toml"
    toml.write_text(
        textwrap.dedent("""\
            [plugin]
            id      = "graph-view"
            name    = "Graph View"
            version = "0.1.0"
            entry   = "vault.graph"
            hooks   = ["on_load", "on_index_update"]

            [plugin.ui]
            sidebar_panel = "graph_panel_ui"
        """),
        encoding="utf-8",
    )
    return toml


class TestLoadPlugin:
    def test_loads_without_error(self, graph_toml: Path):
        plugin = load_plugin(graph_toml)
        assert plugin is not None

    def test_descriptor_populated(self, graph_toml: Path):
        plugin = load_plugin(graph_toml)
        assert plugin.descriptor.id == "graph-view"
        assert "on_load" in plugin.descriptor.hooks

    def test_plugin_has_on_load(self, graph_toml: Path):
        plugin = load_plugin(graph_toml)
        assert hasattr(plugin, "on_load")

    def test_missing_create_plugin_raises(self, tmp_path: Path):
        """A plugin module without create_plugin() should raise AttributeError."""
        # Write a module with no create_plugin
        mod = tmp_path / "bad_plugin.py"
        mod.write_text("# no create_plugin here\n", encoding="utf-8")

        import sys

        sys.path.insert(0, str(tmp_path))
        toml = tmp_path / "bad.toml"
        toml.write_text(
            "[plugin]\nid='bad'\nname='Bad'\nentry='bad_plugin'\n",
            encoding="utf-8",
        )
        try:
            with pytest.raises(AttributeError, match="create_plugin"):
                load_plugin(toml)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("bad_plugin", None)


# ---------------------------------------------------------------------------
# load_all_plugins
# ---------------------------------------------------------------------------


class TestLoadAllPlugins:
    def test_loads_multiple(self, tmp_path: Path):
        for name in ("graph-view", "canvas", "backlinks"):
            content = textwrap.dedent(f"""\
                [plugin]
                id    = "{name}"
                name  = "{name.title()}"
                entry = "vault.graph"
                hooks = []
            """)
            (tmp_path / f"{name}.toml").write_text(content, encoding="utf-8")

        plugins = load_all_plugins(tmp_path)
        ids = {p.descriptor.id for p in plugins}
        assert ids == {"graph-view", "canvas", "backlinks"}

    def test_skips_bad_plugins(self, tmp_path: Path):
        """A broken plugin should not prevent others from loading."""
        good = tmp_path / "good.toml"
        good.write_text(
            "[plugin]\nid='good'\nname='Good'\nentry='vault.graph'\nhooks=[]\n",
            encoding="utf-8",
        )
        bad = tmp_path / "bad.toml"
        bad.write_text(
            "[plugin]\nid='bad'\nname='Bad'\nentry='vault.nonexistent_module'\nhooks=[]\n",
            encoding="utf-8",
        )

        plugins = load_all_plugins(tmp_path)
        ids = {p.descriptor.id for p in plugins}
        assert "good" in ids
        assert "bad" not in ids


# ---------------------------------------------------------------------------
# fire_hook
# ---------------------------------------------------------------------------


class TestFireHook:
    def test_fires_correct_hook(self, graph_toml: Path, tmp_path: Path):
        from vault.index import VaultIndex

        plugin = load_plugin(graph_toml)
        idx = VaultIndex(tmp_path)
        idx.build()

        # Should not raise
        fire_hook([plugin], "on_load", index=idx)
        fire_hook([plugin], "on_index_update", index=idx)

    def test_ignores_undeclared_hook(self, graph_toml: Path, tmp_path: Path):
        """fire_hook with a hook not in plugin.descriptor.hooks is a no-op."""
        from vault.index import VaultIndex

        plugin = load_plugin(graph_toml)
        idx = VaultIndex(tmp_path)
        idx.build()

        # on_note_select is NOT in hooks list for graph-view fixture
        fire_hook([plugin], "on_note_select", slug="anything", index=idx)
