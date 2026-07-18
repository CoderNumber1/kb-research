# Karpathy's LLM Wiki — Design Notes

Source: Andrej Karpathy, "llm-wiki" gist (April 2026),
<https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>

These notes distill the pattern this knowledge base implements. They are a
companion to the formal [Open Knowledge Format spec](./okf-spec.md): OKF fixes
the *file format*; the LLM-wiki pattern describes the *workflow* an agent runs
against that format.

## The core idea

Traditional RAG re-retrieves from raw documents on **every** query, so the model
re-discovers the same understanding over and over. An LLM wiki instead has the
agent **incrementally build and maintain a persistent, interlinked wiki** of
markdown pages. Knowledge is compiled *once* during ingestion and **compounds**
over time — later work reads the distilled pages, not the raw firehose.

> The wiki is written *for the agent*, not for human browsing. Structure,
> cross-links, and provenance are what make it useful for retrieval.

## Three layers

1. **Raw sources** — Immutable inputs (articles, PDFs, transcripts, data, URLs).
   The agent reads them but never edits them. In this KB they live under
   `kb/<domain>/raw/` and are snapshotted so provenance survives even if the
   original moves or disappears.
2. **The wiki** — Agent-generated pages: entity pages (one concept each),
   concept/topic pages, summaries, and the cross-references between them. This is
   the compounding layer. Everything here is derived from — and cites back to —
   the raw layer.
3. **The schema** — The operating manual (here: the skills + the
   `knowledge-curator` agent + this repo's conventions) that defines page
   structure, naming, linking, and the ingest/query/lint workflows. It is what
   turns a general model into a disciplined knowledge worker.

## Three operations

- **Ingest** — Process new sources: snapshot the raw input, extract the durable
  facts and entities, then **create or update** wiki pages (preferring updates so
  knowledge compounds instead of duplicating), wire in cross-links and citations,
  and refresh the index and log. → `kb-ingest` skill.
- **Query** — Search the wiki, traverse via index/cross-links (progressive
  disclosure), and synthesize an answer grounded in cited pages. Genuinely new,
  durable conclusions produced while answering are worth writing back as pages.
  → `kb-search` skill.
- **Lint** — Health-check the corpus: contradictions, orphaned pages, broken or
  missing cross-references, stale claims, index drift, and OKF conformance.
  → `kb-lint` skill.

## Supporting files (see OKF §6–7)

- **`index.md`** — A catalog with one-line summaries and links, enabling an agent
  to see what exists before opening pages (progressive disclosure).
- **`log.md`** — Append-only, date-grouped history of ingests and structural
  changes, newest first, ISO `YYYY-MM-DD` headings.

## What makes a good wiki page

- One concept per page; the file path is its identity (OKF §2).
- Structural markdown (headings, tables, lists) over prose — it aids retrieval.
- Dense cross-links to related concepts; citations back to raw sources.
- Distilled, non-redundant knowledge — not a copy of the source, but what the
  source *means* for this domain.

## The compounding discipline (why the end-of-turn workflow matters)

The wiki only compounds if new understanding is actually written down. Knowledge
discovered mid-task — a fact looked up, a decision made, a source read, a
question resolved — evaporates between sessions unless captured. The
`knowledge-curator` agent therefore runs an **end-of-turn sweep**: before
finishing, it identifies durable, un-documented knowledge surfaced during the
turn and ingests it. This is the mechanism that turns one-off work into
accumulated, reusable knowledge.
