#!/usr/bin/env python3
"""Search the knowledge base and return ranked concept pages with snippets.

Scores each concept page against the query with frontmatter fields
(title/description/tags/type) weighted above body text. The KB root is resolved
from --kb-root, else $KB_ROOT, else the working directory. Reserved files
(index.md, log.md) and raw/ snapshots are excluded unless --include-raw.

Usage:
  kb_search.py "how do webhooks retry"
  kb_search.py "invoice dunning" --domain billing --limit 8
  kb_search.py "vat" --domain billing/eu --json

Exit codes: 0 ok (even with no hits), 2 no KB / bad path.
"""
import argparse
import json
import os
import re
import sys

from kb_common import STOP, find_kb_root, parse_frontmatter, tokenize

RESERVED = {"index.md", "log.md"}


def iter_pages(root, include_raw):
    for dirpath, _dirnames, filenames in os.walk(root):
        parts = set(os.path.relpath(dirpath, root).split(os.sep))
        if not include_raw and "raw" in parts:
            continue
        for fn in filenames:
            if fn.endswith(".md") and fn not in RESERVED:
                yield os.path.join(dirpath, fn)


def score_page(meta, body, q_terms):
    if not q_terms:
        return 0.0, {}
    title = tokenize(meta.get("title", ""))
    desc = tokenize(meta.get("description", ""))
    tags = meta.get("tags", [])
    tags = [tags] if isinstance(tags, str) and tags else (tags or [])
    tagtok = tokenize(" ".join(tags))
    typetok = tokenize(str(meta.get("type", "")))
    body_count = {}
    for t in tokenize(body):
        body_count[t] = body_count.get(t, 0) + 1

    total, matched = 0.0, {}
    for t in set(q_terms):
        s = 0.0
        if t in title:
            s += 6.0
        if t in tagtok:
            s += 4.0
        if t in typetok:
            s += 3.0
        if t in desc:
            s += 3.0
        if t in body_count:
            s += 1.0 + 0.3 * min(body_count[t] - 1, 5)
        if s:
            matched[t] = round(s, 2)
            total += s
    coverage = len(matched) / len(set(q_terms))
    return total * (0.5 + 0.5 * coverage), matched


def snippet(body, raw_words, width=160):
    low = body.lower()
    for w in raw_words:
        i = low.find(w)
        if i != -1:
            start, end = max(0, i - width // 2), min(len(body), i + width // 2)
            frag = body[start:end].replace("\n", " ").strip()
            return ("…" if start else "") + frag + ("…" if end < len(body) else "")
    return body.replace("\n", " ").strip()[:width]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="+")
    ap.add_argument("--kb-root", default=None)
    ap.add_argument("--domain", default=None, help="Restrict to a (sub-)domain.")
    ap.add_argument("--type", default=None)
    ap.add_argument("--include-raw", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    kb_root = find_kb_root(args.kb_root)
    if not kb_root:
        print("ERROR: no knowledge base found. Create one with kb-init-domain.",
              file=sys.stderr)
        return 2
    root = os.path.join(kb_root, args.domain) if args.domain else kb_root
    if not os.path.isdir(root):
        print(f"ERROR: {root} not found.", file=sys.stderr)
        return 2

    q_terms = tokenize(" ".join(args.query))
    raw_words = [w for w in re.findall(r"[a-z0-9]+", " ".join(args.query).lower())
                 if w not in STOP and len(w) > 1]
    results = []
    for path in iter_pages(root, args.include_raw):
        try:
            meta, body, _ok, _err = parse_frontmatter(
                open(path, encoding="utf-8").read())
        except (OSError, UnicodeDecodeError):
            continue
        if args.type and str(meta.get("type", "")).lower() != args.type.lower():
            continue
        s, matched = score_page(meta, body, q_terms)
        if s <= 0:
            continue
        results.append({
            "path": os.path.relpath(path, kb_root).replace(os.sep, "/"),
            "title": meta.get("title") or os.path.basename(path)[:-3],
            "type": meta.get("type", ""),
            "description": meta.get("description", ""),
            "score": round(s, 2),
            "matched_terms": matched,
            "snippet": snippet(body, raw_words),
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    results = results[:args.limit]

    if args.json:
        print(json.dumps({"kb_root": kb_root, "query_terms": q_terms,
                          "hits": results}, indent=2))
    else:
        if not results:
            print(f"No matches for: {' '.join(args.query)}")
            print("The knowledge base may not cover this yet — consider "
                  "ingesting a source with kb-ingest.")
            return 0
        print(f"Query terms: {', '.join(q_terms)}   ({len(results)} hits)\n")
        for r in results:
            print(f"[{r['score']:>6}] {r['path']}")
            print(f"         {r['type']}: {r['title']}")
            if r["description"]:
                print(f"         {r['description']}")
            print(f"         …{r['snippet']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
