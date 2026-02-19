"""WikiLink, tag, and YAML-frontmatter parser."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from vault.note import Note

# [[Target]] or [[Target|Alias]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
# Inline #tags (not inside code-spans or URLs)
_TAG_RE = re.compile(r"(?<![`\w/#])#([\w/-]+)")
# YAML front-matter block
_FRONTMATTER_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", re.DOTALL)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Split YAML front-matter from body text.

    Returns ``(metadata_dict, body)``; ``metadata_dict`` is empty when there
    is no front-matter block.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    try:
        meta: dict[str, Any] = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, content[match.end() :]


def parse_wikilinks(text: str) -> list[str]:
    """Return all ``[[WikiLink]]`` targets found in *text* (de-duped, ordered)."""
    seen: set[str] = set()
    result: list[str] = []
    for m in _WIKILINK_RE.finditer(text):
        target = m.group(1).strip()
        if target not in seen:
            seen.add(target)
            result.append(target)
    return result


def parse_tags(text: str) -> list[str]:
    """Return all ``#tag`` values found in *text* (de-duped, ordered)."""
    seen: set[str] = set()
    result: list[str] = []
    for m in _TAG_RE.finditer(text):
        tag = m.group(1)
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


def parse_note(path: Path) -> "Note":
    """Read a ``.md`` file and return a fully-populated :class:`Note`."""
    from vault.note import Note

    content = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    links = parse_wikilinks(body)
    inline_tags = parse_tags(body)
    fm_tags: list[str] = frontmatter.get("tags") or []
    if isinstance(fm_tags, str):
        fm_tags = [t.strip() for t in fm_tags.split(",") if t.strip()]
    all_tags = list(dict.fromkeys(fm_tags + inline_tags))

    title: str = frontmatter.get("title") or path.stem

    return Note(
        path=path,
        title=title,
        body=body,
        tags=all_tags,
        links=links,
        frontmatter=frontmatter,
    )
