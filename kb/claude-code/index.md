# Claude Code Platform

Claude Code plugin platform — plugin.json and marketplace.json manifests, component auto-discovery, hooks, CLAUDE_PLUGIN_ROOT, and plugin install scopes.

See [domain.md](domain.md) for scope and conventions.

# Concepts

* [Plugins and MCP servers in cloud sessions](cloud-sessions.md) - How Claude Code cloud sessions acquire plugins and which MCP server declarations they start — observed by probe, with the open questions.
* [Plugin hooks and install scopes](hooks-and-scopes.md) - The SessionStart hook contract for injecting context, and the user/project/local plugin install scopes.
* [Claude Code plugins and marketplaces](plugins-and-marketplace.md) - Plugin manifest, marketplace manifest, component auto-discovery, and the CLAUDE_PLUGIN_ROOT path variable.
