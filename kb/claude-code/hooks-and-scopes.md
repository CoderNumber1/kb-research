---
type: Reference
title: Plugin hooks and install scopes
description: The SessionStart hook contract for injecting context, and the user/project/local plugin install scopes.
tags: [claude-code, hooks, scopes, sessionstart]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T05:54:02Z }
sources:
  - id: plugins-reference
    resource: "https://code.claude.com/docs/en/plugins-reference"
    title: Claude Code plugins reference — hooks, scopes, environment variables
---

# Hooks

A plugin's `hooks/hooks.json` maps lifecycle events to commands, which may use
`${CLAUDE_PLUGIN_ROOT}` (see
[plugins and marketplaces](plugins-and-marketplace.md)). A **SessionStart** hook
runs when a session begins; to add context, print JSON:

```json
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "…"}}
```

Printing nothing contributes no context — so a detector can announce a resource
when present and stay silent otherwise (the KB plugin used one until its
[MCP engine](/kb-plugin/mcp-server.md) replaced it with an instructions-file
directive). The command can be a bundled script or an inline shell one-liner.

# Install scopes

| Scope | Written to | Effect |
|-------|-----------|--------|
| `user` (default) | `~/.claude/settings.json` | available in all your projects |
| `project` | `.claude/settings.json` | shared with a repo's collaborators |
| `local` | `.claude/settings.local.json` | just this project, gitignored |

`claude plugin install <plugin>@<marketplace> --scope <scope>` selects it.
