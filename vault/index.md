---
title: Welcome to Marimo-Obsessed
tags: [meta, start-here]
---

# Welcome to Marimo-Obsessed

This is the root note of your vault.  Every note can link to others using
the `[[WikiLink]]` syntax.

## Quick links

- [[getting-started]] — set up your vault and run the app
- [[plugin-system]] — how the TOML plugin descriptors work
- [[canvas-guide]] — using the tldraw canvas
- [[sync-guide]] — syncing your vault to the cloud

## About

Marimo-Obsessed is an #open-source, #marimo-native knowledge base that
mirrors the core ideas of Obsidian:

| Obsidian feature | Marimo-Obsessed equivalent |
|---|---|
| Vault | `vault/` directory of `.md` files |
| WikiLinks | `[[target]]` parsed by `vault.parser` |
| Graph view | Altair + NetworkX spring layout |
| Canvas | tldraw canvas (embedded via `mo.Html`) |
| Plugins | TOML descriptors + Python entry points |
| Sync | DuckDB / DuckLake + Cloudflare Workers |
