---
type: Reference
title: The LLM-wiki pattern and its three layers
description: Karpathy's pattern of compiling raw sources into a compounding, interlinked wiki, and its three layers.
tags: [llm-wiki, karpathy, compounding]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T05:54:02Z }
sources:
  - id: andrej-karpathy-llm-wiki-gist
    resource: "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"
    title: "Andrej Karpathy, \"llm-wiki\" gist"
---

# The idea

Traditional RAG re-retrieves from raw documents on **every** query, re-deriving
the same understanding repeatedly. An LLM wiki instead has the agent
**incrementally build and maintain a persistent, interlinked wiki** of markdown
pages. Knowledge is compiled *once* during ingestion and **compounds** — later
work reads the distilled pages, not the raw firehose.

# Three layers

1. **Raw sources** — immutable inputs (articles, PDFs, transcripts, data). Read,
   never edited. This repo's plugin treats any `raw/` directory as a
   user-owned Raw Source Archive that agents read and cite but never write;
   other sources are cited where they live.
2. **The wiki** — agent-generated, cross-linked concept pages derived from and
   citing the raw layer. The compounding layer.
3. **The schema** — the operating manual (here: the plugin's doctrine and
   skills, its [MCP tools](/kb-plugin/mcp-server.md), and `CLAUDE.md`) that
   defines page structure, naming, and workflow. It turns a general model into
   a disciplined knowledge worker.

OKF (see the [okf](/okf/bundle-and-frontmatter.md) domain) is the *file format*;
this pattern is the *workflow* over it. Continue with
[operations and compounding](operations-and-compounding.md).
