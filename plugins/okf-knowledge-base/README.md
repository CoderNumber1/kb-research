# OKF Knowledge Base — Claude Code plugin

An agent-operated knowledge base on the [Open Knowledge Format](references/okf-spec.md),
run as a Karpathy-style [LLM wiki](references/llm-wiki.md). Drop it into any
project: when a `kb/` bundle is present in the working directory, the plugin
detects it and the KB tools light up; when there isn't one, the plugin stays out
of the way.

## Components

| Kind | Name | Purpose |
|------|------|---------|
| skill | `kb-init-domain` | Scaffold and register a domain (or nested sub-domain, e.g. `billing/eu`). |
| skill | `kb-ingest` | Snapshot a source, auto-route it to a domain by description, distill into cross-linked pages. |
| skill | `kb-search` | Ranked, cited retrieval over the compiled wiki. |
| skill | `kb-lint` | OKF conformance + wiki-hygiene checks (`--fix-index` repair). |
| skill | `kb-consolidate` | Find duplicate/overlapping pages and merge them (within a domain, or across domains into a canonical home / new common domain); recommend-then-apply. |
| agent | `knowledge-curator` | Operates the KB; end-of-turn sweep captures durable new knowledge. |
| hook | `SessionStart` | `scripts/kb_detect.py` announces a KB found in the working directory. |

## Scripts

Pure-stdlib Python 3 in `scripts/`, invoked by the skills via
`${CLAUDE_PLUGIN_ROOT}`:

- `kb_common.py` — shared frontmatter parser, stemmer/tokenizer, and
  `find_kb_root()` (resolves the KB from `--kb-root`, `$KB_ROOT`, or the working
  directory).
- `init_domain.py`, `detect_domain.py`, `kb_search.py`, `kb_lint.py`,
  `kb_analyze.py` — the operations (analyze finds consolidation candidates).
- `kb_detect.py` — the SessionStart detector.

All of them autodetect the KB, so they run with no arguments from inside a project:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/kb_lint.py"
python3 "$CLAUDE_PLUGIN_ROOT/scripts/detect_domain.py" --list
```

## Knowledge base layout

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
