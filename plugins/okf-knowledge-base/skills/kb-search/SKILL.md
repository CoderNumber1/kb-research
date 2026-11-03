---
name: kb-search
description: >-
  Search and answer questions from the Open Knowledge Format knowledge base under
  kb/, retrieving relevant concept pages and synthesizing a cited answer. Use
  whenever the user asks what the knowledge base, wiki, or "our notes/docs" say
  about something, wants to look up / find / recall information that may have been
  captured before, or asks a question that the KB likely covers — e.g. "what does
  the KB say about webhook retries?", "search the wiki for our dunning policy",
  "do we have anything on the payments API?". Prefer this over ad-hoc grep: it
  ranks pages by relevance across domains, follows cross-links for context, and
  answers from compiled knowledge rather than raw sources. This is the read path
  of the wiki.
---

# Search the Knowledge Base

Querying reads the *compiled* wiki — the distilled Concept Pages — instead of
re-deriving understanding from raw sources every time. The job is to retrieve
the right pages, traverse their cross-links for context, and synthesize a
grounded, **cited** answer. Read
`${CLAUDE_PLUGIN_ROOT}/references/knowledge-base.md` for the governing model if
needed. Pass `kb_root` = absolute path of the workspace `kb/` on every call.

## 1. Retrieve

Call **kb_search** with `query` (the natural-language question). It stems word
families and weights title, tags, type, and description above body text.
Optional arguments:

- `domain` — scope to one (sub-)domain slug when you know the area.
- `type` — restrict to a frontmatter type (e.g. `Playbook`).
- `limit` — more or fewer hits (default 10).
- `include_raw: true` — also search Markdown Raw Artifacts under `raw/` when
  the distilled pages do not answer. Off by default; non-Markdown files are
  never included.

If you don't know which domains exist, call **kb_detect_domain** with
`list: true`.

## 2. Read and traverse (progressive disclosure)

Open the top-ranked pages. Use `index.md` files and the cross-links inside
pages to pull in adjacent context — a page on retries links to the page on
signatures. Follow links until you have enough to answer; follow the graph,
don't dump every page. Note each page's `status` (`draft` is incomplete,
`deprecated` is historical) and whether it is past its `stale_after`.

## 3. Fall back when the knowledge base does not answer

If the hits are absent, weak, or don't address the question, continue with
the codebase, external sources, and your own reasoning.

## 4. Synthesize a cited answer

Answer directly, grounded in what the pages say. **Cite the pages you used** by
their KB path, e.g. "per [retry policy](/billing/retry-policy.md), deliveries
retry with exponential backoff for 24h." Distinguish what the KB states from
your own inference, and say where an answer came from outside the KB.

## 5. Handle gaps honestly

- **No hits or thin coverage** → this is not a "no" or "not supported". Fall
  back (step 3).
- **A page explicitly records that something is unsupported or was decided
  against** → that is a legitimate negative answer; cite it.
- **After exhausting all sources** → if the answer is genuinely unknown, say
  "I don't know" plainly. Never invent a negative to fill the gap.
- **Contradictions across pages** → surface them; they need reconciling (a
  follow-up ingest).

## Compounding note

A genuinely new and durable synthesis the KB doesn't yet capture is worth
writing back through **kb-ingest** — but only knowledge worth reusing, not
routine lookups. In automatic capture mode the end-of-turn **kb-capture**
sweep handles this; in explicit mode, the **knowledge-curator** agent does.
