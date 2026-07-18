---
type: Reference
title: Determinism and Python/PowerShell parity
description: Techniques and gotchas for making the PowerShell scripts produce byte-identical JSON to the Python scripts.
tags: [plugin, parity, powershell, determinism]
timestamp: 2026-07-18T00:00:00Z
---

# Goal

The PowerShell scripts must emit **byte-identical JSON** to the Python scripts so
the [variants](variants.md) are interchangeable; parity tests enforce it (skipped
where `pwsh` is absent).

# Determinism fixes (applied to both engines)

Reaching parity surfaced two real non-determinism bugs in the original Python:

- **kb_search** tie-broke equal scores by filesystem enumeration order → made
  deterministic by adding a secondary sort on `path`.
- **kb_lint** emitted duplicate-title/resource paths in walk order → sorted them.

Lesson: any output that depends on directory-walk order is non-deterministic
across machines; add an explicit tiebreak.

# PowerShell gotchas

- **Empty arrays** → `ConvertTo-Json` renders an empty pipeline result as
  `[null]`; build arrays from a typed `List[T]` and return `.ToArray()`.
- Force arrays with `@(...)` and use `ConvertTo-Json -Depth N`; ordered output
  via `[ordered]@{}`.
- Emulate Python `repr()` for lint messages that use `{x!r}`.
- Match Python's blob/token construction (field order, spacing) exactly, since
  the [stemmer/tokenizer](scripts-and-autodetection.md) feeds similarity scores.

Parity is verified by diffing JSON (ignoring the absolute `kb_root`) across
detect/search/lint/analyze and `--fix-index` file output. Back to
[the variants](variants.md).
