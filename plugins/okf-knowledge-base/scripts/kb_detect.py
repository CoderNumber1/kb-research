#!/usr/bin/env python3
"""SessionStart hook: detect an OKF knowledge base in the working directory.

If a KB is present, emit context announcing it (and its domains) so the model
knows to use the kb-* skills / knowledge-curator agent. If none is found, stay
silent — the plugin adds nothing to unrelated projects. This is what makes the
plugin 'detect and use a KB when present in the working directory'.
"""
import json
import os
import sys

from kb_common import find_kb_root
from detect_domain import load_domains


def main() -> int:
    kb_root = find_kb_root()
    if not kb_root:
        return 0  # no knowledge base here — contribute no context

    try:
        rel = os.path.relpath(kb_root, os.getcwd())
    except ValueError:
        rel = kb_root
    loc = rel if rel.startswith("..") else f"./{rel}"

    domains = load_domains(kb_root)
    if domains:
        names = [d["slug"] for d in domains]
        shown = ", ".join(names[:12]) + (" …" if len(names) > 12 else "")
        context = (
            f"An Open Knowledge Format knowledge base is present at {loc} "
            f"({len(domains)} domain(s): {shown}). It is a Karpathy-style LLM "
            "wiki where knowledge compounds into cross-linked pages. Use the "
            "kb-search skill to answer from it (cite the pages); kb-ingest to "
            "capture sources or findings (it auto-routes to a domain by "
            "description); kb-init-domain for a new area; kb-lint for health "
            "checks — or the knowledge-curator agent for sustained work. Prefer "
            "the compiled wiki over re-deriving from raw sources, and capture "
            "durable new knowledge back into it before finishing."
        )
    else:
        context = (
            f"An empty Open Knowledge Format knowledge base is present at {loc} "
            "(no domains yet). Use the kb-init-domain skill to create the first "
            "domain, then kb-ingest to populate it."
        )

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": context,
    }}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
