#!/usr/bin/env python3
"""kb-mcp (Python): the okf-knowledge-base MCP server over stdio. Standard library only.

A drop-in equivalent of the C# server in src/KnowledgeBase.Mcp: the same tools,
arguments, and JSON results, verified by running the xUnit suite against both
(KB_MCP_SERVER=python). The plugin's .mcp.json launches it with `python3`.
"""
import sys

sys.dont_write_bytecode = True  # keep the installed plugin free of __pycache__

if sys.version_info < (3, 11):
    sys.exit("kb-mcp requires Python 3.11 or newer")

import json  # noqa: E402
import traceback  # noqa: E402

from kbmcp import analyze, detect, init, lint, search  # noqa: E402
from kbmcp.common import KbError  # noqa: E402
from kbmcp.index import KbIndex  # noqa: E402

SERVER_INFO = {"name": "kb-mcp", "version": "0.2.0"}
PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
REQUIRED = object()

KB_ROOT = ("Absolute path to the knowledge base root (the kb/ directory holding index.md and the domain "
           "folders). Required; makes the call independent of the working directory.")

INDEX = KbIndex()


def _tool(name, description, params, handler, read_only=False, destructive=False):
    return {"name": name, "description": description, "params": params, "handler": handler,
            "read_only": read_only, "destructive": destructive}


TOOLS = [
    _tool(
        "kb_search",
        "Ranks concept pages by query relevance and returns compact JSON hits with snippets and matched terms. "
        "Used by the kb-search skill, which wraps it with orientation, cross-link traversal, and citation — "
        "prefer that skill for answering questions.",
        [("kb_root", "string", KB_ROOT, REQUIRED),
         ("query", "string", "The natural-language search query.", REQUIRED),
         ("domain", "string", 'Restrict the search to one (sub-)domain slug, e.g. "billing" or "billing/eu".', None),
         ("type", "string", 'Restrict to a frontmatter type, e.g. "Playbook".', None),
         ("limit", "integer", "Maximum number of hits to return (default 10).", 10),
         ("include_raw", "boolean", "Also search user-owned Markdown Raw Artifacts under raw/ (off by default).", False)],
        lambda a: search.run(INDEX, a["kb_root"], a["query"], a["domain"], a["type"], a["limit"], a["include_raw"]),
        read_only=True),
    _tool(
        "kb_detect_domain",
        "Routes a topic to the best-matching knowledge-base domain, or lists all domains. With a query, returns "
        "ranked domains plus a confidence and recommendation (deprecated domains are never routed to); with "
        "list=true or no query, returns the domain catalog. Used by the kb-ingest and kb-capture skills. This "
        "routes; it does not search page content (use kb_search for that).",
        [("kb_root", "string", KB_ROOT, REQUIRED),
         ("query", "string", "Topic text to route to a domain. Omit (or set list=true) to list domains.", None),
         ("list", "boolean", "List all domains instead of scoring a query.", False),
         ("limit", "integer", "Maximum number of ranked domains to return (default 5).", 5)],
        lambda a: detect.run(INDEX, a["kb_root"], a["query"], a["list"], a["limit"]),
        read_only=True),
    _tool(
        "kb_lint",
        "Lints the knowledge base for OKF v0.2 concept-page conformance and wiki hygiene (frontmatter, "
        "provenance/trust/lifecycle fields, broken links, orphans, index drift, staleness) and returns JSON with "
        "summary, conformant, and findings. conformant=false means ERROR-level findings exist; that is a valid "
        "response, not a tool failure. Used by the kb-lint skill and after every write.",
        [("kb_root", "string", KB_ROOT, REQUIRED),
         ("domain", "string", "Restrict linting to one (sub-)domain slug.", None),
         ("fix_index", "boolean", "Rewrite drifted index.md concept lists in place to match the pages on disk.", False),
         ("stale_days", "integer", "Also flag pages whose generated.at (or legacy timestamp) is older than this many "
                                   "days (0 disables; stale_after is always checked).", 0)],
        lambda a: lint.run(INDEX, a["kb_root"], a["domain"], a["fix_index"], a["stale_days"])),
    _tool(
        "kb_analyze",
        "Finds consolidation candidates: clusters of concept pages with high term overlap that may be duplicates, "
        "split into within-domain and cross-domain groups with similarity and estimated byte savings. Used by the "
        "kb-consolidate skill.",
        [("kb_root", "string", KB_ROOT, REQUIRED),
         ("domain", "string", "Analyze within one (sub-)domain only.", None),
         ("min_similarity", "number", "Minimum Jaccard similarity to report a pair (default 0.4).", 0.4),
         ("min_shared_terms", "integer", "Minimum number of shared terms to report a pair (default 4).", 4),
         ("max_postings", "integer", "Skip ultra-common terms appearing in more than this many pages (default 200).", 200),
         ("limit", "integer", "Maximum number of groups to return per scope (default 50).", 50),
         ("include_raw", "boolean", "Also include Markdown Raw Artifacts from raw/ directories (off by default).", False)],
        lambda a: analyze.run(INDEX, a["kb_root"], a["min_similarity"], a["min_shared_terms"], a["max_postings"],
                              a["limit"], a["include_raw"], a["domain"]),
        read_only=True),
    _tool(
        "kb_init",
        "Bootstraps a knowledge base: creates the kb/ root (index.md declaring okf_version 0.2, and log.md) if "
        "absent, and writes or replaces the <knowledge-base> capture directive in the repository instructions file. "
        "capture_mode 'automatic' writes the full directive (search first, end-of-turn kb-capture); 'agent' writes a "
        "search-only directive and leaves capture to the knowledge-curator agent. Re-running switches mode or "
        "refreshes the directive. Used by the kb-init skill.",
        [("kb_root", "string", "Absolute path of the kb/ root to create or reuse.", REQUIRED),
         ("capture_mode", "string", "'automatic' (directive runs kb-capture every turn) or 'agent' (search-only "
                                    "directive; capture only via the knowledge-curator agent).", REQUIRED),
         ("instructions_file", "string", "Instructions file to write the directive into (default: CLAUDE.md beside kb/).", None)],
        lambda a: init.init_kb(INDEX, a["kb_root"], a["capture_mode"], a["instructions_file"]),
        destructive=True),
    _tool(
        "kb_init_domain",
        "Scaffolds a new OKF v0.2 domain (or nested sub-domain) with domain.md, index.md, and log.md, and registers "
        "it in the parent catalog. Requires an existing KB root (run kb-init first). Returns a status line. Used by "
        "the kb-init-domain skill, which settles naming and scope first.",
        [("kb_root", "string", KB_ROOT, REQUIRED),
         ("slug", "string", 'Domain slug (kebab-case). Use "parent/child" or the parent argument for a sub-domain.', REQUIRED),
         ("title", "string", "Human-readable domain title.", REQUIRED),
         ("description", "string", "One-sentence scope description; the key input for auto-routing.", REQUIRED),
         ("parent", "string", "Parent domain slug when creating a sub-domain.", None),
         ("tags", "string", "Comma-separated tags for the domain frontmatter.", None),
         ("force", "boolean", "Reuse an existing domain directory instead of erroring.", False)],
        lambda a: init.init_domain(INDEX, a["kb_root"], a["slug"], a["title"], a["description"], a["parent"],
                                   a["tags"], a["force"]),
        destructive=True),
]
TOOLS_BY_NAME = {t["name"]: t for t in TOOLS}


def _schema(tool):
    props, required = {}, []
    for name, typ, desc, default in tool["params"]:
        prop = {"type": typ, "description": desc}
        if default is REQUIRED:
            required.append(name)
        elif default is not None:
            prop["default"] = default
        props[name] = prop
    return {"type": "object", "properties": props, "required": required}


def _coerce(name, typ, value):
    if typ == "string" and isinstance(value, str):
        return value
    if typ == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"
    if typ == "integer" and not isinstance(value, bool):
        if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
            return int(value)
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return int(value)
    if typ == "number" and not isinstance(value, bool):
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    raise KbError(f"ERROR: argument '{name}' must be a {typ}.")


def _bind(tool, arguments):
    bound = {}
    for name, typ, _, default in tool["params"]:
        value = arguments.get(name)
        if value is None:
            if default is REQUIRED:
                raise KbError(f"ERROR: missing required argument '{name}'.")
            bound[name] = default
        else:
            bound[name] = _coerce(name, typ, value)
    return bound


def _text_result(text, is_error=False):
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _call_tool(params):
    tool = TOOLS_BY_NAME.get(params.get("name"))
    if tool is None:
        raise _RpcError(-32602, f"Unknown tool: {params.get('name')}")
    try:
        return _text_result(tool["handler"](_bind(tool, params.get("arguments") or {})))
    except KbError as ex:
        return _text_result(str(ex), is_error=True)
    except Exception as ex:  # surface, don't crash the server
        traceback.print_exc(file=sys.stderr)
        return _text_result(f"An error occurred invoking '{tool['name']}': {ex}", is_error=True)


class _RpcError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _handle(method, params):
    if method == "initialize":
        requested = params.get("protocolVersion")
        return {
            "protocolVersion": requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": [{
            "name": t["name"],
            "description": t["description"],
            "inputSchema": _schema(t),
            "annotations": {"readOnlyHint": t["read_only"], "destructiveHint": t["destructive"]},
        } for t in TOOLS]}
    if method == "tools/call":
        return _call_tool(params)
    raise _RpcError(-32601, f"Method not found: {method}")


def main():
    out = sys.stdout.buffer

    def send(message):
        out.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n")
        out.flush()

    while True:
        raw = sys.stdin.buffer.readline()
        if not raw:
            return
        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            continue
        if not isinstance(message, dict) or "id" not in message:
            continue  # notifications (and anything without an id) need no response
        try:
            result = _handle(message.get("method"), message.get("params") or {})
        except _RpcError as ex:
            send({"jsonrpc": "2.0", "id": message["id"], "error": {"code": ex.code, "message": str(ex)}})
        else:
            send({"jsonrpc": "2.0", "id": message["id"], "result": result})


if __name__ == "__main__":
    main()
