---
type: Reference
title: Plugins and MCP servers in cloud sessions
description: How Claude Code cloud sessions acquire plugins and which MCP server declarations they start — observed by probe, with the open questions.
tags: [claude-code, cloud, plugins, mcp, marketplace]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T05:54:02Z }
sources:
  - id: cloud-mcp-plugin-probe-results
    resource: "https://github.com/CoderNumber1/kb-research/blob/db0bc3d678add905927d88617f9c08d2eb7175ab/docs/cloud-mcp-plugin-probe-results.md"
    title: Cloud MCP plugin probe results
  - id: cloud-mcp-probe-results
    resource: "https://github.com/CoderNumber1/kb-research/blob/e3777aea493ba0f8fd6e1bff9677333be4ef8609/docs/cloud-mcp-probe-results.md"
    title: Cloud MCP probe results
---

# Scope

Observed behavior of Claude Code **cloud sessions** (Claude Code 2.1.311,
environment type `cloud_default`, 2026-10-27), established by two probes run
in the session. The VM itself is described in
[the sandbox VM](/dev-environment/sandbox-vm.md). These are observations, not
documented guarantees — re-probe after major Claude Code releases.

# How plugins arrive

| Mechanism | Works in cloud? | Notes |
|-----------|-----------------|-------|
| Account plugin sync (`CLAUDE_CODE_SYNC_PLUGINS=1`) | **yes** | Plugins enabled at user scope are installed into `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` at startup. |
| Project `.claude/settings.json` `extraKnownMarketplaces` (directory source) + `enabledPlugins` | **no** | Neither the session host nor a headless child installed it. |
| `--plugin-dir <path>` on a child `claude` | yes | Useful for testing; not how a session gets plugins. |

The synced copy is a **pinned commit of the marketplace repo's default branch**,
not the session's checkout — a session started on a feature branch still runs
the plugin from `main` (consistent with
[marketplace install resolving to the default branch](plugins-and-marketplace.md)).
So a plugin change reaches cloud sessions only once it is on the default branch.

File modes in the plugin cache **mirror git**: files committed `100755` are
executable, `100644` files are not. A shipped binary or directly-executed script
must be committed with the exec bit (`git update-index --chmod=+x` from Windows).

Plugin skills, agents, and `SessionStart` [hooks](hooks-and-scopes.md) from a
synced plugin all load.

# Which MCP declarations start

| Declaration | Started? | Evidence |
|-------------|----------|----------|
| Project `.mcp.json` at the repo root | **yes, at session start, no approval** | Server spawned by the host; its tool was callable. `claude mcp list` nonetheless shows "Pending approval" — misleading in cloud. Runs with cwd = repo root and **no** `CLAUDE_PLUGIN_ROOT`, so paths must be repo-relative. |
| Plugin `.mcp.json` (plugin loaded via `--plugin-dir`) | **yes** | Both `python3 ${CLAUDE_PLUGIN_ROOT}/server.py` and a direct-exec `${CLAUDE_PLUGIN_ROOT}/server.py` connected; `CLAUDE_PLUGIN_ROOT` was set. A self-contained .NET binary at `${CLAUDE_PLUGIN_ROOT}/bin/...` also connected. Plugin tools are named `mcp__plugin_<plugin>_<server>__<tool>`. |
| Plugin `.mcp.json` in a plugin **delivered by account sync** | **unknown** | Not yet tested — see below. |

Because the host runs a project `.mcp.json` without prompting, any repository
opened in a cloud session executes its declared MCP commands at startup
(contained by the VM sandbox). Keep probe-only `.mcp.json` files off `main`.

# Open question

Does the session host start MCP servers from a plugin that arrived via the
**account sync** (the real ship path), rather than only from `--plugin-dir`?
Every component has been shown to work separately. Testing it requires a plugin
with a `.mcp.json` on the marketplace's default branch, enabled at user scope.
Look for `mcp__plugin_<plugin>_*` tools in a fresh cloud session.

This is the main residual risk for the KB plugin, whose only engine is now an
MCP server — see [C# MCP engine feasibility](/kb-plugin/csharp-mcp-variant.md).
Once that plugin is on `main`, its first cloud session answers the question.
