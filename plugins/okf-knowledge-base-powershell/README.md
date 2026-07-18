# OKF Knowledge Base — PowerShell (Claude Code plugin)

The **PowerShell edition** of [`okf-knowledge-base`](../okf-knowledge-base/). Same
Open Knowledge Format model, same Karpathy-style [LLM wiki](references/llm-wiki.md)
workflow, same four operations and curator agent — but the bundled scripts are
PowerShell (`.ps1`) instead of Python. Behaviour and JSON output are **identical**
to the Python variant (verified by a parity check in the test suite), so you can
pick whichever runtime your environment already has.

## Requirements

- **PowerShell 7+** (`pwsh`) on `PATH`. Install: <https://learn.microsoft.com/powershell/scripting/install/installing-powershell>.

## Components

- **skills/** — `kb-init-domain`, `kb-ingest`, `kb-search`, `kb-lint`; each calls
  a bundled `pwsh` script via `${CLAUDE_PLUGIN_ROOT}/scripts/*.ps1`.
- **agents/knowledge-curator.md** — operates the KB with the end-of-turn capture
  sweep.
- **hooks/hooks.json** — a `SessionStart` hook running `scripts/kb_detect.ps1`,
  which announces a KB found in the working directory.
- **scripts/** — `KbCommon.psm1` (shared module: frontmatter parser, stemmer,
  `Find-KbRoot`) plus `init_domain.ps1`, `detect_domain.ps1`, `kb_search.ps1`,
  `kb_lint.ps1`, `kb_detect.ps1`.
- **references/** — the OKF spec and LLM-wiki notes.

The scripts share the Python variant's CLI exactly (`--kb-root`, `--query`,
`--json`, `--domain`, `--fix-index`, …), so they run with no arguments from inside
a project:

```powershell
pwsh -File "$env:CLAUDE_PLUGIN_ROOT/scripts/kb_lint.ps1"
pwsh -File "$env:CLAUDE_PLUGIN_ROOT/scripts/detect_domain.ps1" --list
```

## Which variant?

| | `okf-knowledge-base` | `okf-knowledge-base-powershell` (this) | `okf-knowledge-base-scriptless` |
|---|---|---|---|
| Engine | Python 3 scripts | PowerShell 7 scripts | none (agent + file tools) |
| Output | deterministic | deterministic (identical to Python) | agent judgement |
| Needs | Python | pwsh | nothing |

**Install exactly one** okf-knowledge-base variant — they share skill names.

See the repository root for install instructions, the example KB, and the
cross-variant benchmarks under `benchmarks/`.
