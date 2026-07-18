---
name: kb-lint
description: >-
  Health-check the Open Knowledge Format knowledge base under kb/ for conformance
  and wiki hygiene: missing/invalid frontmatter, missing `type`, broken
  cross-links, orphaned pages, index drift, missing recommended fields, non-ISO
  log dates, duplicate titles/resources, and stale pages. Use whenever the user
  wants to lint, validate, audit, check the health of, or clean up the knowledge
  base or wiki — e.g. "lint the KB", "is the wiki healthy?", "check for broken
  links in the knowledge base", "validate our OKF bundle", "find orphaned or stale
  pages". Also run it after ingesting sources or restructuring a domain to catch
  regressions, and as part of the knowledge-curator end-of-turn workflow.
---

# Lint the Knowledge Base

Linting keeps the wiki trustworthy as it grows and is partly agent-generated. It
separates hard **OKF conformance** failures from softer **wiki-hygiene** issues
that the spec tolerates but that degrade retrieval over time (per
`${CLAUDE_PLUGIN_ROOT}/references/okf-spec.md` §9 and the lint operation in `${CLAUDE_PLUGIN_ROOT}/references/llm-wiki.md`).

## Run it

```bash
pwsh -File "${CLAUDE_PLUGIN_ROOT}/scripts/kb_lint.ps1"            # whole KB
pwsh -File "${CLAUDE_PLUGIN_ROOT}/scripts/kb_lint.ps1" --domain billing
pwsh -File "${CLAUDE_PLUGIN_ROOT}/scripts/kb_lint.ps1" --json     # machine-readable
pwsh -File "${CLAUDE_PLUGIN_ROOT}/scripts/kb_lint.ps1" --stale-days 365   # flag old pages
pwsh -File "${CLAUDE_PLUGIN_ROOT}/scripts/kb_lint.ps1" --fix-index        # regenerate index.md concept lists
```

Exit code is `0` when there are no ERRORs and `1` when conformance fails — usable
in CI or a pre-commit check.

## What it checks

**ERROR — OKF v0.1 conformance (§9); must be fixed:**
- A non-reserved `.md` file with missing or unparseable YAML frontmatter.
- Frontmatter missing a non-empty `type`.
- An `index.md` carrying frontmatter (only the bundle-root `index.md` may, and
  only `okf_version`).

**WARNING — hygiene that erodes the wiki:**
- Broken cross-links (target file absent). The spec tolerates these, but the wiki
  discipline is to fix or intentionally stub them.
- Orphaned pages (nothing links to them) — usually means a missing cross-link or
  a page that should be listed in `index.md`.
- Index drift (`index.md` omits sibling concept pages).
- Duplicate `title` or `resource` across pages — often two pages that should be
  merged (compounding).
- Non-ISO `log.md` date headings.
- Unparseable `timestamp` values.

**INFO — soft signals:**
- Missing recommended fields (`title`, `description`, `timestamp`).
- Stale pages (with `--stale-days`).

## How to act on findings

Work top-down by severity:

1. **Fix every ERROR** — the bundle is non-conformant until they're gone. Add the
   missing `type`/frontmatter; move stray frontmatter out of an `index.md`.
2. **Broken links** — create the missing page (ingest the knowledge), correct the
   path, or remove the dead link if the reference was wrong.
3. **Orphans** — add an inbound cross-link from a related page and list the page
   in its `index.md`. If the page is genuinely obsolete, remove it and log it.
4. **Index drift** — run `--fix-index` to regenerate the `# Concepts` list from
   the actual pages and their descriptions (it preserves other sections).
5. **Duplicates** — merge the pages, keep one canonical path, repoint links, and
   log the merge.
6. **Stale / missing fields** — judgement calls; refresh or backfill when the page
   matters, otherwise note them.

`--fix-index` is the only automated repair; everything else is a judgement call,
so review before changing content. After fixing, re-run lint to confirm a clean
pass, and add a `log.md` entry for any structural changes you made.
