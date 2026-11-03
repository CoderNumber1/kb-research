---
name: kb-lint
description: >-
  Health-check the Open Knowledge Format knowledge base under kb/ for OKF v0.2
  conformance and wiki hygiene: missing/invalid frontmatter, missing `type`,
  malformed provenance/trust/lifecycle fields, broken links and source paths,
  orphaned pages, index drift, duplicate titles/resources, stale pages, and
  legacy v0.1 shapes. Use whenever the user wants to lint, validate, audit,
  check the health of, or clean up the knowledge base or wiki — e.g. "lint the
  KB", "is the wiki healthy?", "find orphaned or stale pages". Also run it after
  ingesting or restructuring a domain, and as part of every capture.
---

# Lint the Knowledge Base

Linting keeps the wiki trustworthy as it grows and is partly agent-generated.
It separates hard **conformance** failures from softer **hygiene** issues
that degrade retrieval over time. Read
`${CLAUDE_PLUGIN_ROOT}/references/knowledge-base.md` for the page format and
the rules behind each finding.

## Run it

Call **kb_lint** with `kb_root` = absolute path of the workspace `kb/`.

- `domain: "billing"` → scope to one (sub-)domain.
- `stale_days: 365` → also flag pages whose `generated.at` (or legacy
  `timestamp`) is older than N days. `stale_after` is always checked.
- `fix_index: true` → regenerate the `# Concepts` lists in `index.md` files.

It returns JSON with `summary`, `conformant`, and `findings` (each with
`level`, `code`, `path`, `msg`). `conformant: false` means ERROR findings
exist; that is a valid result, not a tool failure.

## What it checks

**ERROR — conformance; must be fixed** (`frontmatter`, `type`,
`index-frontmatter`):
- A non-reserved `.md` file without parseable YAML frontmatter.
- Frontmatter without a non-empty `type`.
- An `index.md` with frontmatter (only the bundle-root `index.md` may, and
  only `okf_version`).

**WARNING — hygiene:**
- `status` not `draft`, `stable`, or `deprecated`.
- `generated` without `by`; `verified` entries without `by`/`at`; `sources`
  that are not a list of entries with `resource`, or that repeat an `id`.
- `datetime`: a v0.2 datetime without an explicit UTC offset.
- `footnote`: a `[^label]` with no matching `sources` id.
- `broken-link` / `broken-source`: a link or source path whose target is
  missing.
- `raw-link`: a body link into the Raw Source Archive (cite it from `sources`).
- `orphan`: no other Concept Page links here (links from `domain.md`, indexes,
  logs, and raw files don't count; a `sources` lineage edge does).
- `index-drift`, `dup-title`, `dup-resource`, `log-date`, `timestamp`.

**INFO — soft signals:** missing recommended fields (`title`, `description`,
`generated`), `stale` pages, `legacy` v0.1 shapes (`timestamp`,
`# Citations`), and an `okf-version` other than 0.2.

The Raw Source Archive is never linted, and a domain with no pages is valid.

## How to act on findings

Work top-down by severity:

1. **Fix every ERROR** — add the missing frontmatter or `type`; quote YAML
   values containing `: ` or ` #`; move stray frontmatter out of an
   `index.md`.
2. **Malformed v0.2 fields** — correct them against the page format in the
   doctrine. Never invent `verified` events.
3. **Broken links and sources** — create the missing page (ingest the
   knowledge), correct the path, or remove a wrong reference.
4. **Raw links** — replace the body link with a `sources` entry pointing at the
   raw file.
5. **Orphans** — add an inbound link from a genuinely related Concept Page. If
   none exists, leave the finding: it is accurate. Never add a link from
   `domain.md`, an index, or a log just to clear it. Remove a page only if it is
   obsolete, and log the removal.
6. **Index drift** — call **kb_lint** with `fix_index: true`; it rewrites only
   the `# Concepts` section.
7. **Duplicates** — merge the pages (see **kb-consolidate**), keep one
   canonical path, repoint links, and log the merge.
8. **Legacy, stale, and missing fields** — migrate legacy pages when you next
   edit them (move `timestamp` to `generated.at`, and `# Citations` to
   `sources` with footnotes; a provenance URL found in `resource` moves to
   `sources`, never deleted). Refresh stale pages that matter.

`fix_index` is the only automated repair; everything else is a judgement
call, so review before changing content. Re-run **kb_lint** to confirm, and add
a `log.md` entry for structural changes.
