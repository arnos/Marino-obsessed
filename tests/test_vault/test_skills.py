"""Unit tests for vault.skills."""

import textwrap
from pathlib import Path

import pytest

from vault.skills import SkillDescriptor, SkillIndex, _parse_skill


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def skills_dir(tmp_path: Path) -> Path:
    """Minimal skills directory with two skill files."""
    (tmp_path / "create-note.md").write_text(
        textwrap.dedent("""\
            ---
            skill: create-note
            name: Create Note
            description: Creates a new vault note
            triggers: [create, cn, new note]
            tags: [productivity]
            ---

            ## Intent

            Creates a new Markdown note in the vault.

            ## Steps

            1. Derive slug
            2. Write file
        """),
        encoding="utf-8",
    )
    (tmp_path / "add-todo.md").write_text(
        textwrap.dedent("""\
            ---
            skill: add-todo
            name: Add Todo
            description: Quick-captures a TK todo item
            triggers: [tk, todo, capture]
            tags: [productivity, todos]
            ---

            ## Intent

            Append a todo to todos.md using the TK shorthand.
        """),
        encoding="utf-8",
    )
    return tmp_path


# ---------------------------------------------------------------------------
# SkillDescriptor
# ---------------------------------------------------------------------------


class TestSkillDescriptor:
    def test_parse_basic(self, skills_dir: Path):
        skill = _parse_skill(skills_dir / "create-note.md")
        assert skill.skill_id == "create-note"
        assert skill.name == "Create Note"
        assert skill.description == "Creates a new vault note"
        assert "create" in skill.triggers
        assert "cn" in skill.triggers
        assert "productivity" in skill.tags
        assert skill.slug == "create-note"

    def test_body_contains_steps(self, skills_dir: Path):
        skill = _parse_skill(skills_dir / "create-note.md")
        assert "## Steps" in skill.body

    def test_to_dict_keys(self, skills_dir: Path):
        skill = _parse_skill(skills_dir / "add-todo.md")
        d = skill.to_dict()
        assert set(d.keys()) == {"slug", "skill_id", "name", "description", "triggers", "tags"}

    def test_slug_is_stem(self, skills_dir: Path):
        skill = _parse_skill(skills_dir / "create-note.md")
        assert skill.slug == "create-note"

    def test_triggers_as_string(self, tmp_path: Path):
        """Triggers given as a comma-separated string (not list) should be parsed."""
        f = tmp_path / "s.md"
        f.write_text(
            "---\nskill: s\nname: S\ndescription: D\ntriggers: a, b, c\n---\nBody.\n",
            encoding="utf-8",
        )
        skill = _parse_skill(f)
        assert skill.triggers == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# SkillIndex
# ---------------------------------------------------------------------------


class TestSkillIndex:
    def test_build_loads_all_skills(self, skills_dir: Path):
        idx = SkillIndex(skills_dir)
        idx.build()
        assert set(idx.skills.keys()) == {"create-note", "add-todo"}

    def test_empty_dir_does_not_raise(self, tmp_path: Path):
        idx = SkillIndex(tmp_path)
        idx.build()
        assert idx.skills == {}

    def test_nonexistent_dir_does_not_raise(self, tmp_path: Path):
        idx = SkillIndex(tmp_path / "no-such-dir")
        idx.build()
        assert idx.skills == {}

    def test_search_by_name(self, skills_dir: Path):
        idx = SkillIndex(skills_dir)
        idx.build()
        results = idx.search("Create")
        assert any(s.slug == "create-note" for s in results)

    def test_search_by_description(self, skills_dir: Path):
        idx = SkillIndex(skills_dir)
        idx.build()
        results = idx.search("vault note")
        assert any(s.slug == "create-note" for s in results)

    def test_search_by_trigger(self, skills_dir: Path):
        idx = SkillIndex(skills_dir)
        idx.build()
        results = idx.search("tk")
        assert any(s.slug == "add-todo" for s in results)

    def test_by_trigger_exact(self, skills_dir: Path):
        idx = SkillIndex(skills_dir)
        idx.build()
        results = idx.by_trigger("capture")
        assert len(results) == 1
        assert results[0].slug == "add-todo"

    def test_by_trigger_case_insensitive(self, skills_dir: Path):
        idx = SkillIndex(skills_dir)
        idx.build()
        assert idx.by_trigger("TK") == idx.by_trigger("tk")

    def test_resolve_shorthand_exact_trigger(self, skills_dir: Path):
        idx = SkillIndex(skills_dir)
        idx.build()
        results = idx.resolve_shorthand("cn")
        assert any(s.slug == "create-note" for s in results)

    def test_resolve_shorthand_falls_back_to_search(self, skills_dir: Path):
        idx = SkillIndex(skills_dir)
        idx.build()
        results = idx.resolve_shorthand("todo")
        assert len(results) >= 1

    def test_bad_skill_skipped(self, tmp_path: Path):
        """A skill file that fails to parse should not prevent others from loading."""
        (tmp_path / "good.md").write_text(
            "---\nskill: good\nname: Good\ndescription: D\ntriggers: [g]\ntags: []\n---\nBody.\n",
            encoding="utf-8",
        )
        (tmp_path / "bad.md").write_text("not yaml at all {{{{ ]]]]", encoding="utf-8")
        idx = SkillIndex(tmp_path)
        idx.build()
        assert "good" in idx.skills
