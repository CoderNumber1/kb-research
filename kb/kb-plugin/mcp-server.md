---
type: Reference
title: The kb-mcp server
description: The plugin's MCP server in two equivalent implementations — the stdlib-only Python server the plugin ships and the C# server in src/ — its six tools, the required kb_root, the page cache, the YAML model, parity rules, and how it launches.
tags: [plugin, mcp, python, dotnet, engine, tools]
resource: https://github.com/CoderNumber1/kb-research/tree/main/plugins/okf-knowledge-base/server
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-03T03:53:28Z }
sources:
  - id: python-source
    resource: https://github.com/CoderNumber1/kb-research/tree/main/plugins/okf-knowledge-base/server
    title: Python kb-mcp source
  - id: csharp-source
    resource: https://github.com/CoderNumber1/kb-research/tree/main/src/KnowledgeBase.Mcp
    title: C# KnowledgeBase.Mcp source
  - id: launch-tests
    resource: conversation on 2026-10-27
    title: Windows headless plugin launch and WSL smoke tests of the C# binaries
  - id: python-port
    resource: conversation on 2026-11-02
    title: Python port, cross-server parity diffs, and Windows launch of the Python server
---

# Two implementations, one contract

| | Python (`plugins/okf-knowledge-base/server/`) | C# (`src/KnowledgeBase.Mcp/`) |
|---|---|---|
| Shipped by the plugin | **yes** — `.mcp.json` runs `python3 ${CLAUDE_PLUGIN_ROOT}/server/kb_mcp.py` | no (optional local builds via `src/publish.sh` into the ignored `src/publish/`) |
| Runtime | Python 3.11+ as `python3`, standard library only | none for self-contained builds; .NET 10 SDK to build |
| Committed artifacts | none (source only) | none |
| YAML | hand-written parser for the frontmatter subset | YamlDotNet node model |

The Python server exists so the plugin needs no committed build artifacts; the
C# server was kept as an equivalent.[^python-port] Both expose the same tools,
argument names, JSON results, and error messages, and the one xUnit suite
verifies either (`KB_MCP_SERVER=python` switches it to Python). Parity was also
checked by diffing both servers' output over five real KBs — 205 read calls on
Windows and 123 on Linux with zero differences — and the files written by
identical init/fix-index sequences (53 files, identical).

# Tools

| Tool | Replaces | Notes |
|------|----------|-------|
| `kb_search` | `kb_search.py` | Stemmed ranking; title 6, tags 4, type/description 3, body 1 (+0.3 per repeat), scaled by query coverage. `include_raw` opts into raw Markdown. |
| `kb_detect_domain` | `detect_domain.py` | Ranks `domain.md` pages (title + tags strong, description + body weak); `high`/`medium`/`low` confidence. `status: deprecated` domains are listed but never routed to. |
| `kb_lint` | `kb_lint.py` | OKF v0.2 checks; returns `conformant` instead of an exit code. Ignores code spans and fenced blocks when checking links and footnotes. |
| `kb_analyze` | `kb_analyze.py` | See the [consolidation engine](consolidation-engine.md); `domain` scoping. |
| `kb_init` | (new) | Creates the root and writes or replaces the `<knowledge-base>` directive for the chosen capture mode. |
| `kb_init_domain` | `init_domain.py` | Scaffolds a domain with `generated` frontmatter; never touches the instructions file. |

Every tool takes **`kb_root` as a required absolute path**, replacing the
scripts' autodetection: the server's working directory is irrelevant, and the
`SessionStart` detector hook that announced a KB is gone — the directive in
`CLAUDE.md` (or the curator agent) does that job now. Tool errors return their
real message (the C# `KbException` derives from the SDK's `McpException`;
without that, the SDK replaced every message with a generic "An error occurred
invoking …").

# Engine

- One persistent process with a page cache keyed on (path, mtime, size): repeat
  calls re-parse only changed files.
- Frontmatter is parsed as **strict YAML**, so v0.2's nested `generated`,
  `verified`, and `sources` stay nested. A value containing `: ` (e.g.
  `description: Foo: bar`) is invalid YAML and a lint ERROR; the earlier
  lenient scripts accepted it, so older KBs may need such values quoted.
- Output ordering always ends in an explicit tiebreak (path), so results never
  depend on directory-walk order — the lesson from
  [the old parity work](determinism-and-parity.md).
- The directive texts are the plugin's `references/sentinel-*.md` files (the C#
  build compiles them in; the Python server reads them beside itself).

# Parity rules

Details that make the two servers agree byte-for-byte, easy to break:

- Scores round like .NET `Math.Round(x, d)` — scale, round half to even,
  unscale (`net_round`). Python's `round(x, d)` rounds the exact binary value
  and disagrees on midpoints (6.825 → 6.83 vs 6.82).
- Snippet windows count UTF-16 code units, as .NET strings do, so an emoji
  (two units) shifts the window the same way.
- Files are read with the BOM stripped and line endings preserved, and written
  as UTF-8 without a BOM — like `File.ReadAllText`/`WriteAllText`.
- YAML error *wording* differs between the parsers; which pages fail, and at
  which line, does not.

# Launch

- **Python:** verified 2026-11-02 on Windows with Claude Code 2.1.311 via a
  headless `claude -p --plugin-dir` run — `python3` (here the Python install
  manager's alias) launched the server, all six tools loaded, and a tool call
  succeeded. Linux, WSL, and cloud sessions provide `python3`; the classic
  python.org Windows installer provides only `python`/`py`, so such machines
  need the install manager.[^python-port]
- **C# (optional):** the self-contained binaries launch from an extensionless
  `.mcp.json` command (Windows resolves `kb-mcp` to `kb-mcp.exe`; Linux runs
  `kb-mcp` directly).[^launch-tests] See [cloud feasibility](csharp-mcp-variant.md).

Back to [overview](overview.md).

[^python-port]: Python port, cross-server parity diffs, and Windows launch of the Python server
[^launch-tests]: Windows headless plugin launch and WSL smoke tests of the C# binaries
