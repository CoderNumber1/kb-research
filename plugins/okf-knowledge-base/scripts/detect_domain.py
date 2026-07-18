#!/usr/bin/env python3
"""Rank knowledge-base domains by how well they match a source's topic.

Reads every domain.md in the bundle (at any depth — nested sub-domains
included), and scores each against query terms (keyword overlap, title/tags
weighted above description/body). Gives kb-ingest a deterministic baseline for
auto-selecting a target domain; the agent makes the final call.

The KB root is resolved from --kb-root, else $KB_ROOT, else the working
directory (see kb_common.find_kb_root).

Usage:
  detect_domain.py --query "stripe webhook signature verification failed"
  detect_domain.py --list [--json]
  detect_domain.py --query "..." --json

Exit codes: 0 ok, 2 no KB found, 3 no domains in the bundle.
"""
import argparse
import json
import os
import sys

from kb_common import find_kb_root, frontmatter, tokenize


def load_domains(kb_root: str):
    """Every directory holding a domain.md, at any depth. Nested sub-domains get
    a bundle-relative slug like 'billing/eu' so ingest can route to the most
    specific match."""
    domains = []
    if not os.path.isdir(kb_root):
        return domains
    for dirpath, _dirnames, filenames in os.walk(kb_root):
        if "domain.md" not in filenames:
            continue
        rel = os.path.relpath(dirpath, kb_root).replace(os.sep, "/")
        if rel == ".":
            continue
        meta, body = frontmatter(
            open(os.path.join(dirpath, "domain.md"), encoding="utf-8").read())
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [tags] if tags else []
        domains.append({
            "slug": rel,
            "dir": dirpath,
            "title": meta.get("title", rel),
            "description": meta.get("description", ""),
            "tags": tags,
            "status": meta.get("status", "active"),
            "_strong": tokenize(meta.get("title", "") + " " + " ".join(tags)),
            "_weak": tokenize(meta.get("description", "") + " " + body),
        })
    domains.sort(key=lambda d: d["slug"])
    return domains


def score(domain, q_terms):
    q = set(q_terms)
    if not q:
        return 0.0, []
    strong, weak = set(domain["_strong"]), set(domain["_weak"])
    hits_strong = q & strong
    hits_weak = (q & weak) - hits_strong
    raw = 3.0 * len(hits_strong) + 1.0 * len(hits_weak)
    return raw / len(q), sorted(hits_strong) + sorted(hits_weak)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="")
    ap.add_argument("--kb-root", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()

    kb_root = find_kb_root(args.kb_root)
    if not kb_root:
        msg = ("No knowledge base found in the working directory. Create one "
               "with the kb-init-domain skill.")
        print(json.dumps({"error": msg}) if args.json else f"ERROR: {msg}",
              file=None if args.json else sys.stderr)
        return 2

    domains = load_domains(kb_root)
    if not domains:
        msg = f"No domains found under {kb_root}. Create one with kb-init-domain."
        print(json.dumps({"domains": [], "note": msg}) if args.json else msg)
        return 3

    if args.list or not args.query:
        out = [{"slug": d["slug"], "title": d["title"],
                "description": d["description"], "tags": d["tags"],
                "status": d["status"]} for d in domains]
        if args.json:
            print(json.dumps({"kb_root": kb_root, "domains": out}, indent=2))
        else:
            print(f"Domains in {kb_root}:")
            for d in out:
                tg = f"  tags: {', '.join(d['tags'])}" if d["tags"] else ""
                print(f"  - {d['slug']} — {d['title']}: {d['description']}{tg}")
        return 0

    q_terms = tokenize(args.query)
    ranked = sorted(((score(d, q_terms), d) for d in domains),
                    key=lambda x: x[0][0], reverse=True)[:args.limit]

    top = ranked[0][0][0] if ranked else 0.0
    runner = ranked[1][0][0] if len(ranked) > 1 else 0.0
    if top >= 0.5 and (top - runner) >= 0.2:
        confidence = "high"
    elif top >= 0.25:
        confidence = "medium"
    else:
        confidence = "low"

    result = {
        "kb_root": kb_root,
        "query_terms": q_terms,
        "confidence": confidence,
        "recommendation": ranked[0][1]["slug"]
        if confidence != "low" and ranked else None,
        "ranking": [{"slug": d["slug"], "title": d["title"],
                     "score": round(s, 3), "matched_terms": matched,
                     "description": d["description"]}
                    for (s, matched), d in ranked],
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Query terms: {', '.join(q_terms) or '(none)'}")
        print(f"Confidence: {confidence}"
              + (f"  ->  recommend '{result['recommendation']}'"
                 if result["recommendation"] else "  ->  no clear match"))
        for r in result["ranking"]:
            print(f"  {r['score']:>5}  {r['slug']:<24} "
                  f"matched: {', '.join(r['matched_terms']) or '-'}")
        if confidence == "low":
            print("\nNo confident match. Consider asking the user, or creating a "
                  "new domain with kb-init-domain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
