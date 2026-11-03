---
name: kb-ingest
description: >-
  Ingest a source (document, URL, PDF, transcript, pasted notes, API docs, or
  findings from the current conversation) into the Open Knowledge Format
  knowledge base under kb/, automatically choosing the domain whose
  description fits. Use whenever the user wants to add, capture, record,
  document, save, or "remember" material in the knowledge base or wiki — e.g.
  "add this doc to the KB", "ingest this article", "document this in the
  wiki". Compiles durable knowledge into cross-linked OKF v0.2 Concept Pages
  with recorded provenance, and keeps the Raw Source Archive under the user's
  control. This is the write path of the wiki.
---

# Ingest a Source into the Knowledge Base

Ingestion acquires source material and compiles its durable meaning into
structured, cross-linked Concept Pages so future work reads the wiki instead
of re-discovering the same understanding. Read
`${CLAUDE_PLUGIN_ROOT}/references/knowledge-base.md` for the page format and
provenance rules.

The guiding principle is **compounding**: prefer updating existing pages and
adding cross-links over creating near-duplicates. A source is not processed
until its durable knowledge lives in Concept Pages.

Routing, search, and lint use the plugin's MCP tools; pass `kb_root` =
absolute path of the workspace `kb/` on every call. Page, index, and log edits
are ordinary file edits.

The Raw Source Archive is user-owned. Ingest **MUST NOT** write to it: reading
a source at its existing path is enough. An agent **MAY** copy material there
only on an express, direct user instruction, as a separate action.

## 1. Acquire the source

- **File / PDF** — read it (use the `pdf` skill for PDFs).
- **URL** — fetch it with WebFetch.
- **Conversation / notes** — use the material already in context.

Note the canonical origin — a URL, a file path, a user-placed Raw Artifact, or
`conversation on <date>` — for the page's `sources`. Report a failed read
explicitly; never substitute a guess.

## 2. Route to a domain

Distill the source to its key topic terms (title, named systems, keywords) and
call **kb_detect_domain** with `query` set to them, e.g.
`"stripe webhook signature verification hmac retry"`. It returns ranked
domains with a `confidence`:

- **high**, and it matches your reading → ingest there.
- **medium / low / ambiguous** → read the top candidates' `domain.md` scope
  (list them with `list: true`). If genuinely torn between two, ask the user.
- **no fit** → create a domain with **kb-init-domain** first.

Do not force a fit. If the best match is low-confidence, consider whether a
new domain — or a sub-domain of an existing one — would fit better, and **ask
the user to approve** creating it before you do. Recommendations may be
nested (`billing/eu`); pass the full slug. A source touching two domains goes
to its best home with a cross-link from the other, never duplicated pages.

## 3. Distill into Concept Pages — reuse the search, do not repeat it

Determine which pages the source touches before writing.

**Reuse first.** If a search covering this concept already ran this turn and
its results are in context — the **kb-search** that answered the user's
question, or an earlier item in the same capture sweep — treat those results
as the answer and go straight to writing.

**Search only when coverage is missing:** call **kb_search** with `query` set
to the key concept and `domain` set to the target domain.

For each durable concept:

- **Existing page** → update it: add facts, refine, cross-link, add `sources`
  entries, and set `generated` to your actor and now. If the page is still
  v0.1-shaped (`timestamp`, `# Citations`), migrate it while you are there. If
  the source contradicts the page, reconcile it and note the change in
  `log.md`; never leave competing claims.
- **New concept** → create `kb/<domain>/<concept-slug>.md`:

```markdown
---
type: <Reference | Playbook | Entity | Metric | ...>
title: <Concept name>
description: <one sentence>
resource: <URI of the underlying asset — omit for abstract concepts>
tags: [<tags>]
generated: { by: <producer>/<model>, at: <ISO 8601 now, with offset> }
sources:
  - id: <short-stable-id>
    resource: <URL | /path | conversation on YYYY-MM-DD>
    title: <source title>
---

# <Structural sections: Overview, Schema, Steps, Examples...>

Headings, tables, and lists over prose. Attribute claims with footnotes keyed
by source id.[^short-stable-id] Link related concepts with bundle-relative
links, e.g. [retry policy](/<domain>/retry-policy.md).

[^short-stable-id]: <source title>
```

Guidelines:

- One concept per page; the file path is its identity.
- Distill meaning and supporting facts; do not reproduce the source.
- Cross-link generously, both directions where it makes sense.
- `generated.by` is your actor (`<producer>/<model>`, e.g.
  `claude-code/claude-opus-5-5`); never write `verified` on someone's behalf.
- Cite a user-placed Raw Artifact through `sources[].resource`, never with a
  body link. A raw citation does not resolve an orphan.
- Quote YAML values that contain `: ` or ` #`.

## 4. Update the index and log

- Add new pages to `kb/<domain>/index.md` under `# Concepts`, or call
  **kb_lint** with `domain` and `fix_index: true` to regenerate the list.
- Prepend a dated entry to `kb/<domain>/log.md` (newest first):

  ```markdown
  ## 2026-07-18
  * **Ingest**: Added [signature verification](/billing/signature-verification.md)
    from the Stripe webhooks documentation.
  ```

## 5. Verify and report

Call **kb_lint** with `domain` and fix what you introduced. Surface failed
reads, writes, lint errors, and unresolved contradictions explicitly. Then
tell the user which domain received the source, which pages were created
versus updated, and any follow-ups.

## Anti-patterns

- Dumping source material into a page without distilling it.
- Creating a new page when an existing one should be extended.
- Treating a user-provided source as permission to archive a copy.
- Putting provenance in `resource`, or citations in a body `# Citations` list.
- Ingesting ephemeral chatter instead of durable, reusable knowledge.
- Fabricating detail the source does not support — leave it out or mark it open.
- Placing Concept Pages at the KB root.
