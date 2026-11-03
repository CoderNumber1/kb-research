# KB Plugin Architecture — Update Log

## 2026-11-03
* **Update**: Recorded the stdlib-only Python port of the MCP server, which the plugin now ships instead of committed C# binaries — rewrote [the kb-mcp server](mcp-server.md) (two implementations, parity rules, launch); updated [overview](overview.md), [variants](variants.md), and [C# engine feasibility](csharp-mcp-variant.md).

## 2026-10-27
* **Update**: Recorded the move to a single C# MCP engine — rewrote [overview](overview.md), [skills](skills.md) (now eight), [consolidation engine](consolidation-engine.md), [variants](variants.md) (now history), and [C# engine feasibility](csharp-mcp-variant.md); added [the kb-mcp server](mcp-server.md), which supersedes the removed scripts-and-autodetection page; marked [determinism and parity](determinism-and-parity.md) `deprecated`.
* **Migration**: Moved pages to OKF v0.2 frontmatter; the raw probe snapshots are no longer cited (pending a `kb-raw-audit` decision).

## 2026-10-26
* **Ingest**: Added [C# MCP server variant — cloud feasibility](csharp-mcp-variant.md) from WSL builds and two cloud probes ([probe](raw/cloud-mcp-probe-results.md), [plugin probe](raw/cloud-mcp-plugin-probe-results.md)); linked it from [variants](variants.md).

## 2026-07-18
* **Ingest**: Documented the plugin build — [overview](overview.md), [variants](variants.md), [skills](skills.md), [scripts & autodetection](scripts-and-autodetection.md), [consolidation engine](consolidation-engine.md), [determinism & parity](determinism-and-parity.md).
* **Initialization**: Created the KB Plugin Architecture domain.
