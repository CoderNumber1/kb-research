"""Drive one stdio MCP server through initialize, tools/list and one tools/call.

Usage: python3 handshake.py <tool-name> <command> [args...]
"""
import json, subprocess, sys, time
tool, cmd = sys.argv[1], sys.argv[2:]
t0 = time.perf_counter()
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
def send(m): p.stdin.write(json.dumps(m) + "\n"); p.stdin.flush()
def recv(): return json.loads(p.stdout.readline())
send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "probe", "version": "0"}}})
recv()["result"]; ms = (time.perf_counter() - t0) * 1000
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}); tools = [t["name"] for t in recv()["result"]["tools"]]
args = {"text": "hi"} if tool == "probe_echo" else {}
send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": tool, "arguments": args}})
out = recv()["result"]["content"][0]["text"]
p.stdin.close(); p.wait(timeout=10)
print(f"initialize OK in {ms:.0f} ms; tools={tools}; call -> {out!r}")
