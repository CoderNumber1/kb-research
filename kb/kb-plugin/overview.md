---
type: Reference
title: KB plugin — overview
description: This repo is a marketplace hosting three variants of an OKF/LLM-wiki knowledge-base plugin, dogfooded against the kb/ bundle.
tags: [plugin, overview, marketplace]
timestamp: 2026-07-18T00:00:00Z
---

# What this repo is

`kb-research` packages an agent-operated knowledge base as reusable
[Claude Code plugins](/claude-code/plugins-and-marketplace.md) and dogfoods them
against the example bundle in `kb/`. It implements the
[OKF](/okf/bundle-and-frontmatter.md) format and the
[LLM-wiki](/llm-wiki/pattern-and-layers.md) workflow.

The repo is simultaneously a one-marketplace, **three-plugin** project:

- [`okf-knowledge-base`](variants.md) — Python scripts.
- `okf-knowledge-base-powershell` — PowerShell scripts, output identical to Python.
- `okf-knowledge-base-scriptless` — skills do the work with built-in file tools.

# The pieces

- [Five skills](skills.md): kb-init-domain, kb-ingest, kb-search, kb-lint,
  kb-consolidate.
- A `knowledge-curator` agent with an end-of-turn capture sweep.
- [Scripts + KB autodetection](scripts-and-autodetection.md) and a SessionStart
  detector hook.
- A [consolidation engine](consolidation-engine.md) for deduplication.
- [Determinism and cross-language parity](determinism-and-parity.md) discipline.
- `benchmarks/` comparing the variants.

Install exactly one variant — they share skill names.
