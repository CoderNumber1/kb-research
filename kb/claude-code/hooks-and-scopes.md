---
type: Reference
title: Plugin hooks and install scopes
description: The SessionStart hook contract for injecting context, and the user/project/local plugin install scopes.
tags: [claude-code, hooks, scopes, sessionstart]
timestamp: 2026-07-18T00:00:00Z
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
when present and stay silent otherwise (as the
[KB detector](/kb-plugin/scripts-and-autodetection.md) does). The command can be a
bundled script or an inline shell one-liner.

# Install scopes

| Scope | Written to | Effect |
|-------|-----------|--------|
| `user` (default) | `~/.claude/settings.json` | available in all your projects |
| `project` | `.claude/settings.json` | shared with a repo's collaborators |
| `local` | `.claude/settings.local.json` | just this project, gitignored |

`claude plugin install <plugin>@<marketplace> --scope <scope>` selects it.

# Citations

[1] [Claude Code plugins reference — hooks, scopes, environment variables](https://code.claude.com/docs/en/plugins-reference)
