---
type: Reference
title: The sandbox VM
description: Platform facts for the Claude Code cloud session VM — architecture, OS, libc, resources, preinstalled runtimes, mounts, and session environment variables.
tags: [environment, cloud, vm, linux, platform]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T02:58:31Z }
sources:
  - id: cloud-mcp-probe-results
    resource: "https://github.com/CoderNumber1/kb-research/blob/e3777aea493ba0f8fd6e1bff9677333be4ef8609/docs/cloud-mcp-probe-results.md"
    title: Cloud MCP probe results
  - id: cloud-mcp-plugin-probe-results
    resource: "https://github.com/CoderNumber1/kb-research/blob/db0bc3d678add905927d88617f9c08d2eb7175ab/docs/cloud-mcp-plugin-probe-results.md"
    title: Cloud MCP plugin probe results
---

# Platform (observed 2026-10-27, `cloud_default`)

| Item | Value |
|------|-------|
| Virtualization | Firecracker microVM (kernel `6.18.x-fc`) |
| Arch | `x86_64` → .NET RID `linux-x64` |
| OS | Ubuntu 24.04.5 LTS |
| libc | glibc 2.39; `libstdc++.so.6.0.33` present |
| CPU / RAM / swap | 4 vCPU / ~16 GB / none |
| Disk | ~30 GB available to the session (`~` and `/tmp` on the same volume) |
| Mounts | no `noexec` on the repo, `~`, or `/tmp` — committed and freshly written executables run |
| Python | `python3` 3.13 |
| .NET | **not** preinstalled; installable user-locally (see [installing tools](installing-tools.md)) |

Other cloud environment types and architectures were not checked; confirm
`uname -m` before shipping a platform-specific binary.

# Session environment variables

Useful for detecting a cloud session from scripts:

- `CLAUDE_CODE_REMOTE=true`
- `CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE=cloud_default`
- `CLAUDE_CODE_SYNC_PLUGINS=1`, `CLAUDE_CODE_SYNC_SKILLS=1` — plugins and skills
  come from the account sync (see
  [plugins and MCP in cloud sessions](/claude-code/cloud-sessions.md))
- `CLAUDE_CODE_BASE_REF` — the branch the session was started on; the working
  branch itself is a generated `ccr-*` name

Outbound HTTPS goes through the [egress proxy](egress-proxy.md)
(`HTTPS_PROXY=http://127.0.0.1:<port>`, custom CA).
