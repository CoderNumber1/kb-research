---
name: kb-consolidate
description: >-
  Analyze the Open Knowledge Format knowledge base under kb/ for duplicated and
  overlapping information, recommend consolidations that shrink the KB without
  losing knowledge, and apply only the ones the user approves. Use whenever the
  user wants to deduplicate, consolidate, merge, prune, tidy, shrink, or
  reduce/clean up the knowledge base or wiki, remove redundant/overlapping pages,
  or asks "where is this documented in more than one place?" or "can we merge
  these?". Finds within-domain duplicates first, then cross-domain duplicates
  (recommending a canonical home domain or a new shared/common domain), produces
  a numbered recommendations report, and acts only as directed.
---

# Consolidate the Knowledge Base

Over time a wiki accumulates the same knowledge in several places — twin pages in
one domain, or the same concept written up separately in two domains. This skill
finds that redundancy and consolidates it so the KB gets **smaller and faster to
search without losing any durable information**. The rule throughout: **recommend
first, act only on what the user approves**, and never lose knowledge or leave
broken links.

## 1. Analyze

Run the analyzer (deterministic candidate finder; you apply judgement next):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/kb_analyze.py" --json
```

Useful flags:
- `--min-similarity 0.5` — raise for fewer, stronger candidates (default 0.4).
- `--domain <slug>` — analyze within one (sub-)domain only.
- `--min-shared-terms`, `--max-postings`, `--limit` — tuning; defaults are fine.

It returns two lists: `within_domain` groups (all members in one domain) and
`cross_domain` groups (members spanning domains), each with the member pages, a
Jaccard similarity range, and an estimated byte saving. It analyses the compiled
pages only — `raw/` snapshots are never touched.

## 2. Judge (separate real redundancy from lookalikes)

The analyzer flags *candidates*; you decide. **Open the member pages and read
them.** Keep a group only when the pages genuinely say the same thing or overlap
heavily — the same concept, procedure, or entity. Discard a group when the pages
are merely on the same topic but cover distinct concepts (high token overlap does
not always mean duplication). Do not merge distinct concepts just to cut the page
count — one concept per page is what keeps retrieval sharp.

## 3. Recommend (write it down, then stop)

Produce a **numbered recommendations report** — save it to
`consolidation-report.md` at the project root (outside `kb/`, so it is not part of
the bundle) and summarise it in chat. For each recommendation give:

- **Scope** — within-domain or cross-domain.
- **Members** — the pages involved, and the proposed **canonical** page/home.
- **Action** — for within-domain: merge the twins into one page. For cross-domain:
  canonicalize into the best-fit existing domain **or** propose a **new common
  domain** (name + one-line description) when the concept is genuinely shared and
  belongs to neither domain more than the other; cross-link from the others.
- **Evidence** — similarity, and which facts are shared vs unique to each page.
- **Estimated saving** and any **risk** (e.g. a page carries domain-specific
  nuance that must be preserved).

Then **stop and ask the user which recommendations to apply** (all, some by
number, or none). Do not modify the KB yet.

## 4. Apply — only the approved recommendations

For each approved item, consolidate **losslessly**:

**Within-domain merge**
1. Pick the canonical page (best title/path, most complete). Fold every *unique*
   durable fact, example, and citation from the other pages into it. If pages
   conflict, reconcile — never silently drop a claim.
2. **Repoint links before deleting.** Search the whole KB for links to the pages
   being removed and update them to the canonical page:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/kb_search.py" "<removed page title>"`
   and grep for the old paths. Never leave a broken link.
3. Delete the now-redundant pages, update the domain `index.md` (or run
   `kb_lint.py --domain <d> --fix-index`) and prepend a `log.md` entry.

**Cross-domain canonicalize**
1. Choose the canonical home: the best-fit existing domain (match the concept
   against domain descriptions), or create a **new common domain** with the
   `kb-init-domain` skill if the user approved one (confirm its name/scope).
2. Put the merged, canonical page there. In each other domain, either remove the
   duplicate and repoint inbound links to the canonical page, or leave a short
   stub that cross-links to it when that domain still needs a local pointer.
3. Update every affected `index.md` and `log.md`.

Raw source snapshots under `raw/` are immutable — cite them, never edit or move
them.

## 5. Verify and report

Run `kb_lint.py` over the affected domains, fix any ERRORs and index drift
(`--fix-index`), and confirm no broken links or orphans were introduced. Then tell
the user what changed: pages merged/removed/created, links repointed, any new
common domain, and the **actual** size reduction. Delete
`consolidation-report.md` once its recommendations are resolved, or note what was
deferred.

## Guardrails

- Recommend first; apply only what the user approves.
- Lossless: preserve every unique durable fact and all provenance/citations.
- Repoint inbound links before removing a page; leave zero broken links.
- Keep one concept per page; don't over-merge to chase a smaller number.
- Never touch `raw/` snapshots.
