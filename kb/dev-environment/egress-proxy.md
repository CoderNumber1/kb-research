---
type: Reference
title: The egress proxy
description: How outbound network access is mediated in the Claude Code remote sandbox, and what that gates.
tags: [environment, proxy, network, tls]
timestamp: 2026-07-18T00:00:00Z
---

# How it works

Outbound HTTPS goes through a local proxy (`$HTTPS_PROXY`) that tunnels to a
policy-enforcing egress proxy. TLS is re-terminated there, so tools must trust
the CA bundle at `/root/.ccr/ca-bundle.crt` (standard CA env vars are pre-set).
Diagnose with `curl -sS "$HTTPS_PROXY/__agentproxy/status"`.

# What it gates

- Package registries (pypi, npm, `packages.microsoft.com`, …) are reachable — see
  [installing tools](installing-tools.md).
- GitHub access is scoped to the session's repositories. Requests to other
  GitHub repos, and to `github.com` release assets, return a policy JSON body
  ("GitHub access to this repository is not enabled for this session").
- `api.github.com` writes are gated on the org connecting the Claude GitHub App —
  which blocks REST-API operations like opening a PR (see
  [git and GitHub](git-and-github.md)).

Rules: never disable TLS verification, never unset `$HTTPS_PROXY`, and do not
retry a `403`/`407` policy denial — report it.

# Citations

[1] Sandbox proxy readme: `/root/.ccr/README.md`
