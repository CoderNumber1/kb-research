---
okf_version: "0.1"
---

# Knowledge Base

This is the root of an [Open Knowledge Format](../plugins/okf-knowledge-base/references/okf-spec.md)
bundle, operated as a Karpathy-style
[LLM wiki](../plugins/okf-knowledge-base/references/llm-wiki.md). Each
subdirectory below is a **domain** — a self-contained area of knowledge with its
own sources, concept pages, index, and log.

To work in this knowledge base, use the `kb-init-domain`, `kb-ingest`,
`kb-search`, and `kb-lint` skills, or the `knowledge-curator` agent.

# Domains
* [Open Knowledge Format](okf/index.md) - The Open Knowledge Format v0.1 specification — knowledge bundles, concepts, YAML frontmatter, reserved files, cross-linking, and conformance.
* [LLM Wiki Pattern](llm-wiki/index.md) - Karpathy's LLM-wiki pattern — compiling raw sources into a compounding interlinked markdown wiki with ingest, query, and lint operations.
* [KB Plugin Architecture](kb-plugin/index.md) - Architecture of the okf-knowledge-base Claude Code plugins in this repo — the Python, PowerShell, and scriptless variants, their five skills, scripts, KB autodetection, nested sub-domains, and consolidation engine.
* [Claude Code Platform](claude-code/index.md) - Claude Code plugin platform — plugin.json and marketplace.json manifests, component auto-discovery, hooks, CLAUDE_PLUGIN_ROOT, and plugin install scopes.
* [Dev Environment](dev-environment/index.md) - Operational knowledge for the Claude Code remote execution sandbox — the egress and git proxy, pushing via a personal access token, reserved environment variables, and installing tools like PowerShell.

