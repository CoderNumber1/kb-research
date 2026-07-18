---
type: Playbook
title: Installing tools in the sandbox
description: Which download hosts the egress policy allows, and how PowerShell 7 was installed for the plugin work.
tags: [environment, tooling, powershell, apt]
timestamp: 2026-07-18T00:00:00Z
---

# What's reachable

The [egress proxy](egress-proxy.md) allows package registries but blocks
arbitrary hosts. Concretely, when installing PowerShell:

- `github.com` release assets → **blocked** (policy JSON, not the file).
- `packages.microsoft.com` → **reachable** (HTTP 200).

So prefer a distro/vendor package repository over a GitHub release download.

# Installing PowerShell 7 (worked example)

```bash
curl -sSL -o ms-prod.deb https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb
dpkg -i ms-prod.deb
apt-get update -o Dir::Etc::sourcelist="sources.list.d/microsoft-prod.list" \
  -o Dir::Etc::sourceparts="-" -o APT::Get::List-Cleanup="0"
DEBIAN_FRONTEND=noninteractive apt-get install -y powershell   # provides `pwsh`
```

This installed PowerShell 7, which was needed to build and parity-test the
[PowerShell plugin variant](/kb-plugin/variants.md). Installs are ephemeral —
they don't persist across sessions, so tests depending on `pwsh` skip cleanly
when it's absent.

# Citations

[1] Sandbox proxy readme: `/root/.ccr/README.md`
