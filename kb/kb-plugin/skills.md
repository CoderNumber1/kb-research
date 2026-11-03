---
type: Reference
title: The eight skills
description: kb-init, kb-init-domain, kb-ingest, kb-search, kb-lint, kb-consolidate, kb-capture, and kb-raw-audit — what each operation does and which MCP tools it calls.
tags: [plugin, skills, operations]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T05:54:02Z }
sources:
  - id: plugin-skills
    resource: https://github.com/CoderNumber1/kb-research/tree/main/plugins/okf-knowledge-base/skills
    title: okf-knowledge-base skills
---

# The operations

| Skill | Does | MCP tools |
|-------|------|-----------|
| **kb-init** | Bootstrap a KB in a repository: asks automatic vs explicit (agent) capture, creates `kb/`, writes the `<knowledge-base>` directive, hands off to kb-init-domain. Re-run to switch mode. | `kb_init` |
| **kb-init-domain** | Scaffold and register a domain or nested sub-domain (`domain.md`, `index.md`, `log.md`; no `raw/`). Requires an initialized root. | `kb_detect_domain`, `kb_init_domain` |
| **kb-ingest** | The write path: route to the best-matching (sub-)domain, reuse in-turn searches, compile OKF v0.2 pages with `generated` and `sources`; asks before creating a domain for a low-confidence fit. | `kb_detect_domain`, `kb_search`, `kb_lint` |
| **kb-search** | The read path: rank pages, traverse cross-links, answer with citations; "no hits" is never a "no" — fall back to code, external sources, then "I don't know". | `kb_search`, `kb_detect_domain` |
| **kb-lint** | OKF v0.2 conformance ERRORs, hygiene WARNINGs, INFO signals; `fix_index` is the one automated repair. | `kb_lint` |
| **kb-consolidate** | Find duplicate/overlapping pages and merge them, recommend-then-apply; see the [consolidation engine](consolidation-engine.md). | `kb_analyze`, `kb_search`, `kb_lint` |
| **kb-capture** | The end-of-turn sweep: scan, filter to durable knowledge, ingest, reconcile, lint, report. | via kb-ingest |
| **kb-raw-audit** | Explicit-only (`disable-model-invocation`), two-phase migration of legacy raw snapshots: a read-only report, then only user-named actions with hash-verified moves. | `kb_lint` |

These realize the three [LLM-wiki operations](/llm-wiki/operations-and-compounding.md)
(ingest, query, lint) plus bootstrap, init, consolidate, and capture. The tools
are described under [the MCP server](mcp-server.md). Back to [overview](overview.md).
