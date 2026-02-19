---
skill: sync-vault
name: Sync Vault
description: Push all local notes and canvas state to the configured sync backend
triggers: [sync, push, upload, backup]
tags: [sync, cloudflare, duckdb]
---

## Intent

Iterate over every note in the vault index and push it to the active sync
backend (DuckLake or Cloudflare Workers).  Also persist the current tldraw
canvas snapshot under the key `main`.

## Parameters

| Name | Required | Description |
|------|----------|-------------|
| `backend` | no | `ducklake` (default) or `cloudflare` |
| `canvas_id` | no | Canvas snapshot key (default: `main`) |

## Steps

1. Instantiate the sync backend from environment variables:
   - `VAULT_R2_*` for DuckLake / R2
   - `VAULT_CF_*` for Cloudflare Workers
2. For each note in `VaultIndex.notes.values()`:
   - Call `backend.push_note(note)`
3. Retrieve the current tldraw snapshot from the canvas plugin
4. Call `backend.push_canvas(canvas_id, snapshot)`
5. Report how many notes were synced

## Environment variables

```bash
# DuckLake / Cloudflare R2
export VAULT_R2_ENDPOINT=https://<account>.r2.cloudflarestorage.com
export VAULT_R2_ACCESS_KEY=<key>
export VAULT_R2_SECRET_KEY=<secret>
export VAULT_R2_BUCKET=marimo-obsessed

# Cloudflare Workers gateway
export VAULT_CF_WORKER_URL=https://vault-sync.<you>.workers.dev
export VAULT_CF_API_TOKEN=<token>
```

## Notes

- See [[sync-guide]] for full sync architecture details
- tldraw real-time sync via Durable Objects is a separate layer on top of this
