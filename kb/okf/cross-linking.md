---
type: Reference
title: Cross-linking in OKF
description: How OKF concepts link to each other and how consumers treat those links.
tags: [okf, links]
timestamp: 2026-07-18T00:00:00Z
---

# Link forms

Concepts link with standard markdown links, two forms:

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

Citations to external sources go under a `# Citations` heading, numbered. See
[bundle structure and frontmatter](bundle-and-frontmatter.md).

# Citations

[1] [OKF v0.1 specification, §5 Cross-linking](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
