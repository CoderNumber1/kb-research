---
name: kb-capture
description: >-
  End-of-turn sweep that finds the durable knowledge that entered the context
  during the turn and writes what the knowledge base does not yet hold into
  Concept Pages. Run it at the end of every turn in a repository whose
  knowledge-base directive asks for automatic capture, and at the end of every
  knowledge-curator agent task. Also use when the user says "capture this",
  "save what we learned", or "record this in the KB".
---

# Capture Knowledge Before You Finish

This is the sweep that makes the wiki **compound**: work is done against the
distilled knowledge base, and durable understanding that surfaces along the
way is written back so it never has to be re-discovered. Read
`${CLAUDE_PLUGIN_ROOT}/references/knowledge-base.md` if the operating model is
not already clear.

## When to run

- **Automatic capture mode:** at the end of every turn in which new
  information entered your context, as the repository's `<knowledge-base>`
  directive instructs.
- **Explicit (agent) mode:** at the end of the `knowledge-curator` agent's
  work, or when the user asks for a capture.

If there is no knowledge base in the working directory (no `kb/` root),
**no-op silently**: do not announce it and do not create one. This sweep
augments the user's request; it never replaces it.

## The sweep

All tools take `kb_root` = absolute path of the workspace `kb/`.

1. **Scan the turn** for durable, reusable knowledge not yet in the knowledge
   base:
   - facts or specifics looked up, fetched, or supplied;
   - decisions and the reasoning behind them;
   - sources worth citing;
   - questions resolved, or corrections to existing knowledge;
   - new entities, systems, or relationships; and
   - novel synthesis the knowledge base does not yet state.
2. **Filter to what is worth keeping.** Keep what a future task would benefit
   from. Skip ephemeral chatter, one-off trivia, secrets, and claims that are
   not sufficiently supported. When it is unclear whether an item is durable
   or supported, ask the user rather than guessing or silently dropping it.
3. **Route and ingest.** For each kept item, follow **kb-ingest**: route with
   **kb_detect_domain**, check existing pages, and create or update Concept
   Pages. Reuse this turn's **kb_search** results where they cover the same
   concept; search again only for a new concept or domain. Record provenance
   in `sources` — a conversation is a valid scope descriptor
   (`resource: conversation on <date>`) when the knowledge originated there.

   Capture writes Concept Pages, indexes, and logs. It **MUST NOT** write
   summaries or other generated material to the Raw Source Archive.
4. **Reconcile, don't contradict.** If new knowledge conflicts with an
   existing page, correct the page, update its `generated`, and note the
   change in the domain `log.md`.
5. **Lint what you touched.** Call **kb_lint** with the affected `domain`; fix
   ERRORs and index drift (`fix_index: true`).
6. **Report the capture.** End your response with a brief list of what was
   captured and where (domain and pages created or updated). If nothing
   qualified, say so in one line.

## Guardrails

Capture only genuine, correct, reusable knowledge; cite sources; never
fabricate detail; keep secrets out of the knowledge base.
