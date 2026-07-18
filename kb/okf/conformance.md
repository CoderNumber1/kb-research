---
type: Reference
title: OKF conformance and versioning
description: The three rules a bundle must satisfy to be OKF v0.1 conformant, plus versioning.
tags: [okf, conformance, versioning]
timestamp: 2026-07-18T00:00:00Z
---

# Conformance (§9)

A bundle is **conformant** with OKF v0.1 if:

1. Every non-reserved `.md` file has a parseable YAML frontmatter block.
2. Every frontmatter block has a non-empty `type`.
3. Reserved files (`index.md`, `log.md`) follow their prescribed structure.

Everything else is soft guidance. Consumers **must not** reject a bundle for
missing optional fields, unknown `type` values, unknown extra keys, broken
cross-links, or missing `index.md` files. This permissive model keeps OKF useful
as bundles grow and are partly agent-generated.

See [bundle structure and frontmatter](bundle-and-frontmatter.md) for the field
rules these checks enforce. The [kb-lint](/kb-plugin/skills.md) skill implements
exactly these as ERROR-level checks.

# Versioning

Versions are `<major>.<minor>`. Minor bumps add backward-compatible features;
major bumps may break. A bundle may declare its target version with
`okf_version: "0.1"` in the bundle-root `index.md` — the only place frontmatter
is allowed in an `index.md`.

# Citations

[1] [OKF v0.1 specification, §9 Conformance and §11 Versioning](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
