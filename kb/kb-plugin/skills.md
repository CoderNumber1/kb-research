---
type: Reference
title: The five skills
description: kb-init-domain, kb-ingest, kb-search, kb-lint, and kb-consolidate — what each operation does.
tags: [plugin, skills, operations]
timestamp: 2026-07-18T00:00:00Z
---

# The operations

- **kb-init-domain** — scaffold and register a domain (or nested sub-domain);
  writes `domain.md`, `index.md`, `log.md`, `raw/`, and updates the catalog.
- **kb-ingest** — the write path: snapshot a source, auto-route it to the
  best-matching (sub-)domain by description, distill into cross-linked pages.
- **kb-search** — the read path: rank pages (frontmatter fields weighted above
  body, light stemming), traverse cross-links, answer with citations.
- **kb-lint** — health-check: OKF [conformance](/okf/conformance.md) ERRORs plus
  hygiene WARNINGs (broken-link, orphan, index-drift, dup-title/resource,
  log-date, timestamp) and INFO (recommended fields, stale). `--fix-index` is the
  one automated repair. Exit 1 on any ERROR.
- **kb-consolidate** — find duplicate/overlapping pages and merge them to shrink
  the KB; see the [consolidation engine](consolidation-engine.md).

These realize the three [LLM-wiki operations](/llm-wiki/operations-and-compounding.md)
(ingest/query/lint) plus init and consolidate. Scripts back them in the Python
and PowerShell variants; the scriptless variant follows the same procedures by
hand. Back to [overview](overview.md).
