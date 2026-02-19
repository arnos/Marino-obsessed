"""Unit tests for vault.index.VaultIndex."""

import textwrap
from pathlib import Path

import pytest

from vault.index import VaultIndex


def _write_note(directory: Path, name: str, content: str) -> Path:
    path = directory / f"{name}.md"
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


@pytest.fixture()
def vault(tmp_path: Path) -> VaultIndex:
    """Minimal vault fixture with three inter-linked notes."""
    _write_note(tmp_path, "alpha", """\
        ---
        title: Alpha
        tags: [first]
        ---
        See [[beta]] and [[gamma]].
    """)
    _write_note(tmp_path, "beta", """\
        ---
        title: Beta
        tags: [second]
        ---
        Links back to [[alpha]].
    """)
    _write_note(tmp_path, "gamma", """\
        ---
        title: Gamma
        tags: [first, second]
        ---
        Standalone note. #extra
    """)
    idx = VaultIndex(tmp_path)
    idx.build()
    return idx


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


class TestVaultIndexNotes:
    def test_all_notes_loaded(self, vault: VaultIndex):
        assert set(vault.notes.keys()) == {"alpha", "beta", "gamma"}

    def test_note_title(self, vault: VaultIndex):
        assert vault.notes["alpha"].title == "Alpha"

    def test_note_tags(self, vault: VaultIndex):
        assert "first" in vault.notes["alpha"].tags


# ---------------------------------------------------------------------------
# Backlinks
# ---------------------------------------------------------------------------


class TestVaultIndexBacklinks:
    def test_alpha_is_linked_by_beta(self, vault: VaultIndex):
        assert "beta" in vault.backlinks.get("alpha", [])

    def test_beta_is_linked_by_alpha(self, vault: VaultIndex):
        assert "alpha" in vault.backlinks.get("beta", [])

    def test_gamma_is_linked_by_alpha(self, vault: VaultIndex):
        assert "alpha" in vault.backlinks.get("gamma", [])

    def test_no_duplicate_backlinks(self, vault: VaultIndex):
        for sources in vault.backlinks.values():
            assert len(sources) == len(set(sources))


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


class TestVaultIndexEdges:
    def test_edges_contain_alpha_to_beta(self, vault: VaultIndex):
        assert ("alpha", "beta") in vault.edges()

    def test_edges_contain_alpha_to_gamma(self, vault: VaultIndex):
        assert ("alpha", "gamma") in vault.edges()

    def test_edges_contain_beta_to_alpha(self, vault: VaultIndex):
        assert ("beta", "alpha") in vault.edges()

    def test_edges_returns_list(self, vault: VaultIndex):
        assert isinstance(vault.edges(), list)


# ---------------------------------------------------------------------------
# Tags index
# ---------------------------------------------------------------------------


class TestVaultIndexTags:
    def test_tag_first_contains_alpha(self, vault: VaultIndex):
        assert "alpha" in vault.tags.get("first", [])

    def test_tag_first_contains_gamma(self, vault: VaultIndex):
        assert "gamma" in vault.tags.get("first", [])

    def test_inline_tag_extra_on_gamma(self, vault: VaultIndex):
        assert "gamma" in vault.tags.get("extra", [])

    def test_notes_with_tag(self, vault: VaultIndex):
        notes = vault.notes_with_tag("second")
        slugs = {n.slug for n in notes}
        assert slugs == {"beta", "gamma"}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestVaultIndexSearch:
    def test_search_by_title(self, vault: VaultIndex):
        results = vault.search("Alpha")
        assert any(n.slug == "alpha" for n in results)

    def test_search_case_insensitive(self, vault: VaultIndex):
        results = vault.search("BETA")
        assert any(n.slug == "beta" for n in results)

    def test_search_body_content(self, vault: VaultIndex):
        results = vault.search("Standalone")
        assert any(n.slug == "gamma" for n in results)

    def test_search_no_match(self, vault: VaultIndex):
        results = vault.search("zzz_no_match_zzz")
        assert results == []

    def test_empty_vault(self, tmp_path: Path):
        idx = VaultIndex(tmp_path)
        idx.build()
        assert idx.notes == {}
        assert idx.edges() == []
        assert idx.search("anything") == []


# ---------------------------------------------------------------------------
# Rebuild
# ---------------------------------------------------------------------------


class TestVaultIndexRebuild:
    def test_rebuild_picks_up_new_note(self, tmp_path: Path):
        idx = VaultIndex(tmp_path)
        idx.build()
        assert "delta" not in idx.notes

        _write_note(tmp_path, "delta", "---\ntitle: Delta\n---\nHello.\n")
        idx.build()
        assert "delta" in idx.notes
