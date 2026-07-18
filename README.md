# kb-research

A reusable **Claude Code plugin** that turns any project into an agent-operated
knowledge base, built on the
[Open Knowledge Format (OKF) v0.1](plugins/okf-knowledge-base/references/okf-spec.md)
and run as a Karpathy-style
[LLM wiki](plugins/okf-knowledge-base/references/llm-wiki.md): knowledge is
compiled once into structured, cross-linked markdown pages so it **compounds**
over time instead of being re-discovered on every query.

The repo is a **marketplace** hosting **two variants of the plugin**, and it
dogfoods them against the example KB in `kb/`.

## The two plugins

Both give you the same four skills — `kb-init-domain`, `kb-ingest` (routes a
source to a domain by its description), `kb-search` (ranked, cited retrieval),
`kb-lint` (OKF conformance + hygiene) — plus a `knowledge-curator` agent with an
end-of-turn capture sweep and a `SessionStart` hook that detects a KB in the
working directory. They differ only in *how the work happens*:

| Plugin | How it works | Dependencies |
|--------|--------------|--------------|
| **`okf-knowledge-base`** | skills call bundled pure-stdlib Python scripts (deterministic routing/ranking/lint, autodetected KB root) | Python 3 |
| **`okf-knowledge-base-scriptless`** | skills instruct the agent to do the work directly with built-in file tools | none |

Pick the scripts variant for large KBs, CI, and reproducible output; the
scriptless variant for zero-setup use or environments without Python. **Install
one or the other, not both** — they share skill names.

## Install

```text
/plugin marketplace add CoderNumber1/kb-research
/plugin install okf-knowledge-base@kb-research              # scripts variant
# ...or:
/plugin install okf-knowledge-base-scriptless@kb-research   # scriptless variant
```

Then, in any project that has (or should have) a `kb/` bundle, ask naturally
("add this doc to the KB", "what does the wiki say about X?", "lint the KB"), or
invoke the skills directly. No `kb/` yet? Ask to initialize a domain and one is
created for you.

## Layout

```
kb-research/
├── .claude-plugin/marketplace.json     # marketplace listing both plugins
├── plugins/
│   ├── okf-knowledge-base/             # scripts variant
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/{kb-init-domain,kb-ingest,kb-search,kb-lint}/SKILL.md
│   │   ├── agents/knowledge-curator.md
│   │   ├── hooks/hooks.json            # SessionStart KB detector (kb_detect.py)
│   │   ├── scripts/                    # kb_common, init/detect/search/lint, kb_detect
│   │   └── references/{okf-spec.md,llm-wiki.md}
│   └── okf-knowledge-base-scriptless/  # scriptless variant (no scripts/)
│       ├── .claude-plugin/plugin.json
│       ├── skills/{kb-init-domain,kb-ingest,kb-search,kb-lint}/SKILL.md
│       ├── agents/knowledge-curator.md
│       ├── hooks/hooks.json            # SessionStart detector (inline shell)
│       └── references/{okf-spec.md,llm-wiki.md}
├── kb/                                 # example / dogfood KB (one OKF bundle)
│   ├── index.md                        # root catalog of domains (okf_version)
│   ├── log.md
│   └── <domain>/                       # domain.md, index.md, log.md, raw/, concepts
│       └── <sub-domain>/               # optional nesting, e.g. billing/eu
├── tests/                              # pytest suite (scripts, skills, agent, plugin)
├── docs/ci.example.yml                 # CI workflow (add under .github/workflows/)
└── CLAUDE.md                           # KB operating guide / schema layer
```

## The three operations (Karpathy) over one format (OKF)

- **Ingest** (`kb-ingest`) — add sources; the target (sub-)domain is auto-detected
  by matching the source's topic against each domain's description.
- **Query** (`kb-search`) — answer from the compiled wiki, with citations.
- **Lint** (`kb-lint`) — check conformance and hygiene (broken links, orphans,
  index drift, stale pages, …).

Plus `kb-init-domain` to open a new subject area (or a nested sub-domain).

## Running the scripts directly

Every script is pure-stdlib Python 3 and autodetects the KB in the working
directory:

```bash
S=plugins/okf-knowledge-base/scripts
python3 $S/kb_lint.py                 # health check (exit 1 on conformance errors)
python3 $S/kb_search.py "webhooks"    # search
python3 $S/detect_domain.py --list    # list domains
```

Under the installed plugin the skills call these via `${CLAUDE_PLUGIN_ROOT}`.

## Development

```bash
pip install -r requirements-dev.txt
pytest                                # 60 tests: scripts, skills, agent, plugin
```

CI: copy `docs/ci.example.yml` to `.github/workflows/ci.yml` (kept out of the repo
history because pushing workflow files needs a token with the Workflows scope).

## Design references

- Open Knowledge Format v0.1 — Google Cloud
  ([spec](plugins/okf-knowledge-base/references/okf-spec.md),
  [announcement](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/)).
- LLM Wiki — Andrej Karpathy
  ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f),
  [notes](plugins/okf-knowledge-base/references/llm-wiki.md)).
