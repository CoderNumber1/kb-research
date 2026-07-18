---
name: kb-lint
description: >-
  Health-check the Open Knowledge Format knowledge base under kb/ for conformance
  and wiki hygiene by inspecting the files yourself — no scripts. Use whenever the
  user wants to lint, validate, audit, check the health of, or clean up the
  knowledge base or wiki — e.g. "lint the KB", "is the wiki healthy?", "check for
  broken links in the knowledge base", "find orphaned or stale pages". Also run it
  after ingesting sources or restructuring a domain, and as part of the
  knowledge-curator end-of-turn workflow. Reports ERRORs (OKF conformance) and
  WARNING/INFO hygiene issues, then helps fix them.
---

# Lint the Knowledge Base (scriptless)

Linting keeps the wiki trustworthy as it grows and is partly agent-generated. You
perform the checks yourself with Glob/Grep/Read — there are no helper scripts, so
work methodically and note that this is a best-effort manual pass. Separate hard
**OKF conformance** failures (ERROR) from softer **hygiene** issues the spec
tolerates but that degrade retrieval (WARNING/INFO). See
`${CLAUDE_PLUGIN_ROOT}/references/okf-spec.md` §9.

## Gather

Glob every `*.md` under the KB root (or a single domain when scoped). Split them
into **concept pages** (all non-reserved `.md`) and **reserved files**
(`index.md`, `log.md`). Read each concept page's frontmatter and body.

## Checks

**ERROR — OKF conformance (§9); must be fixed:**
- A non-reserved `.md` with no parseable YAML frontmatter block.
- Frontmatter missing a non-empty `type`.
- A non-root `index.md` that carries frontmatter (only the bundle-root
  `index.md` may, and only `okf_version`).

**WARNING — hygiene:**
- **Broken cross-links.** Collect every markdown link `[...](target)` in page
  bodies. For bundle-relative (`/…`) and relative (`./…`) targets, verify the file
  exists; flag those that don't. (Ignore external `http(s):`/`mailto:` links.)
- **Orphaned pages.** A concept page (other than `domain.md`) that no other page
  links to — usually a missing cross-link or a page absent from its `index.md`.
- **Index drift.** An `index.md` that omits concept pages sitting beside it.
- **Duplicate `title` or `resource`** across pages — often two pages to merge.
- **Non-ISO `log.md` date headings** (must be `## YYYY-MM-DD`).

**INFO:**
- Missing recommended fields (`title`, `description`, `timestamp`).
- Stale pages (a `timestamp` older than a threshold the user cares about).

## How to run it efficiently

- Use Grep to sweep quickly: e.g. find pages lacking `type:` by scanning
  frontmatter; collect link targets with a Grep for `](` and resolve each.
- Build a set of all page paths once, then check link targets and orphans against
  it, rather than re-reading files repeatedly.

## Report and fix

Present findings grouped by severity, most severe first, with the file path and a
one-line description, then a summary count and an overall "OKF-conformant" /
"NOT conformant" verdict. Then act, top-down:

1. **Fix every ERROR** — add the missing `type`/frontmatter; move stray
   frontmatter out of a non-root `index.md`.
2. **Broken links** — create the missing page, fix the path, or remove the dead
   link.
3. **Orphans** — add an inbound cross-link and list the page in its `index.md`, or
   remove it if genuinely obsolete (and log the removal).
4. **Index drift** — regenerate the `# Concepts` list from the actual pages and
   their descriptions.
5. **Duplicates / stale / missing fields** — merge, refresh, or backfill as
   warranted; these are judgement calls.

After fixing, re-run the checks to confirm a clean pass, and add a `log.md` entry
for any structural changes.
