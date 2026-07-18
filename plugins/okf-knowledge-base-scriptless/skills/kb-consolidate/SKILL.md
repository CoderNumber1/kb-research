---
name: kb-consolidate
description: >-
  Analyze the Open Knowledge Format knowledge base under kb/ for duplicated and
  overlapping information, recommend consolidations that shrink the KB without
  losing knowledge, and apply only the ones the user approves — using your
  built-in file tools, no scripts. Use whenever the user wants to deduplicate,
  consolidate, merge, prune, tidy, shrink, or reduce/clean up the knowledge base
  or wiki, remove redundant/overlapping pages, or asks "where is this documented
  in more than one place?" or "can we merge these?". Finds within-domain
  duplicates first, then cross-domain duplicates (recommending a canonical home
  domain or a new shared/common domain), produces a numbered recommendations
  report, and acts only as directed.
---

# Consolidate the Knowledge Base (scriptless)

Over time a wiki accumulates the same knowledge in several places — twin pages in
one domain, or the same concept written up separately in two domains. This skill
finds that redundancy and consolidates it so the KB gets **smaller and faster to
search without losing any durable information**. You do the analysis yourself with
Grep/Glob/Read — there are no scripts. The rule throughout: **recommend first, act
only on what the user approves**, and never lose knowledge or leave broken links.

## 1. Analyze (you find the overlaps)

Survey the pages and look for redundancy, **within each domain first, then across
domains**:

- **Inventory.** Glob `kb/**/*.md` (skip `index.md`, `log.md`, `domain.md`, and
  `raw/`). Read each page's `title`, `description`, and `tags`.
- **Within a domain.** Group the domain's pages and flag pairs whose titles or
  descriptions clearly restate each other, or that share tags — then read those
  bodies to confirm heavy overlap. For larger domains, Grep for distinctive terms
  (a specific entity, error code, or procedure name) to find pages covering the
  same thing under different titles.
- **Across domains.** Look for the same concept, procedure, or entity documented
  in more than one domain (e.g. a "refunds" write-up in both `billing` and
  `support`). Grep the whole KB for distinctive terms and compare the hits.

Judge overlap by meaning, not just shared words — two pages on the same topic can
still be distinct concepts.

## 2. Judge

Keep a group only when the pages genuinely say the same thing or overlap heavily.
Discard lookalikes that cover distinct concepts. Do not merge distinct concepts
just to cut the page count — one concept per page keeps retrieval sharp.

## 3. Recommend (write it down, then stop)

Produce a **numbered recommendations report** — save it to
`consolidation-report.md` at the project root (outside `kb/`) and summarise it in
chat. For each recommendation give:

- **Scope** — within-domain or cross-domain.
- **Members** — the pages involved, and the proposed **canonical** page/home.
- **Action** — within-domain: merge the twins into one page. Cross-domain:
  canonicalize into the best-fit existing domain **or** propose a **new common
  domain** (name + one-line description) when the concept belongs to neither more
  than the other; cross-link from the others.
- **Evidence** — which facts are shared vs unique to each page.
- **Estimated saving** and any **risk** (domain-specific nuance to preserve).

Then **stop and ask which recommendations to apply** (all, some by number, or
none). Do not modify the KB yet.

## 4. Apply — only the approved recommendations

Consolidate **losslessly**:

**Within-domain merge** — pick the canonical page, fold every unique durable fact,
example, and citation from the others into it (reconcile conflicts, never drop a
claim), repoint every inbound link to the canonical page (Grep the KB for the old
paths **before** deleting), delete the redundant pages, and update the domain
`index.md` and `log.md`.

**Cross-domain canonicalize** — choose the canonical home (best-fit existing
domain, or a new common domain via the `kb-init-domain` skill if approved), put
the merged page there, and in each other domain either remove the duplicate and
repoint inbound links or leave a short stub that cross-links to the canonical
page. Update every affected `index.md` and `log.md`.

Raw source snapshots under `raw/` are immutable — cite them, never edit or move
them.

## 5. Verify and report

Run the `kb-lint` skill over the affected domains; fix any ERRORs and index drift,
and confirm no broken links or orphans were introduced. Tell the user what
changed — pages merged/removed/created, links repointed, any new common domain,
and the actual size reduction. Resolve or note `consolidation-report.md`.

## Guardrails

- Recommend first; apply only what the user approves.
- Lossless: preserve every unique durable fact and all provenance/citations.
- Repoint inbound links before removing a page; leave zero broken links.
- Keep one concept per page; don't over-merge to chase a smaller number.
- Never touch `raw/` snapshots.
