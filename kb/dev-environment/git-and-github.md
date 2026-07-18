---
type: Playbook
title: Git and GitHub in the sandbox
description: Pushing when the session token is read-only, the PAT workaround, why PR creation is blocked, reserved token vars, and unsigned commits.
tags: [environment, git, github, pat]
timestamp: 2026-07-18T00:00:00Z
---

# The default token is often read-only

The session's injected GitHub credential may be **read-only** for a repo: fetch
works, `git push` returns `403` ("Permission ... denied"). Probe read vs write
by comparing the `git-upload-pack` (read) and `git-receive-pack` (write)
services. A read-only token is a permissions issue on the app installation, not
the user's own access.

# Reserved token env vars

`GITHUB_TOKEN` and `GH_TOKEN` are **reserved** — the harness injects the sentinel
value `proxy-injected`, so a personal access token placed there is ignored. Put a
PAT under a **different** variable name (env vars load at session start, so a new
value needs a fresh session).

# Pushing with a PAT

The git remote is rewritten to an internal proxy via an `insteadOf` rule in
`/root/.gitconfig`. To push to `github.com` directly with a PAT (needs
`Contents: write`), bypass that global config for one command and supply the
token via a credential helper so it never appears in the URL or logs:

```bash
GIT_CONFIG_GLOBAL=/dev/null GIT_SSL_CAINFO=/root/.ccr/ca-bundle.crt \
git -c credential.helper='!f() { echo username=x-access-token; echo "password=$KB_PAT"; }; f' \
    push https://github.com/OWNER/REPO.git BRANCH
```

# PR creation is blocked

Opening a PR needs the GitHub **API**, which the [egress proxy](egress-proxy.md)
gates on the org connecting the Claude GitHub App (and the app/PAT having
`Pull requests: write`). Both the REST API (via PAT) and the MCP GitHub tool
return `403` here. Workaround: push the branch, then open the PR manually from the
`compare/...` URL, or have an admin connect the app with PR permission.

# Unsigned commits

No signing key is available, so commits show as **Unverified** on GitHub even
with the correct committer email. This is cosmetic; contents are intact.

# Citations

[1] Sandbox proxy readme: `/root/.ccr/README.md`
