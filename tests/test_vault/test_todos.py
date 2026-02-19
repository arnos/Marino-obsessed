"""Unit tests for vault.todos."""

import textwrap
from pathlib import Path

import pytest

from vault.index import VaultIndex
from vault.todos import TodoItem, append_todo, resolve_todo, scan_todos

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_note(directory: Path, name: str, content: str) -> None:
    (directory / f"{name}.md").write_text(textwrap.dedent(content), encoding="utf-8")


@pytest.fixture()
def vault_with_todos(tmp_path: Path) -> VaultIndex:
    _write_note(tmp_path, "alpha", """\
        ---
        title: Alpha
        ---
        Normal line.
        - [ ] TK: buy milk
        TK: revise introduction
        Just a TK somewhere.
        Already done line.
    """)
    _write_note(tmp_path, "beta", """\
        ---
        title: Beta
        ---
        No todos here.
    """)
    _write_note(tmp_path, "gamma", """\
        ---
        title: Gamma
        ---
        ```
        TK this is inside a code block and must be ignored
        ```
        - [ ] TK: outside the fence
    """)
    idx = VaultIndex(tmp_path)
    idx.build()
    return idx


# ---------------------------------------------------------------------------
# scan_todos
# ---------------------------------------------------------------------------


class TestScanTodos:
    def test_finds_task_item(self, vault_with_todos: VaultIndex):
        todo_idx = scan_todos(vault_with_todos)
        descs = [t.description for t in todo_idx.items if t.source_slug == "alpha"]
        assert any("buy milk" in d for d in descs)

    def test_finds_colon_tk(self, vault_with_todos: VaultIndex):
        todo_idx = scan_todos(vault_with_todos)
        descs = [t.description for t in todo_idx.items if t.source_slug == "alpha"]
        assert any("revise introduction" in d for d in descs)

    def test_finds_bare_tk(self, vault_with_todos: VaultIndex):
        todo_idx = scan_todos(vault_with_todos)
        assert any(t.source_slug == "alpha" for t in todo_idx.items)

    def test_ignores_tk_in_code_block(self, vault_with_todos: VaultIndex):
        todo_idx = scan_todos(vault_with_todos)
        gamma_todos = [t for t in todo_idx.items if t.source_slug == "gamma"]
        descs = [t.description for t in gamma_todos]
        # Only the one outside the fence should appear
        assert all("inside a code block" not in d for d in descs)
        assert any("outside the fence" in d for d in descs)

    def test_clean_note_has_no_todos(self, vault_with_todos: VaultIndex):
        todo_idx = scan_todos(vault_with_todos)
        beta_todos = [t for t in todo_idx.items if t.source_slug == "beta"]
        assert beta_todos == []

    def test_line_numbers_correct(self, vault_with_todos: VaultIndex):
        todo_idx = scan_todos(vault_with_todos)
        alpha_todos = [t for t in todo_idx.items if t.source_slug == "alpha"]
        assert all(t.line_no >= 1 for t in alpha_todos)

    def test_empty_vault(self, tmp_path: Path):
        idx = VaultIndex(tmp_path)
        idx.build()
        todo_idx = scan_todos(idx)
        assert todo_idx.items == []


# ---------------------------------------------------------------------------
# TodoIndex helpers
# ---------------------------------------------------------------------------


class TestTodoIndex:
    def test_pending_excludes_resolved(self, vault_with_todos: VaultIndex):
        todo_idx = scan_todos(vault_with_todos)
        todo_idx.items[0].resolved = True
        assert todo_idx.items[0] not in todo_idx.pending

    def test_by_note_groups_correctly(self, vault_with_todos: VaultIndex):
        todo_idx = scan_todos(vault_with_todos)
        by_note = todo_idx.by_note
        assert "alpha" in by_note
        assert all(t.source_slug == "alpha" for t in by_note["alpha"])

    def test_to_dict(self):
        item = TodoItem("alpha", 3, "do something", "  TK: do something")
        d = item.to_dict()
        assert d["source_slug"] == "alpha"
        assert d["line_no"] == 3
        assert d["description"] == "do something"
        assert d["resolved"] is False


# ---------------------------------------------------------------------------
# append_todo
# ---------------------------------------------------------------------------


class TestAppendTodo:
    def test_creates_file_if_absent(self, tmp_path: Path):
        append_todo(tmp_path, "write tests")
        todos_path = tmp_path / "todos.md"
        assert todos_path.exists()

    def test_appends_tk_line(self, tmp_path: Path):
        append_todo(tmp_path, "write tests")
        content = (tmp_path / "todos.md").read_text()
        assert "TK: write tests" in content

    def test_appends_backlink_when_source_given(self, tmp_path: Path):
        append_todo(tmp_path, "update readme", source_slug="index")
        content = (tmp_path / "todos.md").read_text()
        assert "[[index]]" in content

    def test_second_append_does_not_overwrite(self, tmp_path: Path):
        append_todo(tmp_path, "first todo")
        append_todo(tmp_path, "second todo")
        content = (tmp_path / "todos.md").read_text()
        assert "first todo" in content
        assert "second todo" in content

    def test_frontmatter_in_created_file(self, tmp_path: Path):
        append_todo(tmp_path, "anything")
        content = (tmp_path / "todos.md").read_text()
        assert "---" in content
        assert "todos" in content


# ---------------------------------------------------------------------------
# resolve_todo
# ---------------------------------------------------------------------------


class TestResolveTodo:
    def test_marks_checkbox_resolved(self, tmp_path: Path):
        note = tmp_path / "alpha.md"
        note.write_text("---\ntitle: A\n---\n- [ ] TK: buy milk\n", encoding="utf-8")

        item = TodoItem("alpha", 4, "buy milk", "- [ ] TK: buy milk")
        resolve_todo(tmp_path, item)

        content = note.read_text()
        assert "[x]" in content
        assert item.resolved is True

    def test_nonexistent_note_is_noop(self, tmp_path: Path):
        item = TodoItem("ghost", 1, "task", "- [ ] TK: task")
        resolve_todo(tmp_path, item)  # must not raise
