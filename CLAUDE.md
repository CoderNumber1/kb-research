# CLAUDE.md — Knowledge Base Operating Guide

This repository packages an agent-operated knowledge base as a reusable Claude
Code **plugin** (`plugins/okf-knowledge-base`) and dogfoods it against the
example KB in `kb/`. The plugin's skills carry the workflows; a bundled,
standard-library-only Python MCP server (`server/kb_mcp.py`) does the
deterministic work. An equivalent C# server lives in `src/`. Its behavior is defined by the
[doctrine](plugins/okf-knowledge-base/references/knowledge-base.md), which
follows the Open Knowledge Format (OKF) v0.2 (the file format) and Karpathy's
LLM-wiki pattern (the workflow). This file is the "schema" layer for this
repository: it tells any agent working here how to treat the KB.

## Core principle

Knowledge **compounds**. Do work against the distilled wiki in `kb/`, and write
durable understanding back so it never has to be re-discovered. Reading raw
sources every time is the anti-pattern this repo exists to avoid.

## Where things are

- `kb/` — the knowledge base (one OKF v0.2 bundle). Each subdirectory is a
  **domain** with `domain.md` (scope + routing description), `index.md`,
  `log.md`, and concept pages. Domains may nest **sub-domains** (e.g.
  `billing/eu`) — same shape, registered under the parent's `index.md`. Any
  `raw/` directory is a user-owned Raw Source Archive: never write to it.
- `plugins/okf-knowledge-base/` — the installable plugin:
  - `skills/` — `kb-init`, `kb-init-domain`, `kb-ingest`, `kb-search`,
    `kb-lint`, `kb-consolidate`, `kb-capture`, `kb-raw-audit`.
  - `agents/knowledge-curator.md` — KB-centered work that always ends with the
    `kb-capture` sweep.
  - `.mcp.json` + `server/` — the `knowledge-base` MCP server, launched as
    `python3 ${CLAUDE_PLUGIN_ROOT}/server/kb_mcp.py` (Python 3.11+, stdlib
    only; one module per engine under `server/kbmcp/`).
  - `references/` — the doctrine and the two `<knowledge-base>` directives
    that `kb_init` writes.
- `src/` — the equivalent C# MCP server (`KnowledgeBase.Mcp`), the xUnit
  suite (`KnowledgeBase.Mcp.Tests`) that verifies either server, and
  `publish.sh`, which builds optional C# binaries into the ignored
  `src/publish/`. Built artifacts are never committed.
- `.claude-plugin/marketplace.json` — makes this repo a one-plugin marketplace.

## How to work here

- **Answering from the KB** → use the `kb-search` skill; cite the pages you use.
- **Capturing a source or finding** → use the `kb-ingest` skill; it routes to a
  (sub-)domain by description and compiles cross-linked pages. Prefer
  extending existing pages over creating duplicates.
- **New subject area** → use `kb-init-domain` (a path slug like `billing/eu`
  makes a nested sub-domain).
- **After changes** → run `kb-lint` (scoped with `domain`) and fix ERRORs.

The MCP tools take the KB root as a required, absolute `kb_root` argument —
here, the absolute path of this repository's `kb/`.

## Changing the plugin

- Engine changes go in **both** servers — `plugins/okf-knowledge-base/server/`
  (Python, what the plugin runs) and `src/KnowledgeBase.Mcp` (C#) — with the
  same tools, arguments, results, and messages. Cover them in
  `src/KnowledgeBase.Mcp.Tests` and run the suite against each:
  `KB_MCP_SERVER=python dotnet test src/KnowledgeBase.Mcp.Tests -c Release`
  and `dotnet test src/KnowledgeBase.Mcp.Tests -c Release`.
- Parity details that are easy to break: scores round like .NET
  `Math.Round` (`net_round`), snippet windows count UTF-16 code units, and
  frontmatter must be strict YAML in both parsers.
- Check doctrine and engine changes against the OKF v0.2 specification
  (<https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>).
  The spec validates the plugin; it is not shipped with it.

## Conventions (OKF v0.2)

- Every concept page has YAML frontmatter with a non-empty `type`. Recommended:
  `title`, `description`, `tags`, and `generated: { by, at }`. Use `resource`
  only for the concrete asset a page describes.
- Provenance goes in `sources` (each entry needs `resource`), with claims
  attributed by `[^id]` footnotes. A conversation is a valid source
  (`resource: conversation on YYYY-MM-DD`), never a page's `resource`.
- Cross-link with bundle-relative markdown links: `[x](/domain/x.md)`.
- `index.md` files carry no frontmatter (except the root `kb/index.md`, which
  holds only `okf_version: "0.2"`). `log.md` uses `## YYYY-MM-DD` headings,
  newest first.

## Compounding discipline

Whenever a turn surfaces durable, reusable knowledge that the KB doesn't yet
capture, capture it before finishing (the `kb-capture` sweep). This is
mandatory when acting as the `knowledge-curator` agent and good practice
otherwise. Capture real, correct, reusable knowledge only — no ephemeral
chatter, no secrets, no fabricated detail.
