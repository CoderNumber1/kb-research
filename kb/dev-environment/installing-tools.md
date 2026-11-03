---
type: Playbook
title: Installing tools in the sandbox
description: Which download hosts the egress policy allows, and how PowerShell 7 was installed for the plugin work.
tags: [environment, tooling, powershell, apt]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T02:58:31Z }
sources:
  - id: sandbox-proxy-readme
    resource: file /root/.ccr/README.md in the Claude Code remote sandbox
    title: Sandbox proxy readme
  - id: cloud-mcp-probe-results
    resource: "https://github.com/CoderNumber1/kb-research/blob/e3777aea493ba0f8fd6e1bff9677333be4ef8609/docs/cloud-mcp-probe-results.md"
    title: Cloud MCP probe results
---

# What's reachable

The [egress proxy](egress-proxy.md) allows package registries but blocks
arbitrary hosts. Concretely, when installing PowerShell:

- `github.com` release assets → **blocked** (policy JSON, not the file).
- `packages.microsoft.com` → **reachable** (HTTP 200).

So prefer a distro/vendor package repository over a GitHub release download.

Re-checked 2026-10-27 for .NET: `dot.net`, `builds.dotnet.microsoft.com`, and
`api.nuget.org` are **reachable** (SDK tarball and NuGet restore both worked).
Bare `github.com` returned 400 and the release-asset hosts only answered 404 at
their roots, so GitHub release downloads remain unproven.

# Installing the .NET SDK (worked example)

```bash
curl -sSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
bash /tmp/dotnet-install.sh --channel 10.0 --install-dir ~/.dotnet   # user-local
export PATH="$HOME/.dotnet:$PATH" DOTNET_CLI_TELEMETRY_OPTOUT=1
```

Install + restore + a trimmed single-file publish took ~30 s. Used to test the
[C# MCP variant](/kb-plugin/csharp-mcp-variant.md); see also
[the sandbox VM](sandbox-vm.md).

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
