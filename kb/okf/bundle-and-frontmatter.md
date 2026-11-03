---
type: Reference
title: Bundle structure and frontmatter
description: How an OKF v0.2 knowledge bundle is laid out and what frontmatter each concept carries.
tags: [okf, bundle, frontmatter]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T05:54:02Z }
sources:
  - id: okf-spec
    resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/62432a095456147ee71e70ac6e4dc0d2dea3ac30/okf/SPEC.md
    title: OKF v0.2 specification, §3–4
  - id: okf-announcement
    resource: "https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/"
    title: How the Open Knowledge Format can improve data sharing (Google Cloud)
---

# Bundle

An OKF **bundle** is a directory tree of markdown files. A **concept** is one
markdown document; its **concept ID** is its path within the bundle minus the
`.md` suffix (`tables/users.md` → `tables/users`). Directory structure is free —
producers organize concepts however suits the knowledge.[^okf-spec] OKF is
Google Cloud's open format for knowledge about data and systems.[^okf-announcement]

# Reserved filenames

| Filename   | Purpose |
|------------|---------|
| `index.md` | Directory listing for progressive disclosure (see [cross-linking](cross-linking.md)). |
| `log.md`   | Chronological update history, newest first, `## YYYY-MM-DD` headings. |

All other `.md` files are concept documents.

# Frontmatter

Each concept is YAML frontmatter + markdown body. **`type` is the only required
field**; values are free text, never centrally registered, and consumers
tolerate unknown types. Recommended: `title`, `description`, `resource` (a URI
for the concrete asset the concept describes — absent for abstract ideas), and
`tags`.

v0.2 adds optional families for provenance (`sources`), trust (`generated`,
`verified`), and lifecycle (`status`, `stale_after`) — see
[provenance, trust, and lifecycle](provenance-trust-lifecycle.md) — plus
computation keys for `Attested Computation` concepts. v0.1's `timestamp` is
superseded by `generated.at`.

**Extensions:** producers may add any keys; consumers preserve unknown keys and
never reject on them. A key OKF itself defines (such as `status`) is not an
extension: reusing it with other values defeats its meaning.

`index.md` files carry **no** frontmatter, except the bundle-root `index.md`,
which may hold only `okf_version`. See [conformance](conformance.md) for the
rules a bundle must satisfy.

[^okf-spec]: OKF v0.2 specification, §3–4
[^okf-announcement]: How the Open Knowledge Format can improve data sharing (Google Cloud)
