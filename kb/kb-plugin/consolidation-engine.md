---
type: Reference
title: The consolidation engine
description: How kb_analyze finds duplicate/overlapping pages and how kb-consolidate merges them, recommend-then-apply.
tags: [plugin, consolidation, deduplication, analyze]
timestamp: 2026-07-18T00:00:00Z
---

# Analysis (kb_analyze)

For every concept page (excluding `raw/` and `domain.md`) it builds a set of
stemmed tokens from title + tags + description + body, finds candidate pairs via
an inverted index (an absolute postings cap bounds cost on large KBs), scores
each candidate pair with exact **Jaccard** similarity, and unions pairs above a
threshold (default 0.4) into clusters. It reports **within-domain** groups
(same domain) and **cross-domain** groups (spanning domains) with a similarity
range and an estimated byte saving. Deterministic and dependency-free.

# The kb-consolidate flow

Recommend-then-apply, always:

1. **Analyze**, then apply semantic judgement — the script flags candidates; the
   agent reads them and discards lookalikes that are merely on the same topic.
2. **Recommend** — write a numbered report to `consolidation-report.md` (outside
   `kb/`) and stop for user approval.
3. **Apply** only approved items: merge within a domain, or canonicalize a
   cross-domain duplicate into a best-fit existing domain or a new common domain;
   repoint inbound links *before* deleting; update indexes/logs; re-lint.

Guardrails: lossless (preserve every unique fact and citation), one concept per
page, never touch immutable [`raw/` snapshots](/okf/bundle-and-frontmatter.md).
Consolidation *helps* performance — fewer pages mean faster
[lint/search](skills.md). Back to [overview](overview.md).
