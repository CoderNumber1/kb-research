---
type: Reference
title: Claude Code plugins and marketplaces
description: Plugin manifest, marketplace manifest, component auto-discovery, and the CLAUDE_PLUGIN_ROOT path variable.
tags: [claude-code, plugins, marketplace]
timestamp: 2026-07-18T00:00:00Z
---

# Plugin

A plugin is a directory with a `.claude-plugin/plugin.json` manifest (name +
optional metadata). Components auto-discover from `skills/`, `agents/`,
`commands/`, and `hooks/hooks.json` at the plugin root — **not** inside
`.claude-plugin/`. The manifest is optional; without it the name derives from the
directory.

# Marketplace

A repo becomes a marketplace with `.claude-plugin/marketplace.json` listing
plugins, each with a `name` and a `source` (a relative path like
`./plugins/foo` for a plugin in the same repo). One repo can host several plugins
(this project hosts [three variants](/kb-plugin/variants.md)).

Install: `/plugin marketplace add <owner/repo>` then
`/plugin install <plugin>@<marketplace>`. A `owner/repo` source resolves to the
repo's **default branch**, so work on a feature branch isn't installable that way
until merged.

# CLAUDE_PLUGIN_ROOT

`${CLAUDE_PLUGIN_ROOT}` resolves to the plugin's install directory. Reference
bundled scripts/config with it (e.g.
`pwsh -File "${CLAUDE_PLUGIN_ROOT}/scripts/kb_lint.ps1"`); it changes on update,
so never store state there. See [hooks and install scopes](hooks-and-scopes.md).

# Citations

[1] [Claude Code plugins reference](https://code.claude.com/docs/en/plugins-reference)
