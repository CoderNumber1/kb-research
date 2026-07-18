# kb-research

An agent-operated knowledge base built on the
[Open Knowledge Format (OKF) v0.1](references/okf-spec.md) and run as a
Karpathy-style [LLM wiki](references/llm-wiki.md): knowledge is compiled once into
structured, cross-linked markdown pages so it **compounds** over time instead of
being re-discovered on every query.

## Layout

```
kb/                     # the knowledge base — one OKF bundle
├── index.md            # root catalog of domains (carries okf_version)
├── log.md              # KB-level history
└── <domain>/           # each domain is a self-contained subject area
    ├── domain.md       # scope + description used to auto-route sources
    ├── index.md        # domain catalog (progressive disclosure)
    ├── log.md          # domain history (newest first, ISO dates)
    ├── raw/            # immutable source snapshots (provenance)
    ├── <concept>.md    # distilled, cross-linked concept pages
    └── <sub-domain>/   # optional nested sub-domain (same shape, e.g. billing/eu)
        ├── domain.md   #   registered under the parent's index.md / log.md
        └── …

.claude/
├── skills/             # the operations
│   ├── kb-init-domain/ # create + register a new domain
│   ├── kb-ingest/      # snapshot a source, auto-route by domain description,
│   │                   #   distill into concept pages  (write path)
│   ├── kb-search/      # rank pages, traverse links, answer with citations (read path)
│   └── kb-lint/        # OKF conformance + wiki-hygiene health check
└── agents/
    └── knowledge-curator.md   # agent that operates the KB, with an
                               #   end-of-turn "capture what you learned" sweep

references/
├── okf-spec.md         # the OKF v0.1 specification
└── llm-wiki.md         # notes on Karpathy's LLM-wiki pattern
```

## The three operations (Karpathy) over one format (OKF)

- **Ingest** (`kb-ingest`) — add sources; the target domain is auto-detected by
  matching the source's topic against each domain's description.
- **Query** (`kb-search`) — answer from the compiled wiki, with citations.
- **Lint** (`kb-lint`) — check conformance and hygiene (broken links, orphans,
  index drift, stale pages, …).

Plus `kb-init-domain` to open a new subject area.

## Usage

In Claude Code, the skills trigger from natural requests ("add this doc to the
KB", "what does the wiki say about X?", "lint the knowledge base"), or invoke them
explicitly. For sustained knowledge work, use the **knowledge-curator** agent — it
draws on the KB and, at the end of each turn, captures durable knowledge it
discovered so the wiki keeps growing.

Every script is pure-stdlib Python 3 and runs from the repo root, e.g.:

```bash
python3 .claude/skills/kb-lint/scripts/kb_lint.py            # health check (exit 1 on conformance errors)
python3 .claude/skills/kb-search/scripts/kb_search.py "..."  # search
python3 .claude/skills/kb-ingest/scripts/detect_domain.py --list   # list domains
```

## Tests

A pytest suite exercises the scripts (against throwaway temporary knowledge
bases) and checks the skills/agent invariants and the committed bundle's
conformance:

```bash
pip install -r requirements-dev.txt
pytest
```

CI is provided as [`docs/ci.example.yml`](docs/ci.example.yml) — copy it to
`.github/workflows/ci.yml` to run the suite and lint the KB on every push/PR
(pushing a workflow file needs a token with the Workflows scope).

## Design references

- Open Knowledge Format v0.1 — Google Cloud
  ([spec](references/okf-spec.md), [announcement](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/)).
- LLM Wiki — Andrej Karpathy
  ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f),
  [notes](references/llm-wiki.md)).
