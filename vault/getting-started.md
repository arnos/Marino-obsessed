---
title: Getting Started
tags: [setup, tutorial]
---

# Getting Started

See also: [[index]], [[plugin-system]]

## Prerequisites

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync project dependencies
uv sync
```

## Running the vault app

```bash
uv run marimo run notebooks/vault_app.py
```

Or in edit mode (to modify the notebook itself):

```bash
uv run marimo edit notebooks/vault_app.py
```

## Adding notes

Drop any `.md` file into the `vault/` directory.  The app rebuilds the index
automatically when you switch tabs.  Use `[[Note Name]]` to link between notes
and `#tag` to tag them.

## Configuration

| Setting | Where |
|---|---|
| Vault directory | `vault/` (default) or set `VAULT_DIR` env var |
| Plugin directory | `plugins/` |
| Sync backend | Environment variables — see [[sync-guide]] |
