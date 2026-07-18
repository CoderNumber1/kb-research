# CLAUDE.md — Knowledge Base Operating Guide

This repository packages an agent-operated knowledge base as a reusable Claude
Code **plugin** (`plugins/okf-knowledge-base/`) and dogfoods it against the
example KB in `kb/`. It follows the
[Open Knowledge Format v0.1](plugins/okf-knowledge-base/references/okf-spec.md)
(the file format) and Karpathy's
[LLM-wiki pattern](plugins/okf-knowledge-base/references/llm-wiki.md) (the
workflow). This file is the "schema" layer: it tells any agent working here how
to treat the KB.

## Core principle

Knowledge **compounds**. Do work against the distilled wiki in `kb/`, and write
durable understanding back so it never has to be re-discovered. Reading raw
sources every time is the anti-pattern this repo exists to avoid.

## Where things are

- `kb/` — the knowledge base (one OKF bundle). Each subdirectory is a **domain**
  with `domain.md` (scope + routing description), `index.md`, `log.md`, `raw/`
  (immutable snapshots), and concept pages. Domains may nest **sub-domains**
  (e.g. `billing/eu`) — same shape, registered under the parent's `index.md`.
- `plugins/okf-knowledge-base/` — the installable plugin:
  - `skills/` — the operations: `kb-init-domain`, `kb-ingest`, `kb-search`,
    `kb-lint`.
  - `agents/knowledge-curator.md` — the agent for sustained KB work, including
    the end-of-turn capture sweep.
  - `scripts/` — pure-stdlib helpers the skills call (`kb_common.py` holds the
    shared parser/stemmer and `find_kb_root`).
  - `hooks/hooks.json` — a `SessionStart` hook that detects a KB in the working
    directory and announces it.
  - `references/` — the OKF spec and LLM-wiki notes.
- `.claude-plugin/marketplace.json` — makes this repo a one-plugin marketplace.
- `tests/` — the pytest suite for the scripts, skills, agent, and plugin.

## How to work here

- **Answering from the KB** → use the `kb-search` skill; cite the pages you use.
- **Capturing a source or finding** → use the `kb-ingest` skill; it auto-routes to
  a (sub-)domain by description and distills into cross-linked pages. Prefer
  extending existing pages over creating duplicates.
- **New subject area** → use `kb-init-domain` (a path slug like `billing/eu`
  makes a nested sub-domain).
- **After changes** → run `kb-lint` (scoped with `--domain`) and fix ERRORs.

The scripts autodetect the KB root (the `kb/` bundle in the working directory),
so they need no `--kb-root` when run from the project.

## Conventions (OKF)

- Every concept page has YAML frontmatter with a non-empty `type`. Recommended:
  `title`, `description`, `tags`, `timestamp` (ISO 8601), and `resource` for
  concrete assets.
- Cross-link with bundle-relative markdown links: `[x](/domain/x.md)`.
- `index.md` files carry no frontmatter (except the root `kb/index.md`, which may
  hold only `okf_version`). `log.md` uses `## YYYY-MM-DD` headings, newest first.
- `raw/` snapshots are immutable — never edit a source after writing it; cite it.

## Compounding discipline

Whenever a turn surfaces durable, reusable knowledge that the KB doesn't yet
capture, ingest it before finishing. This is mandatory when acting as the
`knowledge-curator` agent (its end-of-turn workflow) and good practice otherwise.
Capture real, correct, reusable knowledge only — no ephemeral chatter, no secrets,
no fabricated detail.
