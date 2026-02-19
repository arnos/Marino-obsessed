"""TK (to-come) todo detection and quick-capture.

``TK`` is a classic publishing placeholder meaning "to come" — content that
still needs to be written.  In Marimo-Obsessed every ``TK`` marker in a note
body becomes a trackable todo item.

Supported patterns (matched line-by-line, case-insensitive)
------------------------------------------------------------
- ``- [ ] TK: buy milk``          — Markdown task list with TK prefix
- ``TK: revise introduction``     — Explicit inline TK with description
- ``TK``                          — Bare marker; surrounding line used as context

Quick-capture shorthand
-----------------------
Typing ``tk <description>`` in the vault app's command bar appends a new
``- [ ] TK: <description>`` line to ``vault/todos.md`` (created if absent)
and triggers an index rebuild so the new todo appears immediately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vault.index import VaultIndex

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Markdown task item: "- [ ] TK: optional description"
_TASK_TK_RE = re.compile(r"^[-*]\s+\[\s*\]\s+TK(?::\s*(.+))?$", re.IGNORECASE)
# Standalone "TK: description" (not inside a code block)
_COLON_TK_RE = re.compile(r"^\s*TK:\s*(.+)$", re.IGNORECASE)
# Bare TK anywhere on a line (last resort)
_BARE_TK_RE = re.compile(r"\bTK\b", re.IGNORECASE)

# Lines to skip (code fences, HTML comments)
_SKIP_RE = re.compile(r"^\s*(```|~~~|<!--)")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TodoItem:
    source_slug: str   # slug of the note that contains the marker
    line_no: int       # 1-based line number
    description: str   # human-readable description extracted from the marker
    raw_line: str      # original unmodified line
    resolved: bool = False

    def to_dict(self) -> dict:
        return {
            "source_slug": self.source_slug,
            "line_no": self.line_no,
            "description": self.description,
            "resolved": self.resolved,
        }


@dataclass
class TodoIndex:
    items: list[TodoItem] = field(default_factory=list)

    @property
    def pending(self) -> list[TodoItem]:
        return [t for t in self.items if not t.resolved]

    @property
    def by_note(self) -> dict[str, list[TodoItem]]:
        result: dict[str, list[TodoItem]] = {}
        for item in self.items:
            result.setdefault(item.source_slug, []).append(item)
        return result


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


def scan_todos(index: "VaultIndex") -> TodoIndex:
    """Scan every note in *index* for TK markers and return a :class:`TodoIndex`."""
    result = TodoIndex()
    for slug, note in index.notes.items():
        in_code_block = False
        for line_no, line in enumerate(note.body.splitlines(), start=1):
            # Toggle code-block tracking
            if _SKIP_RE.match(line):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            stripped = line.strip()

            # Pattern 1: markdown task item with TK
            m = _TASK_TK_RE.match(stripped)
            if m:
                desc = (m.group(1) or "").strip() or stripped
                result.items.append(TodoItem(slug, line_no, desc, line))
                continue

            # Pattern 2: "TK: description"
            m = _COLON_TK_RE.match(stripped)
            if m:
                result.items.append(TodoItem(slug, line_no, m.group(1).strip(), line))
                continue

            # Pattern 3: bare TK anywhere on the line
            if _BARE_TK_RE.search(stripped):
                # Use the full line as description context
                desc = stripped.replace("TK", "").strip(" -:").strip() or stripped
                result.items.append(TodoItem(slug, line_no, desc, line))

    return result


# ---------------------------------------------------------------------------
# Quick-capture
# ---------------------------------------------------------------------------


def append_todo(vault_dir: Path, description: str, source_slug: str = "") -> None:
    """Append a new TK todo to ``vault/todos.md``, creating the file if absent.

    Parameters
    ----------
    vault_dir:
        Root of the vault (``Path`` to ``vault/`` directory).
    description:
        Human-readable description of the todo.
    source_slug:
        Optional slug of the note this todo is associated with.  Rendered as
        a ``[[backlink]]`` in the todos file.
    """
    todos_path = vault_dir / "todos.md"
    today = date.today().isoformat()

    if not todos_path.exists():
        todos_path.write_text(
            "---\ntitle: Todos\ntags: [todos, meta]\n---\n\n# Todos\n\n"
            "_Auto-generated by the vault TK quick-capture shorthand._\n\n",
            encoding="utf-8",
        )

    source = f" (from [[{source_slug}]])" if source_slug else ""
    line = f"- [ ] TK: {description}{source} — {today}\n"

    with todos_path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def resolve_todo(vault_dir: Path, item: TodoItem) -> None:
    """Mark a TK item as resolved by replacing ``- [ ]`` with ``- [x]`` in-place."""
    note_path = vault_dir / f"{item.source_slug}.md"
    if not note_path.exists():
        return
    lines = note_path.read_text(encoding="utf-8").splitlines(keepends=True)
    idx = item.line_no - 1  # 0-based
    if 0 <= idx < len(lines):
        lines[idx] = re.sub(r"\[\s*\]", "[x]", lines[idx], count=1)
        note_path.write_text("".join(lines), encoding="utf-8")
        item.resolved = True
