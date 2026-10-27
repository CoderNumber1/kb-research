# Cloud MCP plugin probe — results

Run 2026-10-27 in a Claude Code cloud session (Claude Code 2.1.311, linux-x64)
following [cloud-mcp-plugin-probe.md](cloud-mcp-plugin-probe.md).

## 1. Verdict

- **Does the cloud session host load a project `.mcp.json`?** **Yes.** The host
  started `probe-project` at session start and exposed
  `mcp__probe-project__probe_ping` (deferred, found by ToolSearch), and calling
  it worked. This happened even though `claude mcp list` reports the server as
  "Pending approval". That status is misleading here.
- **Does it install and load a plugin from the project `.claude/settings.json`
  directory marketplace?** **No.** `kb-mcp-probe` is not registered, `mcp-probe`
  is not installed, and no `plugin-interp`/`plugin-exec` server was started.
- **Can a plugin's `.mcp.json` server run here when the plugin is loaded?**
  **Yes.** Step 3a connected both plugin servers (interpreter and direct-exec),
  and the call returned. Step 4 did the same with a self-contained .NET binary,
  which connected and answered `probe_echo`.

## 2. Host evidence (step 2, before any child `claude`)

Preconditions: current branch `ccr-936f9de1-6q9pl0` (the session's working
branch), `CLAUDE_CODE_BASE_REF=probe/cloud-mcp`, HEAD `1ac6a56` (= `origin/probe/cloud-mcp`).
`server.py` is mode 100755, and `.mcp.json` and `.claude/settings.json` are present.
`claude --version` and `$CLAUDE_CODE_EXECPATH` (`/opt/claude-code/bin/claude`)
both report 2.1.311.

`/tmp/mcp-probe.log` before any child ran:

```
{"t": "2026-10-27T02:40:13", "label": "project", "pid": 220, "event": {"start": {"label": "project", "pid": 220, "argv0": "probes/mcp/plugin/server.py", "cwd": "/home/user/kb-research", "python": "3.13.17", "CLAUDE_PLUGIN_ROOT": null}}}
{"t": "2026-10-27T02:40:13", "label": "project", "pid": 220, "event": "initialize"}
{"t": "2026-10-27T02:40:13", "label": "project", "pid": 220, "event": "tools/list"}
```

After calling the tool, a fourth line appeared:
`{"t": "2026-10-27T02:40:25", "label": "project", "pid": 220, "event": "tools/call"}`.

`probe_ping` tools in the session's tool list: only `mcp__probe-project__probe_ping`.
It was deferred and loaded with ToolSearch `probe_ping`. No
`mcp__plugin_mcp-probe_*` tools existed. Call output:

```
pong {"label": "project", "pid": 220, "argv0": "probes/mcp/plugin/server.py", "cwd": "/home/user/kb-research", "python": "3.13.17", "CLAUDE_PLUGIN_ROOT": null}
```

`claude mcp list`:

```
probe-project: python3 probes/mcp/plugin/server.py --label project - ⏸ Pending approval (run `claude` to approve)
```

`claude plugin list`: only `mattpocock-skills@mattpocock` (1.3.1) and
`okf-knowledge-base@kb-research` (0.1.0), both user scope and enabled.

Plugin registration: the grep printed "probe plugin/marketplace not registered".
`known_marketplaces.json` holds only `kb-research` (github
`CoderNumber1/kb-research`) and `mattpocock` (github `mattpocock/skills`).
`~/.claude/settings.json` has only `enabledPlugins` for those two plugins.

Project approval keys: no `projects` entry for `kb-research` in `~/.claude.json`,
so no output.

Diagnostics (`$CLAUDE_CODE_DIAGNOSTICS_FILE`; `~/.claude/debug` does not
exist): no line matches the probe/mcpjson pattern, and the events carry no
server names. Relevant startup events:

```
02:40:12.664Z plugins_sync_starting
02:40:12.874Z mcp_connect_starting {"transport":"stdio"}   (+4x http)
02:40:13.028Z mcp_connect_complete {"transport":"stdio","duration_ms":153}
02:40:13.392Z plugins_sync_no_changes {"count":0,...,"had_manifest":false}
```

The single stdio connect matches the `project` server start at 02:40:13.

## 3. Controls (step 3, separate log `/tmp/mcpprobe2/child.log`)

**a) `--plugin-dir probes/mcp/plugin`, call `probe-exec`** (exit 0)

- servers: `plugin:mcp-probe:probe-interp` connected (plugin),
  `plugin:mcp-probe:probe-exec` connected (plugin)
- probe tools: `mcp__plugin_mcp-probe_probe-exec__probe_ping`,
  `mcp__plugin_mcp-probe_probe-interp__probe_ping`
- plugins: `mcp-probe@inline`, `okf-knowledge-base@kb-research`,
  `mattpocock-skills@mattpocock`, plus builtins
- result: success, `pong {"label": "plugin-exec", "pid": 394, "argv0": "/home/user/kb-research/probes/mcp/plugin/server.py", "cwd": "/tmp/mcpprobe2", "python": "3.13.17", "CLAUDE_PLUGIN_ROOT": "/home/user/kb-research/probes/mcp/plugin"}`

**b) repo root, project `.mcp.json` + `.claude/settings.json`** (exit 0)

- servers: `probe-project` connected (project)
- probe tools: `mcp__probe-project__probe_ping`
- plugins: `okf-knowledge-base@kb-research`, `mattpocock-skills@mattpocock`,
  plus builtins. `mcp-probe` was **not** installed from the directory marketplace.
- result: success, `OK`

Child-log labels/events: `plugin-exec` (start, initialize, tools/list,
tools/call), `plugin-interp` (start, initialize, tools/list), `project` (start,
initialize, tools/list).

## 4. .NET (step 4)

Step 5 of [cloud-mcp-probe.md](cloud-mcp-probe.md) ran first. It installed SDK
10.0.403 and published in about 30 s, producing a 30.9 MB `McpProbe` that links
only to glibc/libstdc++. The bare handshakes succeeded (`initialize OK in
131–154 ms; tools=['probe_echo']; call -> 'echo: hi'`).

Plugin wrapping (`${CLAUDE_PLUGIN_ROOT}/bin/McpProbe`), exit 0:

- init: `plugin:mcp-probe-dotnet:dotnet` connected (plugin); tool
  `mcp__plugin_mcp-probe-dotnet_dotnet__probe_echo`
- result: success, `echo: hi`

## 5. Implications

- **Declare the real server in the plugin's own `.mcp.json`** with
  `${CLAUDE_PLUGIN_ROOT}/...`. A loaded plugin starts both interpreter-launched
  and directly-executed servers, including a self-contained linux-x64 .NET
  binary with its exec bit intact.
- **Don't rely on project `.claude/settings.json` marketplaces in the cloud.**
  Neither the session host nor a headless child installs a plugin from an
  `extraKnownMarketplaces` directory source plus `enabledPlugins`. The session's
  plugins come from the account-level plugin sync (`plugins_sync`), which here
  installed `okf-knowledge-base@kb-research` from the GitHub marketplace into
  `~/.claude/plugins/cache/...` at user scope.
- **A project `.mcp.json` works as a fallback.** The cloud host starts it at
  session start with no approval step, despite `claude mcp list` showing
  "Pending approval". It runs from the repo checkout with no
  `CLAUDE_PLUGIN_ROOT`, so its paths must be repo-relative.
- **The ship-path test is still needed.** This probe did not exercise a plugin
  with a `.mcp.json`, installed from the GitHub marketplace on `main` and synced
  into the session as `okf-knowledge-base@kb-research` is today. Every component
  has been shown to work on its own: the sync installs the plugin, and a loaded
  plugin's `.mcp.json` server starts. What remains unconfirmed is whether the
  session host starts MCP servers from a *synced* plugin at startup, rather than
  only from `--plugin-dir`. Test it from the user side: add a `.mcp.json` to the
  plugin on `main`, start a fresh cloud session, and look for the
  `mcp__plugin_okf-knowledge-base_*` tools.
