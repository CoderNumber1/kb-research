#!/usr/bin/env python3
"""Minimal stdio MCP server for the cloud MCP plugin probe.

Pure stdlib. Every start is appended to $MCP_PROBE_LOG (default
/tmp/mcp-probe.log), so a spawn is visible even if its tools never reach the
model. Exposes one tool, probe_ping, which reports how it was launched.
"""
import json
import os
import sys
import time

LABEL = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else "unlabelled"
LOG = os.environ.get("MCP_PROBE_LOG", "/tmp/mcp-probe.log")


def log(event):
    with open(LOG, "a") as fh:
        fh.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "label": LABEL,
                             "pid": os.getpid(), "event": event}) + "\n")


def launch_info():
    return {"label": LABEL, "pid": os.getpid(), "argv0": sys.argv[0], "cwd": os.getcwd(),
            "python": sys.version.split()[0],
            "CLAUDE_PLUGIN_ROOT": os.environ.get("CLAUDE_PLUGIN_ROOT")}


def reply(msg_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\n")
    sys.stdout.flush()


TOOL = {"name": "probe_ping", "description": "Reports how this probe MCP server was launched.",
        "inputSchema": {"type": "object", "properties": {}}}


def main():
    log({"start": launch_info()})
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        method, msg_id = msg.get("method"), msg.get("id")
        if msg_id is None:  # notification
            continue
        if method == "initialize":
            log("initialize")
            reply(msg_id, {"protocolVersion": msg["params"].get("protocolVersion", "2025-06-18"),
                           "capabilities": {"tools": {}},
                           "serverInfo": {"name": f"mcp-probe-{LABEL}", "version": "0"}})
        elif method == "tools/list":
            log("tools/list")
            reply(msg_id, {"tools": [TOOL]})
        elif method == "tools/call":
            log("tools/call")
            reply(msg_id, {"content": [{"type": "text", "text": "pong " + json.dumps(launch_info())}]})
        elif method == "ping":
            reply(msg_id, {})
        else:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id,
                                         "error": {"code": -32601, "message": method}}) + "\n")
            sys.stdout.flush()
    log("exit")


if __name__ == "__main__":
    main()
