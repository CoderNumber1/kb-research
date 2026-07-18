---
name: kb-search
description: >-
  Search and answer questions from the Open Knowledge Format knowledge base under
  kb/, retrieving relevant concept pages and synthesizing a cited answer. Use
  whenever the user asks what the knowledge base, wiki, or "our notes/docs" say
  about something, wants to look up / find / recall information that may have been
  captured before, or asks a question that the KB likely covers — e.g. "what does
  the KB say about webhook retries?", "search the wiki for our dunning policy",
  "do we have anything on the payments API?", "look up how signature verification
  works". Prefer this over ad-hoc grep: it ranks pages by relevance across
  domains, follows cross-links for context, and answers from compiled knowledge
  rather than raw sources. This is the read path of the wiki.
---

# Search the Knowledge Base

Querying reads the *compiled* wiki — the distilled concept pages — instead of
re-deriving understanding from raw sources every time. The job is to retrieve the
right pages, traverse their cross-links for context, and synthesize a grounded,
**cited** answer. Read `${CLAUDE_PLUGIN_ROOT}/references/llm-wiki.md` for the model if needed.

## Workflow

### 1. Retrieve

Run the ranked search (stems word families, weights title/tags/type/description
above body text):

```bash
pwsh -File "${CLAUDE_PLUGIN_ROOT}/scripts/kb_search.ps1" "how are failed deliveries retried" --json
```

Useful flags:
- `--domain <slug>` — scope to one domain when you already know the area.
- `--type <Type>` — restrict to a frontmatter type (e.g. `Playbook`).
- `--limit N` — more/fewer hits (default 10).
- `--include-raw` — also search `raw/` snapshots (off by default; use when the
  distilled pages don't answer and you need to check the source material).

If you don't know which domains exist, list them first:
`pwsh -File "${CLAUDE_PLUGIN_ROOT}/scripts/detect_domain.ps1" --list`.

### 2. Read and traverse (progressive disclosure)

Open the top-ranked pages. Use `index.md` files and the bundle-relative
cross-links inside pages to pull in adjacent context — a page on retries will
link to the page on signatures, etc. Follow links until you have enough to answer;
don't dump every page, follow the graph.

### 3. Synthesize a cited answer

Answer the question directly, grounded in what the pages say. **Cite the pages you
used** by their KB path so the user can verify, e.g. "per
[retry policy](/billing/retry-policy.md), deliveries retry with exponential
backoff for 24h." Distinguish what the KB actually states from your own inference.

### 4. Handle gaps honestly

- **No hits / thin coverage** → say so plainly. Offer to ingest a source
  (`kb-ingest`) to fill the gap rather than inventing an answer.
- **Contradictions across pages** → surface them; they're a signal to reconcile
  (a `kb-lint` job or a follow-up ingest).

## Compounding note

If, while answering, you produce a genuinely new and *durable* synthesis that the
KB doesn't yet capture (not a one-off restatement), that's worth writing back as a
concept page via `kb-ingest`. This is how query results compound into the wiki
over time — but only for knowledge worth reusing, not routine lookups. When
operating as the `knowledge-curator` agent, the end-of-turn workflow handles this
capture automatically.
