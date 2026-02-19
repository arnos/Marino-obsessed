---
skill: query-vault
name: Query Vault
description: Run a SQL query against the vault database (VaultDB / Bases view)
triggers: [query, sql, db, search sql, bases]
tags: [database, productivity]
---

## Intent

Run an ad-hoc DuckDB SQL query against the vault's in-memory database.  The
`notes` table exposes `slug`, `title`, `body`, `tags`, `links`, and
`frontmatter` (JSON).  Results are returned as a Polars DataFrame displayed
in the Database tab.

## Parameters

| Name | Required | Description |
|------|----------|-------------|
| `sql` | yes | A valid DuckDB SQL statement |

## Common queries

```sql
-- All notes tagged "python"
SELECT slug, title FROM notes WHERE 'python' = ANY(tags);

-- Notes that link to "index"
SELECT slug, title FROM notes WHERE 'index' = ANY(links);

-- Tag frequency table
SELECT tag, COUNT(*) AS count
FROM (SELECT unnest(tags) AS tag FROM notes)
GROUP BY tag ORDER BY count DESC;

-- Notes with a "status" frontmatter property
SELECT slug, title, json_extract_string(frontmatter, '$.status') AS status
FROM notes
WHERE json_extract_string(frontmatter, '$.status') IS NOT NULL;

-- Full-text search
SELECT slug, title FROM notes WHERE body ILIKE '%marimo%';
```

## Steps

1. Open the **Database** tab in the vault app
2. Type your SQL in the query input and press **Run**
3. Results appear as an interactive Polars/Marimo table below

## Notes

- The `frontmatter` column is a JSON string; use `json_extract_string()` or
  `json_extract()` to reach nested fields
- `tags` and `links` are `VARCHAR[]` arrays; use `= ANY(tags)` or
  `list_contains(tags, 'value')` for membership checks
- The database is rebuilt each time `VaultIndex.build()` is called
