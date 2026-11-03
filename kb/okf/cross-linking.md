---
type: Reference
title: Cross-linking in OKF
description: How OKF concepts link to each other, which fields hold paths, and how consumers treat those links.
tags: [okf, links]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T05:54:02Z }
sources:
  - id: okf-spec
    resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/62432a095456147ee71e70ac6e4dc0d2dea3ac30/okf/SPEC.md
    title: OKF v0.2 specification, §6
---

# Link forms

Concepts link with standard markdown links, two forms:[^okf-spec]

- **Absolute (bundle-relative)** — the target begins with `/` and is resolved
  from the bundle root (e.g. a link whose target is `/tables/customers.md`).
  **Recommended** — stable when a document moves within its subdirectory.
- **Relative** — ordinary relative paths (e.g. a target of `./other.md`).

# Semantics

A link asserts an untyped *relationship*; the kind of relationship is conveyed by
the surrounding prose, not the link. Consumers **must tolerate broken links** — a
link to a not-yet-written concept is valid, not an error. (This repo's
[kb-lint](/kb-plugin/skills.md) still flags them as a hygiene warning so they get
fixed or intentionally stubbed.)

# Path-valued fields

`resource`, `sources[].resource`, and the computation fields accept an absolute
URL, a bundle-relative path beginning with `/`, or a relative path. A
`sources[].resource` may instead be a non-followable scope descriptor. A
`references/` subdirectory is a conventional (not required) home for mirrored
external material that sources point into.

Provenance no longer lives in a body `# Citations` list: v0.2 records it in
frontmatter `sources` with footnote attribution — see
[provenance, trust, and lifecycle](provenance-trust-lifecycle.md) and
[bundle structure and frontmatter](bundle-and-frontmatter.md).

[^okf-spec]: OKF v0.2 specification, §6
