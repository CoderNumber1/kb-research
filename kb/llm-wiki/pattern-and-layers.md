---
type: Reference
title: The LLM-wiki pattern and its three layers
description: Karpathy's pattern of compiling raw sources into a compounding, interlinked wiki, and its three layers.
tags: [llm-wiki, karpathy, compounding]
timestamp: 2026-07-18T00:00:00Z
---

# The idea

Traditional RAG re-retrieves from raw documents on **every** query, re-deriving
the same understanding repeatedly. An LLM wiki instead has the agent
**incrementally build and maintain a persistent, interlinked wiki** of markdown
pages. Knowledge is compiled *once* during ingestion and **compounds** — later
work reads the distilled pages, not the raw firehose.

# Three layers

1. **Raw sources** — immutable inputs (articles, PDFs, transcripts, data). Read,
   never edited. In this repo they live under `kb/<domain>/raw/`.
2. **The wiki** — agent-generated, cross-linked concept pages derived from and
   citing the raw layer. The compounding layer.
3. **The schema** — the operating manual (here: the skills, the
   `knowledge-curator` agent, and `CLAUDE.md`) that defines page structure,
   naming, and workflow. It turns a general model into a disciplined knowledge
   worker.

OKF (see the [okf](/okf/bundle-and-frontmatter.md) domain) is the *file format*;
this pattern is the *workflow* over it. Continue with
[operations and compounding](operations-and-compounding.md).

# Citations

[1] [Andrej Karpathy, "llm-wiki" gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
