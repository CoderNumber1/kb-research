# Cloud MCP probe — results

Run on 2026-10-27 in a Claude Code cloud session (environment type
`cloud_default`), following [cloud-mcp-probe.md](cloud-mcp-probe.md).

## 1. Verdict

**Yes, with conditions:** a committed, self-contained, single-file
**`linux-x64`** .NET MCP binary runs here unchanged. The trimmed + ReadyToRun
build is ~31 MB, needs only glibc + libstdc++, and answers `initialize` in
~100–125 ms with no SDK on `PATH`. The conditions are about how the binary gets
to the VM and gets loaded, not whether it runs (see [Implications](#4-implications)).

## 2. Facts (steps 1–4)

| Item | Value |
| --- | --- |
| Kernel | `Linux vm 6.18.44-fc-v165 #1 SMP PREEMPT_DYNAMIC x86_64 GNU/Linux` (Firecracker VM) |
| Arch → RID | `x86_64` → `linux-x64` |
| OS | Ubuntu 24.04.5 LTS (noble) |
| glibc | `ldd (Ubuntu GLIBC 2.39-0ubuntu8.9) 2.39` — same as the WSL reference |
| libstdc++ | `/lib/x86_64-linux-gnu/libstdc++.so.6` → `libstdc++.so.6.0.33` |
| CPU / RAM / swap | 4 vCPU / 16 091 MB / none |
| Disk (`~`, `/tmp`) | both on `/dev/vda`: 252G size, 30G avail (per-session allowance) |
| .NET preinstalled | no (`dotnet` not on `PATH`) |
| Python | `/usr/bin/python3`, 3.13.17 |
| Exec bit preserved by clone | yes — `git ls-files -s` 100755, `stat` `-rwxr-xr-x`; `./kb_search.py --help` runs |
| Exec bit in installed plugin cache | yes — modes mirror git (e.g. `kb_analyze.py`, committed 100644, is `-rw-r--r--` in the cache; the 100755 scripts are `-rwxr-xr-x`) |
| noexec mounts | none — repo, `~` and `/tmp` are all `/` mounted `rw,relatime,…` (no `noexec`); `/tmp/probe.sh` printed `exec-ok` |
| `https://dot.net/v1/dotnet-install.sh` | 301 (redirect; 200 with `-L` → `builds.dotnet.microsoft.com/dotnet/scripts/v1/dotnet-install.sh`) |
| `https://builds.dotnet.microsoft.com/` | 400 at the bare root; 200 for `…/dotnet/release-metadata/releases-index.json`; the 240 MB SDK tarball downloaded fine |
| `https://api.nuget.org/v3/index.json` | 200 (package restore worked) |
| `https://github.com/` | 400 (through the agent proxy) |
| `https://objects.githubusercontent.com/` | 404 at the root (host reachable, no object requested) |
| `https://release-assets.githubusercontent.com/` | 404 at the root (host reachable, no object requested) |
| Proxy | `HTTPS_PROXY`/`https_proxy=http://127.0.0.1:<port>` (local agent proxy, custom CA); `NO_PROXY` covers localhost, private ranges, `*.anthropic.com` API hosts, npm/jsr/PyPI/crates/Go proxies |
| `CLAUDE*` env (relevant) | `CLAUDE_CODE_REMOTE=true`, `CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE=cloud_default`, `CLAUDE_CODE_ENTRYPOINT=remote_mobile`, `CLAUDE_CODE_SYNC_PLUGINS=1`, `CLAUDE_CODE_SYNC_SKILLS=1`, `CLAUDE_CODE_DISABLE_BUILTIN_ANTMCP=1`, `CLAUDE_CODE_VERSION=2.1.42`; token values redacted, account/org IDs omitted |
| `~/.claude` | present; `settings.json` enables `okf-knowledge-base@kb-research` and `mattpocock-skills@mattpocock` |
| Installed plugin | `okf-knowledge-base@kb-research` 0.1.0, user scope, cached at `~/.claude/plugins/cache/kb-research/okf-knowledge-base/0.1.0/`, from marketplace `CoderNumber1/kb-research` at commit `3d4c51d` (the marketplace's default branch, **not** this session's checkout) |
| Repo `.claude/settings.json` / `.mcp.json` | neither exists |
| `claude` CLI on `PATH` | `/opt/node22/bin/claude`, `2.1.311 (Claude Code)`; `claude mcp list` → "No MCP servers configured." (the session itself runs from `/opt/claude-code/bin/claude`) |
| MCP tools available to the session | `mcp__github__*`, `mcp__claude-code-remote__*`, `mcp__Claude_Docs__*` (all host-provided); `Webull` listed as needing auth. None come from a plugin `.mcp.json` |
| `okf-knowledge-base` skills loaded | yes — `kb-init-domain`, `kb-ingest`, `kb-search`, `kb-lint`, `kb-consolidate`, plus the `knowledge-curator` agent and the `SessionStart` hook (it announced the KB at session start) |

## 3. Step 5 output

- SDK install: `dotnet-install.sh --channel 10.0` → SDK **10.0.403** in `~/.dotnet`.
- Restore: `Restored /tmp/mcpprobe/McpProbe.csproj (in 4.22 sec)`.
- Publish (`-r linux-x64 --self-contained -p:PublishSingleFile=true
  -p:PublishTrimmed=true -p:PublishReadyToRun=true`, first run incl. restore):
  `real 0m27.618s`, `user 0m28.695s`, `sys 0m4.719s`.
- Binary: `-rwxr-xr-x 30948986 out/McpProbe` (~29.5 MiB / 31 MB).
- `ldd out/McpProbe`:

  ```
  linux-vdso.so.1
  libdl.so.2 => /lib/x86_64-linux-gnu/libdl.so.2
  librt.so.1 => /lib/x86_64-linux-gnu/librt.so.1
  libgcc_s.so.1 => /lib/x86_64-linux-gnu/libgcc_s.so.1
  libpthread.so.0 => /lib/x86_64-linux-gnu/libpthread.so.0
  libm.so.6 => /lib/x86_64-linux-gnu/libm.so.6
  libstdc++.so.6 => /lib/x86_64-linux-gnu/libstdc++.so.6
  libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6
  /lib64/ld-linux-x86-64.so.2
  ```

- Handshakes (`env -i PATH=/usr/bin:/bin`, SDK not visible):

  ```
  initialize OK in 123 ms; tools=['probe_echo']; call -> 'echo: hi'
  initialize OK in 114 ms; tools=['probe_echo']; call -> 'echo: hi'
  ```

- Same binary copied into the repo checkout and run from there:

  ```
  initialize OK in 102 ms; tools=['probe_echo']; call -> 'echo: hi'
  ```

## 4. Implications

- **`linux-x64` is the RID needed here**; this VM is x86_64 with the same glibc
  (2.39) as the WSL reference, so the WSL-built binary should run as-is. No
  arm64 build is required for this environment (other cloud environments were
  not tested).
- **Committing the binary works for execution.** The exec bit survives both the
  session clone and the plugin-cache install (modes mirror git), and nothing is
  mounted `noexec`. Commit it as mode 100755 (`git update-index --chmod=+x`), or
  it lands non-executable — the cache faithfully copied a 100644 script as
  `-rw-r--r--`.
- **Building or downloading at session start is also viable**: `dot.net`,
  `builds.dotnet.microsoft.com` and `api.nuget.org` are reachable through the
  proxy, and a full SDK install + restore + publish took well under a minute of
  build time. Bare `github.com` returned 400 via the proxy, so a
  GitHub-release download path was not proven; test a real release-asset URL
  before relying on it.
- **The plugin is installed from the marketplace's default branch**, not from
  the session's checkout. A binary has to be on that branch to reach cloud
  sessions through the plugin, and the cache is a pinned commit copy
  (~31 MB per binary per installed version).
- **MCP loading is unverified.** `claude mcp list` shows no servers and every
  MCP tool in this session is host-provided; the plugin currently ships no
  `.mcp.json`, so this probe could not show whether a plugin `.mcp.json` is
  honoured in cloud sessions. The next probe should add a plugin `.mcp.json`
  pointing at a committed binary (via `${CLAUDE_PLUGIN_ROOT}`) and check
  whether its tools appear. Note `CLAUDE_CODE_DISABLE_BUILTIN_ANTMCP=1` only
  concerns built-in servers, and plugin skills/hooks do load
  (`CLAUDE_CODE_SYNC_PLUGINS=1`).
