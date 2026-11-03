---
type: Reference
title: C# MCP engine — cloud feasibility
description: The evidence that a self-contained C# MCP server can serve as the plugin's engine in Claude Code cloud sessions, the build trade-offs measured, and what remains unverified.
tags: [plugin, mcp, dotnet, cloud, feasibility]
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-03T03:53:28Z }
sources:
  - id: cloud-probe
    resource: "https://github.com/CoderNumber1/kb-research/blob/e3777aea493ba0f8fd6e1bff9677333be4ef8609/docs/cloud-mcp-probe-results.md"
    title: Cloud MCP probe results
  - id: plugin-probe
    resource: "https://github.com/CoderNumber1/kb-research/blob/db0bc3d678add905927d88617f9c08d2eb7175ab/docs/cloud-mcp-plugin-probe-results.md"
    title: Cloud MCP plugin probe results
  - id: wsl-tests
    resource: conversation on 2026-10-26
    title: Local WSL builds and smoke tests of the bag-o-squirrels C# server
---

# Status

Adopted on 2026-10-27 as the plugin's only engine, then on 2026-11-02 kept as
an equivalent alternative: the plugin now ships a stdlib-only Python port so no
built artifacts need committing — see [the kb-mcp server](mcp-server.md) and
the [variant history](variants.md). The C# server started from the one in the
`bag-o-squirrels` repo's `plugins/knowledge-base` (which targets Copilot CLI and
its `"type": "local"` `.mcp.json` format). This page keeps the feasibility
evidence; most of it (cloud plugin `.mcp.json` launch, exec bits, the sync
question) applies to any MCP engine.

# Build options (linux-x64, measured on Ubuntu 24.04 under WSL)

| Publish flags | Size | Cold `initialize` | Notes |
|---------------|------|-------------------|-------|
| `--self-contained -p:PublishSingleFile=true` | 76.9 MB | ~330 ms | no code changes |
| `+ -p:PublishTrimmed=true` | 18.7 MB | ~565 ms | trimming drops the framework's ReadyToRun code → more JIT |
| **`+ -p:PublishTrimmed=true -p:PublishReadyToRun=true`** | **~33 MB** | **~115 ms** | chosen |

- Runtime deps: glibc + libstdc++ only; `InvariantGlobalization=true` removes ICU.[^wsl-tests]
- Trim warnings came only from the server's own generic `JsonArray.Add<T>`
  calls; casting to `JsonNode` removed them. YamlDotNet's node model trims
  cleanly.
- Cross-publishing linux-x64 from Windows works for single-file, trimmed, and
  ReadyToRun builds; Native AOT cannot cross-compile from Windows to Linux.
- Peak RSS ~56 MB during a smoke test of all tools.

# What is known (cloud)

From two probes in a cloud session (see
[plugins and MCP in cloud sessions](/claude-code/cloud-sessions.md) and
[the sandbox VM](/dev-environment/sandbox-vm.md)):

- The VM is x86_64 Ubuntu 24.04, glibc 2.39 — the WSL-built `linux-x64`
  binary's environment exactly. A same-stack minimal MCP server answered
  `initialize` in 102–154 ms with no SDK on `PATH`.[^cloud-probe]
- The exec bit survives the clone **and** the plugin-cache install (modes
  mirror git); nothing is mounted `noexec`.
- A plugin `.mcp.json` launching `${CLAUDE_PLUGIN_ROOT}/bin/<binary>` connects
  and serves tools when the plugin is loaded via `--plugin-dir`.[^plugin-probe]
- Building at session start is also viable: `dot.net`,
  `builds.dotnet.microsoft.com`, and `api.nuget.org` are reachable; SDK install
  + restore + publish took ~30 s.

# What is not known

- **Whether a plugin delivered by the account sync gets its `.mcp.json`
  servers started by the session host.** Only `--plugin-dir` loading was
  tested. This is the main residual risk for cloud sessions whichever engine
  ships; check for `mcp__plugin_okf-knowledge-base_*` tools in the first cloud
  session after the plugin reaches `main`.
- Whether GitHub release downloads work through the egress proxy (bare
  `github.com` returned 400) — relevant only if C# binaries were ever
  distributed as release assets.
- Other cloud environment types, arm64 hosts, and macOS.

# Distribution, if the C# server were shipped

- Cloud sessions run the plugin from the marketplace's **default branch**, so
  the binaries would have to be committed to `main` (~33 MB per platform; each
  installed plugin version keeps its own copy) — the cost that led to shipping
  the Python port instead.
- One extensionless `.mcp.json` command serves both platforms: Windows resolves
  `kb-mcp` to `kb-mcp.exe` (verified), Linux runs `kb-mcp` directly — no
  launcher needed.
- The Linux binary would need committing as mode `100755`.
