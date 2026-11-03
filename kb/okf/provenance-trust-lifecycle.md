---
type: Reference
title: Provenance, trust, and lifecycle (OKF v0.2)
description: The optional v0.2 frontmatter families — sources with footnote attribution, generated/verified trust, status and stale_after lifecycle — and the actor and datetime conventions they use.
tags: [okf, provenance, trust, lifecycle, sources]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T05:54:02Z }
sources:
  - id: okf-spec
    resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/62432a095456147ee71e70ac6e4dc0d2dea3ac30/okf/SPEC.md
    title: OKF v0.2 specification, §5, §7, §13
---

All of these are optional; their absence carries meaning (an unverified concept
is distinguishable from a verified one) but never makes a concept rejectable.
Every timestamp is ISO 8601 with an explicit UTC offset.[^okf-spec]

# Provenance: `sources`

`sources` lists what a concept derives from. Each entry **requires
`resource`** — an absolute URL, a bundle-relative or relative path, or a scope
descriptor that is not followable (e.g. "all queries in project X") — and may
carry `id`, `title`, and the credibility signals `author`, `usage_count`, and
`last_modified`. A sibling `usage_window: { from, to }` frames usage counts.

Specific claims are attributed with markdown footnotes whose label is a source
`id` (`[^ga4-schema]`). Labels are keyed, not positional, because agents
constantly rewrite documents and a reordered list would silently misattribute.
Credibility is inferred from the signals, never stored as a score. A
`resource` pointing at another concept is a lineage edge in the bundle graph.

v0.2 supersedes the v0.1 body `# Citations` list; consumers may still parse it
as a fallback.

# Trust: `generated` and `verified`

- `generated: { by, at }` — who produced the current content (`by` required)
  and when it last meaningfully changed. Supersedes v0.1 `timestamp`.
- `verified` — a list of `{ by, at }` confirmation events, independent of
  `generated`. A single bare mapping must be read as a one-element list.
- **Trust tiers** are derived: no `verified` → unverified; only non-human
  verifiers → machine-confirmed; any `human:` verifier → human-reviewed. They
  are advisory, not access control.

# Actors

Identity fields use one convention: `<producer>/<version>` for agents and tools
(`reference_agent/gemini-2.5-pro`), `human:<id>` for people, `process:<id>` for
automated processes. Producers must use `human:` for hand-authored or
human-confirmed content, because trust tiers key off that prefix.

# Lifecycle: `status` and `stale_after`

- `status` is `draft` (unreviewed, possibly incomplete), `stable` (the default
  when absent), or `deprecated` (kept for links and history).
- `stale_after` is an absolute instant; a concept is stale when now is on or
  after it. An absolute instant keeps staleness a plain comparison.

This plugin's [lint](/kb-plugin/skills.md) validates all of these, and its
[MCP server](/kb-plugin/mcp-server.md) routes away from `deprecated` domains.
See also [bundle structure and frontmatter](bundle-and-frontmatter.md).

[^okf-spec]: OKF v0.2 specification, §5, §7, §13
