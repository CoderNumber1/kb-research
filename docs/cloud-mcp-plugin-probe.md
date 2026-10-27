# Cloud MCP plugin probe

**Audience: a Claude Code cloud session started on the `probe/cloud-mcp`
branch.** If you were asked to run this probe, work through every step below,
then write and push the results file described in [Report](#report). Do not
change anything else in the repository.

MCP configuration is read when a session **starts**. This probe only means
something in a session that was started on a branch already carrying the probe
files (below); nothing you do mid-session can make the host load them. If
`git branch --show-current` and `CLAUDE_CODE_BASE_REF` both say something other
than `probe/cloud-mcp`, or the files are missing, record that and stop.

## Why

[The first probe](cloud-mcp-probe-results.md) showed a self-contained
`linux-x64` .NET MCP binary runs on the cloud VM, but could not show whether an
MCP server declared in **config** gets loaded: the session had no `.mcp.json`
anywhere and every MCP tool was host-provided. This probe declares the same
trivial server in three places and records which ones the cloud session's own
host actually starts and exposes as tools.

Already established while writing this probe (2026-10-27, cloud VM, Claude Code
2.1.311), so treat these as controls, not open questions:

- A headless child `claude -p --plugin-dir probes/mcp/plugin` connects both of
  the plugin's servers and can call `probe_ping`; `${CLAUDE_PLUGIN_ROOT}` is
  set and the exec-bit launch works.
- The same child with a plugin wrapping the .NET `McpProbe` binary connects
  and answers `probe_echo`.
- A headless child started in the repo root connects the project
  `.mcp.json` server (`source: project`), but does **not** install the plugin
  from the project `.claude/settings.json` directory marketplace.
- `claude mcp list` in the repo root shows `probe-project` as
  "Pending approval" despite `enableAllProjectMcpServers: true`.

## What the probe adds

All of it is probe-only; remove it before anything merges to `main`.

| File | Declares |
| --- | --- |
| `probes/mcp/plugin/server.py` | Stdlib stdio MCP server (mode 100755). Tool `probe_ping` returns its launch label, pid, cwd and `CLAUDE_PLUGIN_ROOT`. Every start and request is appended to `$MCP_PROBE_LOG` (default `/tmp/mcp-probe.log`), so a spawn is visible even if no tool reaches the model. |
| `probes/mcp/plugin/.mcp.json` | Plugin servers `probe-interp` (`python3 ${CLAUDE_PLUGIN_ROOT}/server.py`) and `probe-exec` (`${CLAUDE_PLUGIN_ROOT}/server.py` run directly, the way a native binary would be). |
| `probes/mcp/plugin/.claude-plugin/plugin.json` | Plugin `mcp-probe`. |
| `probes/mcp/.claude-plugin/marketplace.json` | Marketplace `kb-mcp-probe` listing `mcp-probe`. |
| `.mcp.json` (repo root) | Project server `probe-project` (label `project`). |
| `.claude/settings.json` (repo root) | `enableAllProjectMcpServers: true`; `extraKnownMarketplaces.kb-mcp-probe` as a `directory` source `./probes/mcp`; `enabledPlugins["mcp-probe@kb-mcp-probe"]: true`. |
| `probes/mcp/handshake.py` | Drives one server by hand: `handshake.py <tool> <command> [args...]`. |

Labels in the log tell you which declaration launched a server: `project`,
`plugin-interp`, `plugin-exec`. Plugin tools are named
`mcp__plugin_mcp-probe_<server>__probe_ping`; the project tool is
`mcp__probe-project__probe_ping`.

## 1. Preconditions

```bash
git branch --show-current; echo "base ref: $CLAUDE_CODE_BASE_REF"
git log -1 --oneline
git ls-files -s probes/mcp/plugin/server.py .mcp.json .claude/settings.json
claude --version; echo "session CLI: $CLAUDE_CODE_EXECPATH"; "$CLAUDE_CODE_EXECPATH" --version
```

## 2. What the session host loaded (the real question)

Do this **before** any step that runs a child `claude`, so every log line comes
from the host that launched this session.

```bash
cat /tmp/mcp-probe.log 2>/dev/null || echo "no /tmp/mcp-probe.log: no probe server was started by the host"
```

Then check your own tool list for any tool whose name contains `probe_ping`.
MCP tools may be deferred: if none is listed, run ToolSearch with the query
`probe_ping` before concluding there are none. Record every full name you find.
Call each one (no arguments) and record its output; the `label` and
`CLAUDE_PLUGIN_ROOT` in the reply say which declaration it came from. Re-read
`/tmp/mcp-probe.log` afterwards and confirm a `tools/call` line appeared.

Then gather the host-side state:

```bash
claude mcp list
claude plugin list 2>&1 | head -40
grep -n '"mcp-probe\|kb-mcp-probe' ~/.claude/plugins/installed_plugins.json ~/.claude/plugins/known_marketplaces.json ~/.claude/settings.json 2>/dev/null || echo "probe plugin/marketplace not registered"
# Project approval state (key names and server names only, no values that could be secrets)
python3 - <<'EOF'
import json, os
p = os.path.expanduser("~/.claude.json")
try:
    d = json.load(open(p))
except Exception as e:
    print("~/.claude.json:", e); raise SystemExit
for k, v in (d.get("projects") or {}).items():
    if "kb-research" in k:
        print(k, {x: v.get(x) for x in ("hasTrustDialogAccepted", "enabledMcpjsonServers", "disabledMcpjsonServers", "enableAllProjectMcpServers") if x in v})
EOF
# Startup diagnostics that mention the probe or MCP config loading
for f in "$CLAUDE_CODE_DIAGNOSTICS_FILE" ~/.claude/debug/*; do
  [ -f "$f" ] && grep -iE 'probe-|mcp-probe|kb-mcp-probe|mcpjson|\.mcp\.json|extraKnownMarketplaces' "$f" | head -20 | sed -E 's/(token|key|secret)[^ ]*/\1=<redacted>/Ig' | sed "s|^|$f: |"
done
```

## 3. Headless controls

These repeat the checks that already passed when this probe was written, to
show the CLI on this VM can load each declaration when it reads it itself. Use
a separate log so they don't mix with step 2, and run the whole block as
**one** shell command (shell variables don't persist between tool calls).
`--allowedTools` is variadic, so it must use `=` and the prompt must come first.

```bash
REPO="$(git rev-parse --show-toplevel)"; W=/tmp/mcpprobe2; mkdir -p "$W"
export MCP_PROBE_LOG="$W/child.log"; : > "$MCP_PROBE_LOG"
summ() { python3 - "$1" <<'EOF'
import json, sys
for line in open(sys.argv[1]):
    m = json.loads(line)
    if m.get("type") == "system" and m.get("subtype") == "init":
        print("  mcp_servers:", [(s["name"], s["status"], s.get("source")) for s in m.get("mcp_servers", [])])
        print("  probe tools:", [t for t in m.get("tools", []) if "probe" in t])
        print("  plugins:", [p["source"] for p in m.get("plugins", [])])
    elif m.get("type") == "result":
        print("  result:", m.get("subtype"), "is_error=", m.get("is_error"), str(m.get("result"))[:300])
EOF
}

# a) Plugin .mcp.json via --plugin-dir, calling the direct-exec server.
T=mcp__plugin_mcp-probe_probe-exec__probe_ping
(cd "$W" && timeout 150 claude -p "Call the $T tool and reply with its exact output." \
  --plugin-dir "$REPO/probes/mcp/plugin" --output-format stream-json --verbose --max-turns 3 \
  --allowedTools="$T" < /dev/null > a.jsonl 2> a.err); echo "a) exit=$?"; summ "$W/a.jsonl"; head -c 300 "$W/a.err"

# b) Project .mcp.json + .claude/settings.json, from the repo root.
(cd "$REPO" && timeout 150 claude -p "Reply OK." --output-format stream-json --verbose --max-turns 1 \
  < /dev/null > "$W/b.jsonl" 2> "$W/b.err"); echo "b) exit=$?"; summ "$W/b.jsonl"; head -c 300 "$W/b.err"

echo "child log labels/events:"
python3 -c "import json,sys; print(sorted({(json.loads(l)['label'], str(json.loads(l)['event'])[:10]) for l in open(sys.argv[1])}))" "$MCP_PROBE_LOG"
```

## 4. Optional: .NET binary through a plugin `.mcp.json`

Only if step 3a passed. First run the whole step 5 block of
[cloud-mcp-probe.md](cloud-mcp-probe.md); it installs the SDK and leaves the
published binary at `/tmp/mcpprobe/out/McpProbe`. Then wrap that binary in a
throwaway plugin and run it the way a shipped plugin would. One shell command:

```bash
set -x
D=/tmp/mcpprobe2/dotnet-plugin; mkdir -p "$D/.claude-plugin" "$D/bin"
cp /tmp/mcpprobe/out/McpProbe "$D/bin/"
echo '{"name":"mcp-probe-dotnet","version":"0.0.1"}' > "$D/.claude-plugin/plugin.json"
echo '{"mcpServers":{"dotnet":{"command":"${CLAUDE_PLUGIN_ROOT}/bin/McpProbe"}}}' > "$D/.mcp.json"
T=mcp__plugin_mcp-probe-dotnet_dotnet__probe_echo
cd /tmp/mcpprobe2 && timeout 150 claude -p "Call the $T tool with text 'hi' and reply with its exact output." \
  --plugin-dir "$D" --output-format stream-json --verbose --max-turns 3 --allowedTools="$T" \
  < /dev/null | grep -E '"subtype":"init"|"type":"result"' | cut -c1-600
```

## Report

Write `docs/cloud-mcp-plugin-probe-results.md` containing:

1. **Verdict** — one line each:
   - does the cloud session host load a project `.mcp.json`? (yes / pending approval / no)
   - does it install and load a plugin from the project `.claude/settings.json`
     directory marketplace? (yes / no)
   - can a plugin's `.mcp.json` server run here when the plugin is loaded?
     (from step 3a, and step 4 for .NET)
2. **Host evidence** (step 2) — the contents of `/tmp/mcp-probe.log` before
   any child ran, the `probe_ping` tool names in your tool list (or "none, also
   not found by ToolSearch") and their call output, `claude mcp list`, plugin
   registration, project approval keys, relevant diagnostic lines.
3. **Controls** (step 3) — for a) and b): servers and status, probe tools,
   plugins, result line, and the child-log labels.
4. **.NET** (step 4) — init line and result, or "skipped" and why.
5. **Implications** — how the real plugin should declare its server given
   these results (e.g. plugin `.mcp.json` works once installed from the
   marketplace; project-settings marketplaces don't auto-install in the cloud;
   project servers need approval), and what still needs a user-side test. The
   one path this probe cannot exercise is the real ship path: a plugin with a
   `.mcp.json` installed from the GitHub marketplace on `main` and synced into
   the session. Say whether that test is still needed.

Redact any token or secret values. Then commit **only** that file and push it
to the branch you were started on:

```bash
git add docs/cloud-mcp-plugin-probe-results.md
git commit -m "Add cloud MCP plugin probe results"
git push
```
