"""Unit tests for vault.parser."""

import textwrap
from pathlib import Path

from vault.parser import (
    parse_frontmatter,
    parse_note,
    parse_tags,
    parse_wikilinks,
)

# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_no_frontmatter_returns_empty_dict(self):
        meta, body = parse_frontmatter("Just some text.")
        assert meta == {}
        assert body == "Just some text."

    def test_basic_frontmatter(self):
        raw = textwrap.dedent("""\
            ---
            title: My Note
            tags: [a, b]
            ---
            Body here.
        """)
        meta, body = parse_frontmatter(raw)
        assert meta["title"] == "My Note"
        assert meta["tags"] == ["a", "b"]
        assert "Body here." in body

    def test_frontmatter_not_at_start_is_ignored(self):
        raw = "Intro\n---\ntitle: Nope\n---\nMore text."
        meta, body = parse_frontmatter(raw)
        assert meta == {}

    def test_empty_frontmatter_block(self):
        raw = "---\n---\nBody."
        meta, body = parse_frontmatter(raw)
        assert meta == {}
        assert "Body." in body

    def test_invalid_yaml_returns_empty_dict(self):
        raw = "---\n: broken: yaml:\n---\nBody."
        meta, body = parse_frontmatter(raw)
        # Should not raise; returns empty meta
        assert isinstance(meta, dict)


# ---------------------------------------------------------------------------
# parse_wikilinks
# ---------------------------------------------------------------------------


class TestParseWikilinks:
    def test_single_link(self):
        assert parse_wikilinks("See [[Getting Started]] for details.") == ["Getting Started"]

    def test_multiple_links(self):
        links = parse_wikilinks("[[A]] and [[B]] and [[C]]")
        assert links == ["A", "B", "C"]

    def test_link_with_alias(self):
        # [[Target|Display Text]] — only target is returned
        links = parse_wikilinks("See [[index|Home Page]] here.")
        assert links == ["index"]

    def test_link_with_heading(self):
        # [[Note#Section]] — only note part returned
        links = parse_wikilinks("Jump to [[canvas-guide#Interaction]].")
        assert links == ["canvas-guide"]

    def test_deduplication(self):
        links = parse_wikilinks("[[A]] then [[A]] again")
        assert links == ["A"]

    def test_no_links(self):
        assert parse_wikilinks("Plain text, no links.") == []

    def test_preserves_order(self):
        links = parse_wikilinks("[[Z]] then [[A]] then [[M]]")
        assert links == ["Z", "A", "M"]


# ---------------------------------------------------------------------------
# parse_tags
# ---------------------------------------------------------------------------


class TestParseTags:
    def test_single_tag(self):
        assert parse_tags("This is #marimo content.") == ["marimo"]

    def test_multiple_tags(self):
        tags = parse_tags("Post tagged #python and #open-source.")
        assert tags == ["python", "open-source"]

    def test_deduplication(self):
        tags = parse_tags("#python code in #python style")
        assert tags == ["python"]

    def test_no_tags(self):
        assert parse_tags("No hashtags here.") == []

    def test_url_not_matched(self):
        # Hash inside a URL should not be extracted as a tag
        tags = parse_tags("Visit https://example.com/page#section for info.")
        assert "section" not in tags

    def test_nested_tag(self):
        tags = parse_tags("Category #tools/marimo used here.")
        assert "tools/marimo" in tags

    def test_code_span_excluded(self):
        tags = parse_tags("Use `#include` in C code.")
        assert "include" not in tags


# ---------------------------------------------------------------------------
# parse_note (integration)
# ---------------------------------------------------------------------------


class TestParseNote:
    def test_full_note(self, tmp_path: Path):
        md = tmp_path / "my-note.md"
        md.write_text(
            textwrap.dedent("""\
                ---
                title: My Note
                tags: [setup]
                ---
                See [[getting-started]] and [[index]].

                Also tagged #tutorial here.
            """),
            encoding="utf-8",
        )
        note = parse_note(md)
        assert note.title == "My Note"
        assert note.slug == "my-note"
        assert "getting-started" in note.links
        assert "index" in note.links
        assert "setup" in note.tags
        assert "tutorial" in note.tags

    def test_note_without_frontmatter(self, tmp_path: Path):
        md = tmp_path / "simple.md"
        md.write_text("# Simple\nJust text.\n", encoding="utf-8")
        note = parse_note(md)
        assert note.title == "simple"  # falls back to filename stem
        assert note.slug == "simple"
        assert note.links == []
        assert note.tags == []

    def test_no_duplicate_tags_from_fm_and_body(self, tmp_path: Path):
        md = tmp_path / "dup-tags.md"
        md.write_text(
            "---\ntags: [python]\n---\nTagged #python again.\n",
            encoding="utf-8",
        )
        note = parse_note(md)
        assert note.tags.count("python") == 1
