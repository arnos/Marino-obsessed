---
skill: create-note
name: Create Note
description: Creates a new note in the vault with proper frontmatter
triggers: [create, new note, cn, add note]
tags: [vault, productivity]
---

## Intent

Create a new Markdown note in the `vault/` directory with well-formed YAML
frontmatter.  The note is immediately picked up by the vault index on the next
refresh.

## Parameters

| Name | Required | Description |
|------|----------|-------------|
| `title` | yes | Human-readable title of the note |
| `tags` | no | Comma-separated list of tags (e.g. `python, tutorial`) |
| `links` | no | `[[WikiLink]]` references to include in the body stub |

## Steps

1. Derive a slug from the title: lowercase, spaces → hyphens, strip punctuation
2. Write `vault/<slug>.md` with frontmatter block:
   ```yaml
   ---
   title: <title>
   tags: [<tags>]
   ---
   ```
3. Add a stub body: `# <title>\n\nTK: Add content.`
4. Call `VaultIndex.build()` to refresh the index
5. Navigate to the new note in the Editor tab

## Example

```
create A Guide to Polars tags=python,data
```

Creates `vault/a-guide-to-polars.md` with tags `python` and `data`.
