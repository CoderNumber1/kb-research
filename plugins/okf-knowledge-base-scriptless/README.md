# OKF Knowledge Base — Scriptless (Claude Code plugin)

The **scriptless** variant of [`okf-knowledge-base`](../okf-knowledge-base/). Same
Open Knowledge Format model, same Karpathy-style [LLM wiki](references/llm-wiki.md)
workflow, same four operations and curator agent — but the skills carry the logic
and do the work with your built-in file tools (Read, Grep, Glob, Write, Edit).
There are **no helper scripts and no Python dependency**.

## When to pick this one

| | `okf-knowledge-base` | `okf-knowledge-base-scriptless` (this) |
|---|---|---|
| How the work happens | skills call bundled Python scripts | skills instruct the agent to do it directly |
| Dependencies | Python 3 (stdlib only) | none |
| Domain routing | keyword-overlap scoring | the agent reads domain descriptions and reasons |
| Search ranking | deterministic scoring | the agent's judgement over Grep results |
| Lint | exhaustive, mechanical, exit codes | best-effort manual checklist |
| Best for | large KBs, CI, reproducible output | zero-setup use, environments without Python |

**Install one or the other, not both** — they share skill names
(`kb-init-domain`, `kb-ingest`, `kb-search`, `kb-lint`), so enabling both at once
collides.

## Components

- **skills/** — `kb-init-domain`, `kb-ingest`, `kb-search`, `kb-lint`,
  `kb-consolidate`, each a self-contained procedure the agent follows with file
  tools.
- **agents/knowledge-curator.md** — operates the KB with the end-of-turn capture
  sweep.
- **hooks/hooks.json** — a `SessionStart` hook (an inline shell one-liner, no
  bundled script) that announces a `kb/` bundle found in the working directory.
- **references/** — the OKF spec and LLM-wiki notes.

## Knowledge base layout

Identical to the scripts variant:

```
kb/
├── index.md            # root catalog (okf_version)
├── log.md
└── <domain>/
    ├── domain.md       # scope + routing description
    ├── index.md
    ├── log.md
    ├── raw/            # immutable source snapshots
    ├── <concept>.md    # distilled, cross-linked pages
    └── <sub-domain>/   # optional nesting
```

See the repository root for install instructions and the example KB.
