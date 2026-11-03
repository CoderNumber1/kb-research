---
type: Reference
title: The consolidation engine
description: How the kb_analyze tool finds duplicate/overlapping pages and how kb-consolidate merges them, recommend-then-apply.
tags: [plugin, consolidation, deduplication, analyze]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T05:54:02Z }
sources:
  - id: analyze-engine
    resource: https://github.com/CoderNumber1/kb-research/blob/main/src/KnowledgeBase.Mcp/Core/AnalyzeEngine.cs
    title: AnalyzeEngine source
---

# Analysis (kb_analyze)

For every concept page (excluding `raw/` and `domain.md`) the
[kb-mcp server](mcp-server.md) builds a set of stemmed tokens from title + tags +
description + body, finds candidate pairs via an inverted index (a postings cap
bounds cost on large KBs), scores each pair with exact **Jaccard** similarity,
and unions pairs above a threshold (default 0.4) into clusters. It reports
**within-domain** groups (same domain) and **cross-domain** groups (spanning
domains) with a similarity range and an estimated byte saving. A `domain`
argument restricts the analysis to one (sub-)domain. Deterministic.

# The kb-consolidate flow

Recommend-then-apply, always:

1. **Analyze**, then apply semantic judgement — the tool flags candidates; the
   agent reads them and discards lookalikes that are merely on the same topic.
2. **Recommend** — write a numbered report to `consolidation-report.md` (outside
   `kb/`) and stop for user approval.
3. **Apply** only approved items: merge within a domain, or canonicalize a
   cross-domain duplicate into a best-fit existing domain or a new common domain;
   repoint inbound links *before* deleting; fold every unique fact and `sources`
   entry into the canonical page; update indexes/logs; re-lint.

Guardrails: lossless (preserve every unique fact and source), one concept per
page, never touch the user-owned Raw Source Archive. Consolidation also helps
performance — fewer pages mean faster [lint and search](skills.md). Back to
[overview](overview.md).
