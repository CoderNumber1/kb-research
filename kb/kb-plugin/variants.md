---
type: Reference
title: The three plugin variants
description: Python, PowerShell, and scriptless variants — how they differ and when to pick each, with benchmark findings.
tags: [plugin, variants, benchmark, powershell]
timestamp: 2026-07-18T00:00:00Z
---

# The variants

All three expose the same [five skills](skills.md), agent, and detector hook;
they differ only in *how the work happens*. Install exactly one — they share
skill names, so enabling two collides.

| Variant | Engine | Dependency |
|---------|--------|------------|
| `okf-knowledge-base` | pure-stdlib Python scripts | Python 3 |
| `okf-knowledge-base-powershell` | PowerShell scripts, byte-identical JSON to Python | PowerShell 7+ |
| `okf-knowledge-base-scriptless` | skills instruct the agent to do it with file tools | none |

# When to pick which

- **Scripts (Python/PowerShell)** — large KBs, CI gating, reproducible output.
- **Scriptless** — zero-setup / no-runtime environments, small personal KBs.

# Benchmark findings

Python and PowerShell produce **identical** output (enforced by parity tests).
PowerShell's per-invocation startup (~0.7–0.9 s) dominates, making it ~15–50×
slower per call — a real cost since each skill call spawns a fresh process; the
gap narrows as work grows. The scriptless variant isn't wall-timed (it needs the
model in the loop); its cost scales with the bytes an agent must read into
context, so it is best on small KBs and the script variants win at scale.
Achieving Python/PowerShell parity required a shared discipline — see
[determinism and parity](determinism-and-parity.md). Back to [overview](overview.md).
