"""Skill descriptor system for Marimo-Obsessed.

Skills are Markdown files in the ``skills/`` directory that describe *intent*:
what a piece of work should accomplish, what parameters it accepts, and what
steps are involved.  They serve the same role as Claude Code skill files — a
structured prompt template that can be invoked from the vault UI or handed off
to an AI assistant.

Skill file format
-----------------
::

    ---
    skill: create-note
    name: Create Note
    description: Creates a new note in the vault with correct frontmatter
    triggers: [create, new note, cn]
    tags: [productivity, vault]
    ---

    ## Intent

    ...

    ## Parameters

    - `title` (required): The title of the note
    - `tags`  (optional): Comma-separated list of tags

    ## Steps

    1. Write frontmatter block with title + tags
    2. Save to ``vault/<slug>.md``
    3. Rebuild index

Trigger matching
----------------
``tk`` in the vault UI resolves triggers case-insensitively.  Typing ``tk``
as the shorthand prefix *also* activates the todo quick-capture (see
:mod:`vault.todos`).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vault.parser import parse_frontmatter


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SkillDescriptor:
    """Metadata and markdown body of a single skill file."""

    path: Path
    skill_id: str       # ``skill`` frontmatter field
    name: str
    description: str
    triggers: list[str]
    tags: list[str]
    body: str           # markdown body (frontmatter stripped)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def slug(self) -> str:
        return self.path.stem

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "triggers": self.triggers,
            "tags": self.tags,
        }


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


class SkillIndex:
    """Scans a ``skills/`` directory and indexes all skill descriptors."""

    def __init__(self, skills_dir: Path) -> None:
        self.skills_dir = Path(skills_dir)
        self.skills: dict[str, SkillDescriptor] = {}

    def build(self) -> None:
        """(Re-)scan the skills directory."""
        self.skills = {}
        if not self.skills_dir.exists():
            return
        for path in sorted(self.skills_dir.glob("**/*.md")):
            try:
                skill = _parse_skill(path)
                self.skills[skill.slug] = skill
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] Failed to load skill {path.name}: {exc}", file=sys.stderr)

    def search(self, query: str) -> list[SkillDescriptor]:
        """Full-text search over name, description, and triggers."""
        q = query.lower()
        return [
            s
            for s in self.skills.values()
            if q in s.name.lower()
            or q in s.description.lower()
            or any(q in t.lower() for t in s.triggers)
            or any(q in t.lower() for t in s.tags)
        ]

    def by_trigger(self, trigger: str) -> list[SkillDescriptor]:
        """Return skills whose triggers exactly match *trigger* (case-insensitive)."""
        t = trigger.lower()
        return [s for s in self.skills.values() if any(t == tr.lower() for tr in s.triggers)]

    def resolve_shorthand(self, text: str) -> list[SkillDescriptor]:
        """Resolve a free-text shorthand to matching skills (prefix or exact trigger)."""
        t = text.lower().strip()
        exact = self.by_trigger(t)
        if exact:
            return exact
        return self.search(t)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _parse_skill(path: Path) -> SkillDescriptor:
    content = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(content)

    triggers = meta.get("triggers") or []
    if isinstance(triggers, str):
        triggers = [t.strip() for t in triggers.split(",") if t.strip()]

    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    return SkillDescriptor(
        path=path,
        skill_id=meta.get("skill", path.stem),
        name=meta.get("name", path.stem),
        description=meta.get("description", ""),
        triggers=triggers,
        tags=tags,
        body=body,
        meta={
            k: v
            for k, v in meta.items()
            if k not in {"skill", "name", "description", "triggers", "tags"}
        },
    )
