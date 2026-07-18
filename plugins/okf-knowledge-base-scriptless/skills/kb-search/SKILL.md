---
name: kb-search
description: >-
  Search and answer questions from the Open Knowledge Format knowledge base under
  kb/ using your built-in search and file tools — no scripts. Use whenever the
  user asks what the knowledge base, wiki, or "our notes/docs" say about
  something, wants to look up / find / recall information that may have been
  captured before, or asks a question the KB likely covers — e.g. "what does the
  KB say about webhook retries?", "search the wiki for our dunning policy", "do we
  have anything on the payments API?". Ranks pages by relevance, follows
  cross-links for context, and answers from the compiled wiki with citations.
---

# Search the Knowledge Base (scriptless)

Querying reads the *compiled* wiki — the distilled concept pages — instead of
re-deriving understanding from raw sources every time. You do the retrieval and
ranking yourself with Grep/Glob/Read; there are no helper scripts.

## 1. Retrieve candidates

- **Orient first.** Read `kb/index.md` and the relevant `kb/*/index.md` to see
  what exists (progressive disclosure). If you don't know the domains, Glob
  `kb/**/domain.md` and read their descriptions.
- **Search.** Use Grep across `kb/` for the query's key terms and their obvious
  variants/stems (e.g. `retry`, `retried`, `retries`). Search both frontmatter
  fields (`title:`, `description:`, `tags:`, `type:`) and page bodies. Exclude
  `raw/` snapshots and reserved files (`index.md`, `log.md`) unless the distilled
  pages don't answer and you need to consult the source material.
- Scope to a `--domain`-equivalent subtree (e.g. `kb/billing/`) when you already
  know the area, including nested sub-domains like `kb/billing/eu/`.

## 2. Rank and read

Judge relevance the way the scored tools would: a term appearing in a page's
**title, tags, type, or description outweighs a body mention**, and pages
covering more of the query's terms rank higher. Open the top few pages, and
follow their bundle-relative cross-links to pull in adjacent context (a page on
retries will link to the page on signatures). Follow the graph until you have
enough — don't dump every page.

## 3. Synthesize a cited answer

Answer directly, grounded in what the pages say, and **cite the pages you used**
by their KB path so the user can verify — e.g. "per
[retry policy](/billing/retry-policy.md), deliveries retry with backoff for 24h."
Distinguish what the KB states from your own inference.

## 4. Handle gaps honestly

- **No hits / thin coverage** → say so plainly and offer to ingest a source
  (`kb-ingest`) rather than inventing an answer.
- **Contradictions across pages** → surface them; they're a signal to reconcile.

## Compounding note

If, while answering, you produce a genuinely new and *durable* synthesis the KB
doesn't yet capture (not a routine restatement), that's worth writing back as a
concept page via `kb-ingest`. When operating as the `knowledge-curator` agent, the
end-of-turn workflow handles this capture automatically.
