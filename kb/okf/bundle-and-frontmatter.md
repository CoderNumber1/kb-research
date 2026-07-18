---
type: Reference
title: Bundle structure and frontmatter
description: How an OKF knowledge bundle is laid out and what frontmatter each concept carries.
tags: [okf, bundle, frontmatter]
timestamp: 2026-07-18T00:00:00Z
---

# Bundle

An OKF **bundle** is a directory tree of markdown files. A **concept** is one
markdown document; its **concept ID** is its path within the bundle minus the
`.md` suffix (`tables/users.md` → `tables/users`). Directory structure is free —
producers organize concepts however suits the knowledge.

# Reserved filenames

| Filename   | Purpose |
|------------|---------|
| `index.md` | Directory listing for progressive disclosure (see [cross-linking](cross-linking.md)). |
| `log.md`   | Chronological update history, newest first, `## YYYY-MM-DD` headings. |

All other `.md` files are concept documents.

# Frontmatter

Each concept is YAML frontmatter + markdown body. **`type` is the only required
field.** Recommended (in priority order): `title`, `description`, `resource`
(canonical URI for a concrete asset), `tags`, `timestamp` (ISO 8601). Producers
may add any extra keys; consumers preserve unknown keys and never reject on them.

`index.md` files carry **no** frontmatter, except the bundle-root `index.md`,
which may hold only `okf_version`. See [conformance](conformance.md) for the
rules a bundle must satisfy.

# Citations

[1] [OKF v0.1 specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
[2] [How the Open Knowledge Format can improve data sharing (Google Cloud)](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/)
