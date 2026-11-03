# OKF Knowledge Base — Claude Code plugin

An agent-operated knowledge base on the Open Knowledge Format (OKF) v0.2, run
as a Karpathy-style LLM wiki: sources are compiled into cross-linked Concept
Pages so knowledge compounds instead of being re-derived. The plugin's
behavior is defined by its [doctrine](references/knowledge-base.md); the OKF
v0.2 specification is its validation target and is not shipped with it.

## Getting started

Run **`/kb-init`** in a repository. It asks how knowledge capture should work,
creates the `kb/` root, writes a `<knowledge-base>` directive into `CLAUDE.md`,
and walks you through the first domain.

| Capture mode | Directive tells agents to | Knowledge is captured |
|---|---|---|
| Automatic | search the KB first, and run `kb-capture` at the end of every turn | every turn that learned something |
| Explicit (agent) | search the KB first | when you work through the `knowledge-curator` agent |

Run `/kb-init` again to switch modes.

## Components

| Kind | Name | Purpose |
|------|------|---------|
| skill | `kb-init` | Bootstrap a KB in a repository and choose the capture mode. |
| skill | `kb-init-domain` | Scaffold and register a domain or nested sub-domain (e.g. `billing/eu`). |
| skill | `kb-ingest` | Route a source to a domain and compile it into OKF v0.2 Concept Pages with `sources` provenance. |
| skill | `kb-search` | Ranked, cited retrieval over the compiled wiki. |
| skill | `kb-lint` | OKF v0.2 conformance and wiki-hygiene checks (`fix_index` repair). |
| skill | `kb-consolidate` | Find duplicate/overlapping pages and merge them; recommend-then-apply. |
| skill | `kb-capture` | The end-of-turn sweep that writes durable knowledge back. |
| skill | `kb-raw-audit` | Explicit-only (`/kb-raw-audit <kb-root>`), two-phase migration of legacy raw snapshots. |
| agent | `knowledge-curator` | Does KB-centered work and always finishes with `kb-capture` (explicit capture mode). |
| MCP server | `knowledge-base` (`server/kb_mcp.py`) | The deterministic operations as tools. |

## Requirements

**Python 3.11 or newer, available as `python3` on `PATH`.** The server uses only
the standard library — nothing to install. Linux, macOS, WSL, and Claude Code
cloud sessions have `python3`; on Windows it comes from the Python install
manager, not the classic python.org installer (which provides only `python`
and `py`).

## The MCP server

`server/` holds `kb-mcp`, a standard-library-only Python server, declared in
[`.mcp.json`](.mcp.json) as `python3 ${CLAUDE_PLUGIN_ROOT}/server/kb_mcp.py`. It
is equivalent to the C# server in the repository's `src/` (same tools,
arguments, and results; the C# test suite runs against both). Tools:

| Tool | Does |
|------|------|
| `kb_search` | Ranked concept-page search with snippets (`domain`, `type`, `limit`, `include_raw`). |
| `kb_detect_domain` | Route a topic to a domain, or list domains; deprecated domains are never routed to. |
| `kb_lint` | OKF v0.2 conformance + hygiene findings (`domain`, `stale_days`, `fix_index`). |
| `kb_analyze` | Consolidation candidates, within- and cross-domain (`domain`, similarity tuning). |
| `kb_init` | Create the KB root and write/replace the capture directive (`capture_mode`). |
| `kb_init_domain` | Scaffold a domain or sub-domain. |

Every tool takes the KB root as a required, absolute `kb_root` argument, so the
server works regardless of its working directory. It is one persistent process
with a cache keyed on file modification times, so repeated calls only re-read
pages that changed.

## Knowledge base layout

```
kb/
├── index.md            # root catalog (okf_version: "0.2")
├── log.md
└── <domain>/
    ├── domain.md       # scope + routing description
    ├── index.md
    ├── log.md
    ├── <concept>.md    # distilled, cross-linked OKF v0.2 pages
    ├── raw/            # optional user-owned Raw Source Archive (never written by the plugin)
    └── <sub-domain>/   # optional nesting
```

Any `raw/` directory is a user-owned Raw Source Archive: the plugin never writes
to it, lint ignores it, and pages cite its files through `sources`.
