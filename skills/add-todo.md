---
skill: add-todo
name: Add Todo
description: Quick-captures a TK todo item into vault/todos.md
triggers: [tk, todo, add todo, capture]
tags: [productivity, todos]
---

## Intent

Append a new `- [ ] TK: <description>` line to `vault/todos.md` using the
`tk` shorthand.  The file is created automatically if it does not exist.
Triggers the vault index rebuild so the todo appears in the Todos panel
immediately.

## Parameters

| Name | Required | Description |
|------|----------|-------------|
| `description` | yes | What needs to be done |
| `source` | no | Slug of the note this todo relates to (creates a backlink) |

## Steps

1. Parse `tk <description>` from the command bar
2. Call `vault.todos.append_todo(vault_dir, description, source_slug)`
3. Append `- [ ] TK: <description> (from [[source]]) — YYYY-MM-DD` to `todos.md`
4. Rebuild index so the new TK appears in the Todos panel

## Trigger shorthand

Type `tk ` (note the space) followed by your description in the vault app
command bar and press **Enter**:

```
tk revise the introduction section
```

This creates:
```markdown
- [ ] TK: revise the introduction section — 2026-02-19
```

## Notes

- Resolved todos (`- [x]`) are hidden from the pending list automatically
- `vault.todos.resolve_todo()` flips `[ ]` to `[x]` in the source note
