---
type: Reference
title: KB plugin — overview
description: This repo is a one-plugin marketplace for okf-knowledge-base — an OKF v0.2 / LLM-wiki knowledge base driven by skills and a bundled MCP server — dogfooded against the kb/ bundle.
tags: [plugin, overview, marketplace]
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-03T03:53:28Z }
sources:
  - id: repo
    resource: https://github.com/CoderNumber1/kb-research
    title: kb-research repository
---

# What this repo is

`kb-research` packages an agent-operated knowledge base as a reusable
[Claude Code plugin](/claude-code/plugins-and-marketplace.md),
`okf-knowledge-base`, and dogfoods it against the example bundle in `kb/`. It
implements the [OKF v0.2](/okf/bundle-and-frontmatter.md) format and the
[LLM-wiki](/llm-wiki/pattern-and-layers.md) workflow. Behavior is defined by
the plugin's doctrine (`references/knowledge-base.md`); the OKF spec validates
it but is not shipped.

# The pieces

- [Eight skills](skills.md): kb-init, kb-init-domain, kb-ingest, kb-search,
  kb-lint, kb-consolidate, kb-capture, and the explicit-only kb-raw-audit.
- A `knowledge-curator` agent that always finishes with the kb-capture sweep.
- A [bundled MCP server](mcp-server.md) doing the deterministic work: a
  stdlib-only Python server (`server/kb_mcp.py`, needs `python3` 3.11+), with
  an equivalent C# server kept in `src/`. No built artifacts are committed.
- A [consolidation engine](consolidation-engine.md) for deduplication.

# Capture modes

`kb-init` asks each repository how knowledge capture should work and writes a
`<knowledge-base>` directive into its `CLAUDE.md`:

| Mode | Directive tells agents to | Capture happens |
|------|---------------------------|-----------------|
| Automatic | search the KB first; run kb-capture at the end of every turn | every turn that learned something |
| Explicit (agent) | search the KB first | when the user works through `knowledge-curator` |

Re-running `kb-init` switches modes by replacing the directive in place.

# Raw sources

Any `raw/` directory is a user-owned Raw Source Archive: the plugin never writes
to it, lint ignores it, and pages cite raw files through `sources`. The
`kb-raw-audit` skill migrates archives that earlier versions filled with
agent-made snapshots.

# History

Until 2026-10-27 the repo shipped [three script/scriptless variants](variants.md);
they were replaced by the single C# engine after its
[cloud feasibility](csharp-mcp-variant.md) was established.
