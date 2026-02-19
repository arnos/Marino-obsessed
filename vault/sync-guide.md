---
title: Sync Guide
tags: [sync, cloudflare, duckdb]
---

# Sync Guide

See also: [[index]], [[canvas-guide]]

Marimo-Obsessed has two optional sync backends that can be used independently
or together.

## DuckDB / DuckLake (local-first)

Uses the `ducklake` DuckDB extension to write Parquet files to Cloudflare R2
(S3-compatible).  Ideal when you want SQL-queryable vault data on the cloud.

```bash
export VAULT_R2_ENDPOINT=https://<account>.r2.cloudflarestorage.com
export VAULT_R2_ACCESS_KEY=<key-id>
export VAULT_R2_SECRET_KEY=<secret>
export VAULT_R2_BUCKET=marimo-obsessed
```

```python
from vault.sync.duckdb_lake import DuckLakeSync

sync = DuckLakeSync("vault.db")
sync.push_note(note)
```

## Cloudflare Workers (serverless API)

A Cloudflare Worker acts as a REST gateway in front of R2.  Notes and canvas
snapshots are stored as R2 objects; the Worker handles authentication and
routing.

```bash
export VAULT_CF_WORKER_URL=https://vault-sync.<you>.workers.dev
export VAULT_CF_API_TOKEN=<shared-secret>
```

```python
from vault.sync.cloudflare import CloudflareWorkerClient

client = CloudflareWorkerClient()
client.push_note(note)
canvas = client.pull_canvas("main")
```

## tldraw real-time sync

For live multi-user canvas collaboration tldraw's `@tldraw/sync` package can
be layered on top using a **Cloudflare Durable Object** as the WebSocket
server.  This is the recommended path for the client wrapper milestone.
