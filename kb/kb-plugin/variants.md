---
type: Reference
title: Plugin engine variants (history)
description: The Python, PowerShell, and scriptless variants the plugin shipped until 2026-10-27, what the benchmarks showed, and why a single C# MCP engine replaced them.
tags: [plugin, variants, benchmark, powershell, history]
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-03T03:53:28Z }
sources:
  - id: benchmarks
    resource: https://github.com/CoderNumber1/kb-research/tree/3d4c51d/benchmarks
    title: Cross-variant benchmark harness and results (last commit before removal)
  - id: decision
    resource: conversation on 2026-10-27
    title: Decision to replace all variants with the C# MCP server
---

# The three variants (retired)

Until 2026-10-27 the marketplace shipped three interchangeable plugins with the
same skills, agent, and detector hook, differing only in *how the work
happened*:

| Variant | Engine | Dependency |
|---------|--------|------------|
| `okf-knowledge-base` | pure-stdlib Python scripts | Python 3 |
| `okf-knowledge-base-powershell` | PowerShell scripts, byte-identical JSON to Python | PowerShell 7+ |
| `okf-knowledge-base-scriptless` | skills instructed the agent to use file tools | none |

# What the benchmarks showed

Python and PowerShell produced identical output (enforced by
[parity tests](determinism-and-parity.md)). PowerShell's per-invocation startup
(~0.7–0.9 s) made it ~15–50× slower per call, because every skill call spawned
a fresh process. The scriptless variant's cost scaled with the bytes an agent
had to read into context, so it suited small KBs only.[^benchmarks]

# Why one C# engine replaced them

The variants were removed in favor of the [kb-mcp server](mcp-server.md): one
persistent process with a warm page cache (no per-call startup cost), no runtime
to install (self-contained binaries), and one implementation to keep correct
instead of a cross-language parity discipline.[^decision] Its suitability for
cloud sessions was established first — see
[cloud feasibility](csharp-mcp-variant.md).

On 2026-11-02 a stdlib-only Python port of that server became what the plugin
ships, so no built binaries need committing; the C# server stays as an
equivalent, and one test suite verifies both. Unlike the retired script
variants, the two are kept identical by running the same tests against each
rather than by a separate parity harness. Back to [overview](overview.md).

[^benchmarks]: Cross-variant benchmark harness and results
[^decision]: Decision to replace all variants with the C# MCP server
