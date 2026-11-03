# KB Plugin Architecture

Architecture of the okf-knowledge-base Claude Code plugin in this repo — its eight skills, capture modes, the bundled C# kb-mcp server and its tools, the consolidation engine, and the history of the retired script variants.

See [domain.md](domain.md) for scope and conventions.

# Concepts

* [The consolidation engine](consolidation-engine.md) - How the kb_analyze tool finds duplicate/overlapping pages and how kb-consolidate merges them, recommend-then-apply.
* [C# MCP engine — cloud feasibility](csharp-mcp-variant.md) - The evidence that a self-contained C# MCP server can serve as the plugin's engine in Claude Code cloud sessions, the build trade-offs measured, and what remains unverified.
* [Determinism and Python/PowerShell parity](determinism-and-parity.md) - Historical — the techniques used to make the retired PowerShell scripts emit byte-identical JSON to the retired Python scripts, and the determinism lesson that still applies.
* [The kb-mcp server](mcp-server.md) - The plugin's MCP server in two equivalent implementations — the stdlib-only Python server the plugin ships and the C# server in src/ — its six tools, the required kb_root, the page cache, the YAML model, parity rules, and how it launches.
* [KB plugin — overview](overview.md) - This repo is a one-plugin marketplace for okf-knowledge-base — an OKF v0.2 / LLM-wiki knowledge base driven by skills and a bundled MCP server — dogfooded against the kb/ bundle.
* [The eight skills](skills.md) - kb-init, kb-init-domain, kb-ingest, kb-search, kb-lint, kb-consolidate, kb-capture, and kb-raw-audit — what each operation does and which MCP tools it calls.
* [Plugin engine variants (history)](variants.md) - The Python, PowerShell, and scriptless variants the plugin shipped until 2026-10-27, what the benchmarks showed, and why a single C# MCP engine replaced them.
