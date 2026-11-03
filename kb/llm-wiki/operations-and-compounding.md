---
type: Reference
title: The three operations and the compounding discipline
description: Ingest, query, and lint — plus the end-of-turn capture sweep that makes knowledge compound.
tags: [llm-wiki, operations, ingest, query, lint]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T05:54:02Z }
sources:
  - id: andrej-karpathy-llm-wiki-gist
    resource: "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"
    title: "Andrej Karpathy, \"llm-wiki\" gist"
---

# Three operations

- **Ingest** — process a source: read the raw input, extract durable facts,
  create or update wiki pages (preferring updates so knowledge compounds), wire
  in cross-links and citations, refresh index and log.
- **Query** — search the wiki, traverse via index/cross-links, synthesize a
  cited answer. Durable new conclusions are worth writing back.
- **Lint** — health-check for contradictions, orphans, broken/missing links,
  stale claims, and index drift.

This repo maps these to the [kb-ingest, kb-search, and kb-lint skills](/kb-plugin/skills.md).

# Compounding discipline

The wiki only compounds if new understanding is actually written down. Knowledge
discovered mid-task evaporates between sessions unless captured, so this repo's
plugin has a **capture sweep** (`kb-capture`): before finishing, it identifies
durable, un-documented knowledge surfaced during the turn and ingests it. A
repository runs it either automatically at the end of every turn or explicitly
through the `knowledge-curator` agent — see the
[capture modes](/kb-plugin/overview.md). This ingestion of the session that
built the plugin is itself an example.

See [the pattern and its layers](pattern-and-layers.md).
