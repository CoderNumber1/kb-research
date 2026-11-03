---
type: Reference
title: OKF conformance and versioning
description: The three rules a bundle must satisfy to be OKF v0.2 conformant, what consumers must tolerate, and how versions and the v0.1→v0.2 changes work.
tags: [okf, conformance, versioning]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T05:54:02Z }
sources:
  - id: okf-spec
    resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/62432a095456147ee71e70ac6e4dc0d2dea3ac30/okf/SPEC.md
    title: OKF v0.2 specification, §11–13
---

# Conformance (§11)

A bundle is **conformant** with OKF v0.2 if:[^okf-spec]

1. Every non-reserved `.md` file has a parseable YAML frontmatter block.
2. Every frontmatter block has a non-empty `type`.
3. Reserved files (`index.md`, `log.md`) follow their prescribed structure.

When the provenance, trust, lifecycle, or computation families are present,
producers should follow their rules and consumers must read a bare `verified`
mapping as a one-element list, must not reject a concept for missing any
optional family, and should derive trust tiers and staleness only from the
specified fields.

Everything else is soft guidance. Consumers **must not** reject a bundle for
missing optional fields, unknown `type` values, unknown extra keys, broken
cross-links, or missing `index.md` files. This permissive model keeps OKF useful
as bundles grow and are partly agent-generated.

The [kb-lint](/kb-plugin/skills.md) skill implements the three rules as
ERROR-level checks and the family rules as warnings; see
[provenance, trust, and lifecycle](provenance-trust-lifecycle.md).

# Versioning (§12)

Versions are `<major>.<minor>`. Minor bumps add backward-compatible features;
major bumps may break. A bundle may declare its target with
`okf_version: "0.2"` in the bundle-root `index.md` — the only place frontmatter
is allowed in an `index.md`. Consumers that don't understand a declared version
should attempt best-effort consumption.

# Changes from v0.1 (§13)

v0.2 is a minor bump with two deliberate breaking changes, both with consumer
fallbacks:

- `timestamp` is superseded by `generated.at`.
- The body `# Citations` list is superseded by frontmatter `sources`.

Everything else — bundle structure, reserved filenames, required `type`,
recommended fields, cross-linking, index and log files, permissive
conformance — carries forward unchanged. See
[bundle structure and frontmatter](bundle-and-frontmatter.md).

[^okf-spec]: OKF v0.2 specification, §11–13
