---
type: Reference
title: Claude Code plugins and marketplaces
description: Plugin manifest, marketplace manifest, component auto-discovery, and the CLAUDE_PLUGIN_ROOT path variable.
tags: [claude-code, plugins, marketplace]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T02:58:31Z }
sources:
  - id: claude-code-plugins-reference
    resource: "https://code.claude.com/docs/en/plugins-reference"
    title: Claude Code plugins reference
  - id: cloud-mcp-plugin-probe-results
    resource: "https://github.com/CoderNumber1/kb-research/blob/db0bc3d678add905927d88617f9c08d2eb7175ab/docs/cloud-mcp-plugin-probe-results.md"
    title: Cloud MCP plugin probe results
---

# Plugin

A plugin is a directory with a `.claude-plugin/plugin.json` manifest (name +
optional metadata). Components auto-discover from `skills/`, `agents/`,
`commands/`, and `hooks/hooks.json` at the plugin root — **not** inside
`.claude-plugin/`. The manifest is optional; without it the name derives from the
directory.

A `.mcp.json` at the plugin root declares MCP servers the plugin provides
(`{"mcpServers": {"<name>": {"command": "${CLAUDE_PLUGIN_ROOT}/...", "args": [...]}}}`);
their tools appear as `mcp__plugin_<plugin>_<server>__<tool>`. For how this
behaves in cloud sessions, see
[plugins and MCP in cloud sessions](cloud-sessions.md).

# Marketplace

A repo becomes a marketplace with `.claude-plugin/marketplace.json` listing
plugins, each with a `name` and a `source` (a relative path like
`./plugins/foo` for a plugin in the same repo). One repo can host several plugins
(this project hosts [three variants](/kb-plugin/variants.md)).

Install: `/plugin marketplace add <owner/repo>` then
`/plugin install <plugin>@<marketplace>`. A `owner/repo` source resolves to the
repo's **default branch**, so work on a feature branch isn't installable that way
until merged. Cloud sessions are subject to the same rule: their synced plugins
are a pinned default-branch commit, not the session's checkout.

# CLAUDE_PLUGIN_ROOT

`${CLAUDE_PLUGIN_ROOT}` resolves to the plugin's install directory. Reference
bundled scripts/config with it (e.g.
`pwsh -File "${CLAUDE_PLUGIN_ROOT}/scripts/kb_lint.ps1"`); it changes on update,
so never store state there. See [hooks and install scopes](hooks-and-scopes.md).
