---
type: Reference
title: Determinism and Python/PowerShell parity
description: Historical — the techniques used to make the retired PowerShell scripts emit byte-identical JSON to the retired Python scripts, and the determinism lesson that still applies.
tags: [plugin, parity, powershell, determinism, history]
status: deprecated
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T05:54:02Z }
---

> **Deprecated.** The Python and PowerShell [variants](variants.md) were
> retired on 2026-10-27. The determinism lesson below still governs the
> [kb-mcp server](mcp-server.md); the PowerShell specifics are history.

# Goal (historical)

The PowerShell scripts had to emit **byte-identical JSON** to the Python
scripts so the variants were interchangeable; parity tests enforced it.

# Determinism fixes (still applicable)

Reaching parity surfaced two real non-determinism bugs in the original Python:

- **kb_search** tie-broke equal scores by filesystem enumeration order → made
  deterministic by adding a secondary sort on `path`.
- **kb_lint** emitted duplicate-title/resource paths in walk order → sorted them.

Lesson: any output that depends on directory-walk order is non-deterministic
across machines; add an explicit tiebreak.

# PowerShell gotchas (historical)

- **Empty arrays** → `ConvertTo-Json` renders an empty pipeline result as
  `[null]`; build arrays from a typed `List[T]` and return `.ToArray()`.
- Force arrays with `@(...)` and use `ConvertTo-Json -Depth N`; ordered output
  via `[ordered]@{}`.
- Emulate Python `repr()` for lint messages that use `{x!r}`.
- Match Python's blob/token construction (field order, spacing) exactly, since
  the stemmer/tokenizer feeds similarity scores.

Parity was verified by diffing JSON (ignoring the absolute `kb_root`) across
detect/search/lint/analyze and `--fix-index` file output.
