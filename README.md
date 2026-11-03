# kb-research

A reusable **Claude Code plugin** that turns any project into an agent-operated
knowledge base, built on the Open Knowledge Format (OKF) v0.2 and run as a
Karpathy-style LLM wiki: knowledge is compiled once into structured,
cross-linked markdown pages so it **compounds** over time instead of being
re-discovered on every query.

The repo is a single-plugin **marketplace** for `okf-knowledge-base`, and it
dogfoods the plugin against the example KB in `kb/`.

## The plugin

- **Skills:** `kb-init` (bootstrap a KB and choose the capture mode),
  `kb-init-domain`, `kb-ingest` (routes a source to a domain by its
  description), `kb-search` (ranked, cited retrieval), `kb-lint` (OKF v0.2
  conformance + hygiene), `kb-consolidate` (find and merge duplicate pages,
  recommend-then-apply), `kb-capture` (the end-of-turn sweep), and the
  explicit-only `kb-raw-audit` migration aid.
- **Agent:** `knowledge-curator`, which does KB-centered work and always
  finishes with `kb-capture`.
- **MCP server:** a standard-library-only Python server
  (`server/kb_mcp.py`, needs `python3` 3.11+) exposing `kb_search`,
  `kb_detect_domain`, `kb_lint`, `kb_analyze`, `kb_init`, and
  `kb_init_domain`. An equivalent C# server lives in `src/`; the same test
  suite verifies both, and no built artifacts are committed.

Behavior is defined by the plugin's
[doctrine](plugins/okf-knowledge-base/references/knowledge-base.md). See the
[plugin README](plugins/okf-knowledge-base/README.md) for details.

## Install

```text
/plugin marketplace add CoderNumber1/kb-research
/plugin install okf-knowledge-base@kb-research
```

Then run `/kb-init` in a project. It asks whether capture should be
**automatic** (every turn) or **explicit** (through the `knowledge-curator`
agent), creates `kb/`, writes the directive into `CLAUDE.md`, and opens the
first domain. After that, ask naturally ("add this doc to the KB", "what does
the wiki say about X?", "lint the KB").

The plugin needs Python 3.11+ as `python3` on `PATH` (present on Linux, macOS,
WSL, and Claude Code cloud sessions; on Windows, install Python with the Python
install manager).

## Layout

```
kb-research/
├── .claude-plugin/marketplace.json     # marketplace listing
├── plugins/okf-knowledge-base/
│   ├── .claude-plugin/plugin.json
│   ├── .mcp.json                       # declares python3 ${CLAUDE_PLUGIN_ROOT}/server/kb_mcp.py
│   ├── server/                         # the Python MCP server (kb_mcp.py + kbmcp/ engines)
│   ├── skills/                         # the eight skills
│   ├── agents/knowledge-curator.md
│   └── references/                     # doctrine + the two capture directives
├── src/
│   ├── KnowledgeBase.Mcp/              # the equivalent C# MCP server (net10.0)
│   ├── KnowledgeBase.Mcp.Tests/        # xUnit suite over MCP stdio; runs against either server
│   └── publish.sh                      # optional self-contained C# builds into src/publish/ (ignored)
├── kb/                                 # example / dogfood KB (one OKF v0.2 bundle)
├── docs/ci.example.yml                 # CI workflow (add under .github/workflows/)
└── CLAUDE.md                           # KB operating guide for this repo
```

## Development

Requires the .NET 10 SDK (for the test suite and the C# server) and Python 3.11+.

```bash
KB_MCP_SERVER=python dotnet test src/KnowledgeBase.Mcp.Tests -c Release   # against the plugin's Python server
dotnet test src/KnowledgeBase.Mcp.Tests -c Release                        # against the C# server
bash src/publish.sh                                                       # optional C# binaries → src/publish/
```

The test suite drives a server over MCP stdio — engine behavior, the plugin's
surface, and a lint of the committed `kb/` that fails on conformance errors.
`KB_MCP_SERVER=python` swaps the C# server for the Python one
(`KB_MCP_PYTHON` overrides the interpreter). Any engine change must land in
both servers and pass both runs.

CI: copy `docs/ci.example.yml` to `.github/workflows/ci.yml` (kept out of the
repo history because pushing workflow files needs a token with the Workflows
scope).

## Design references

- Open Knowledge Format v0.2 — Google Cloud
  ([spec](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md),
  [announcement](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/)).
  The plugin's doctrine is validated against it; the spec is not shipped.
- LLM Wiki — Andrej Karpathy
  ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)).
