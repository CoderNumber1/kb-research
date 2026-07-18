# Dev Environment

Operational knowledge for the Claude Code remote execution sandbox — the egress and git proxy, pushing via a personal access token, reserved environment variables, and installing tools like PowerShell.

See [domain.md](domain.md) for scope and conventions.

# Concepts

* [The egress proxy](egress-proxy.md) - How outbound network access is mediated in the Claude Code remote sandbox, and what that gates.
* [Git and GitHub in the sandbox](git-and-github.md) - Pushing when the session token is read-only, the PAT workaround, why PR creation is blocked, reserved token vars, and unsigned commits.
* [Installing tools in the sandbox](installing-tools.md) - Which download hosts the egress policy allows, and how PowerShell 7 was installed for the plugin work.

# Sources

* [Raw sources](raw/) - immutable snapshots of ingested material.
