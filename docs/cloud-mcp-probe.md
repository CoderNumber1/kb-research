# Cloud MCP probe

**Audience: a Claude Code cloud session.** If you were asked to run this probe,
work through every step below, then write and push the results file described
in [Report](#report). Do not change anything else in the repository.

## Why

We are deciding whether this plugin could ship a C# MCP server as a
**self-contained, single-file .NET executable** (no .NET install on the host),
launched from the plugin's `.mcp.json`. It already works on Ubuntu 24.04 under
WSL (x86_64, glibc 2.39): a trimmed + ReadyToRun `linux-x64` build is ~33 MB,
needs only glibc + libstdc++, and answers `initialize` in ~120 ms. This probe
finds out whether the **cloud session VM** can do the same, and if not, why.

Record what you observe. If a step fails, capture the exact error and keep
going; a failure is a result.

## 1. Platform

```bash
uname -a
uname -m                                   # x86_64 -> linux-x64, aarch64 -> linux-arm64
cat /etc/os-release
ldd --version | head -1                    # glibc version (musl prints differently)
ls /lib/x86_64-linux-gnu/libstdc++.so.6* /lib/aarch64-linux-gnu/libstdc++.so.6* 2>/dev/null
nproc; free -m; df -h ~ /tmp
command -v dotnet && dotnet --list-sdks
command -v python3 && python3 --version
```

## 2. Can it execute files?

```bash
# Executable bit preserved by the clone? These are committed as mode 100755.
git ls-files -s plugins/okf-knowledge-base/scripts/kb_search.py
stat -c '%A %n' plugins/okf-knowledge-base/scripts/kb_search.py
./plugins/okf-knowledge-base/scripts/kb_search.py --help | head -3

# noexec mounts? (repo dir, home, /tmp)
findmnt -T . -o TARGET,OPTIONS; findmnt -T ~ -o TARGET,OPTIONS; findmnt -T /tmp -o TARGET,OPTIONS
printf '#!/bin/sh\necho exec-ok\n' > /tmp/probe.sh && chmod +x /tmp/probe.sh && /tmp/probe.sh
```

## 3. Network reachability

A binary committed to the repo needs no network. Building one, or downloading
one at session start, does. Record the HTTP status (or the failure) for each:

```bash
for u in https://dot.net/v1/dotnet-install.sh \
         https://builds.dotnet.microsoft.com/ \
         https://api.nuget.org/v3/index.json \
         https://github.com/ \
         https://objects.githubusercontent.com/ \
         https://release-assets.githubusercontent.com/; do
  printf '%-50s ' "$u"; curl -sS -o /dev/null -w '%{http_code}\n' --max-time 15 "$u" 2>&1
done
env | grep -iE '^(https?|no)_proxy=' || echo "no proxy vars"
```

## 4. Plugin and MCP context

```bash
env | grep -E '^CLAUDE' | sed -E 's/(TOKEN|KEY|SECRET)=.*/\1=<redacted>/'
ls -la ~/.claude 2>/dev/null; ls -R ~/.claude/plugins 2>/dev/null | head -50
cat .claude/settings.json 2>/dev/null; cat .mcp.json 2>/dev/null
command -v claude && claude --version && claude mcp list
```

Also state, from your own tool list, whether any MCP server tools are available
to you in this session (names only), and whether `okf-knowledge-base` plugin
skills are loaded.

## 5. Build and run a minimal MCP server

This uses the same stack as the real server (.NET 10, `ModelContextProtocol`
1.2.0, `Microsoft.Extensions.Hosting` 10.0.5) and the same publish flags. It was
verified under WSL before this file was committed. Skip to the report if step 3
shows `dot.net` or `api.nuget.org` unreachable, and say so.

Run the whole block as **one** shell command from the repository root (shell
variables do not persist between separate tool calls).

```bash
set -x
REPO="$(git rev-parse --show-toplevel)"
# Install the SDK user-locally (does not touch the system).
curl -sSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
bash /tmp/dotnet-install.sh --channel 10.0 --install-dir ~/.dotnet
export PATH="$HOME/.dotnet:$PATH" DOTNET_CLI_TELEMETRY_OPTOUT=1
dotnet --list-sdks

mkdir -p /tmp/mcpprobe && cd /tmp/mcpprobe
cat > McpProbe.csproj <<'EOF'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <InvariantGlobalization>true</InvariantGlobalization>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" Version="10.0.5" />
    <PackageReference Include="ModelContextProtocol" Version="1.2.0" />
  </ItemGroup>
</Project>
EOF
cat > Program.cs <<'EOF'
using System.ComponentModel;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;

var builder = Host.CreateApplicationBuilder(args);
builder.Logging.ClearProviders();
builder.Services.AddMcpServer().WithStdioServerTransport().WithTools<ProbeTools>();
await builder.Build().RunAsync();

[McpServerToolType]
public sealed class ProbeTools
{
    [McpServerTool(Name = "probe_echo"), Description("Echoes text back.")]
    public static string Echo(string text) => $"echo: {text}";
}
EOF
cat > handshake.py <<'EOF'
import json, subprocess, sys, time
t0 = time.perf_counter()
p = subprocess.Popen([sys.argv[1]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
def send(m): p.stdin.write(json.dumps(m) + "\n"); p.stdin.flush()
def recv(): return json.loads(p.stdout.readline())
send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "probe", "version": "0"}}})
init = recv()["result"]; ms = (time.perf_counter() - t0) * 1000
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}); tools = [t["name"] for t in recv()["result"]["tools"]]
send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "probe_echo", "arguments": {"text": "hi"}}})
echo = recv()["result"]["content"][0]["text"]
p.stdin.close(); p.wait(timeout=10)
print(f"initialize OK in {ms:.0f} ms; tools={tools}; call -> {echo!r}")
EOF

RID=linux-x64; [ "$(uname -m)" = "aarch64" ] && RID=linux-arm64
time dotnet publish -c Release -r $RID --self-contained true \
  -p:PublishSingleFile=true -p:PublishTrimmed=true -p:PublishReadyToRun=true -o out
ls -la out/McpProbe && ldd out/McpProbe

# Run it where the SDK cannot help: strip the SDK from PATH and the env.
env -i PATH=/usr/bin:/bin HOME="$HOME" python3 handshake.py ./out/McpProbe
env -i PATH=/usr/bin:/bin HOME="$HOME" python3 handshake.py ./out/McpProbe

# Same binary, copied into the repo checkout (where a plugin binary would live).
cp out/McpProbe "$REPO/.mcpprobe-bin" && (cd "$REPO" && python3 /tmp/mcpprobe/handshake.py ./.mcpprobe-bin); rm -f "$REPO/.mcpprobe-bin"
```

## Report

Write `docs/cloud-mcp-probe-results.md` containing:

1. **Verdict** — one line: would a committed, self-contained .NET MCP binary run
   here? (yes / yes-with-conditions / no) and which RID.
2. **Facts** — a table of the values from steps 1–4 (arch, OS, glibc,
   libstdc++, exec bit preserved, noexec mounts, each URL's status, proxy,
   plugin/MCP state).
3. **Step 5 output** — publish time, binary size, `ldd` output, and both
   handshake lines (or the exact error).
4. **Implications** — anything that changes how the plugin should ship the
   binary (e.g. arm64 needed, downloads blocked, `.mcp.json` not loaded).

Redact any token or secret values. Then commit **only** that file and push it to
the branch you were started on:

```bash
git add docs/cloud-mcp-probe-results.md
git commit -m "Add cloud MCP probe results"
git push
```
