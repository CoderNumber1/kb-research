---
name: kb-ingest
description: >-
  Ingest a source (document, URL, PDF, transcript, pasted notes, API docs, or
  findings from the current conversation) into the Open Knowledge Format
  knowledge base under kb/, choosing the target domain yourself by reading each
  domain's description — no scripts. Use whenever the user wants to add, capture,
  record, document, save, or "remember" material in the knowledge base or wiki —
  e.g. "add this doc to the KB", "ingest this article", "capture what we learned
  here", "document this in the wiki". Snapshots the raw source for provenance,
  then distills it into cross-linked concept pages (creating or updating them so
  knowledge compounds), and updates the domain index and log.
---

# Ingest a Source into the Knowledge Base (scriptless)

Ingestion is the write path of the wiki: snapshot raw material for provenance,
then **distill** it into structured, cross-linked pages so future work reads the
compiled knowledge instead of re-discovering it. You do every step with your file
tools — there are no helper scripts. The guiding principle is **compounding**:
extend existing pages and add cross-links rather than creating near-duplicates.

## 1. Acquire the source

Get the actual content — read a file/PDF, fetch a URL with WebFetch, or use the
material already in context. Note the canonical origin (URL, path, or
"conversation on <date>"); it becomes the `resource` and a citation.

## 2. Choose the target domain (you do the routing)

List the domains: Glob `kb/**/domain.md` and read each one's `title`,
`description`, and `tags`. Compare them against what the source is actually about
and pick the **most specific** matching (sub-)domain — semantic judgement is your
strength here, so use it.

- Clear single match → ingest there.
- Genuinely ambiguous between two → ask the user.
- Nothing fits → create a domain first with `kb-init-domain`, then continue.
  Don't force an unrelated source into an existing domain.

A source may touch two domains — put the primary knowledge in its best home and
cross-link from the other rather than duplicating.

## 3. Snapshot the raw source

Write an immutable snapshot at `kb/<domain>/raw/<source-slug>.md`:

```markdown
---
type: Source
title: <source title>
description: <one line on what it is>
resource: <original URL or path>
tags: [<domain tags>]
timestamp: <ISO 8601 now>
---

# Source

<A faithful extract or the key excerpts — enough to re-derive the concept pages.
Never edit this file after writing it; it is the provenance record.>
```

Add the source to `kb/<domain>/raw/index.md`.

## 4. Distill into concept pages — look before you write

Knowledge compounds only if you extend what exists. **First search** the domain
with Grep for the concepts the source touches (match titles/tags in frontmatter
and terms in bodies across `kb/<domain>/`). Then, for each durable concept:

- **Existing page** → update it (add facts, refine, add citations). If the source
  contradicts it, reconcile — correct the page and note it in `log.md`; never
  leave two conflicting claims.
- **New concept** → create `kb/<domain>/<concept-slug>.md`:

```markdown
---
type: <Reference | Playbook | Entity | Metric | …>
title: <Concept name>
description: <one sentence>
resource: <URI if it names a concrete asset; omit for abstract concepts>
tags: [<tags>]
timestamp: <ISO 8601 now>
---

# <Structural sections: Overview, Schema, Steps, Examples…>

Prefer headings, tables, and lists over prose — structure aids retrieval. Link
related concepts with bundle-relative markdown links, e.g.
`[retry policy](/<domain>/retry-policy.md)`.

# Citations

[1] [<source title>](/<domain>/raw/<source-slug>.md)
```

Distill *meaning*, don't copy the source (the raw snapshot holds the verbatim
material). One concept per page; the file path is its identity. Cross-link
generously.

## 5. Update index and log

Add new pages to `kb/<domain>/index.md` under `# Concepts`
(`* [<Title>](<slug>.md) - <description>`), and prepend a dated entry to
`kb/<domain>/log.md`:

```markdown
## <YYYY-MM-DD>
* **Ingest**: Added [<title>](/<domain>/<slug>.md) from
  [<source>](/<domain>/raw/<source-slug>.md).
```

## 6. Verify and report

Do a quick `kb-lint` pass (the scriptless lint skill) over the domain and fix easy
issues. Then tell the user, concisely: which (sub-)domain received it, which pages
were created vs updated, and any follow-ups (contradictions found, thin pages).

## Anti-patterns

- Dumping the raw source as a "concept page" without distilling it.
- Creating a new page when an existing one should be extended.
- Ingesting ephemeral chatter, secrets, or fabricated detail — capture durable,
  correct, reusable knowledge only.
