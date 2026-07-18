#!/usr/bin/env python3
"""Search the knowledge base and return ranked concept pages with snippets.

Scans concept pages across the OKF bundle, scoring each against the query with
frontmatter fields (title, description, tags, type) weighted above body text,
so the most on-topic pages surface first. This is the deterministic retrieval
step of the query workflow; the kb-search skill reads the top hits, follows
cross-links, and synthesizes a cited answer.

Usage:
  kb_search.py "how do webhooks retry"
  kb_search.py "invoice dunning" --domain billing --limit 8
  kb_search.py "sla" --type Playbook --json

Reserved files (index.md, log.md) and raw/ snapshots are excluded by default;
pass --include-raw to search source snapshots too.

Exit codes: 0 ok (even with no hits), 2 error.
"""
import argparse
import json
import os
import re
import sys

STOP = set("""a an the of to in on for and or but with without into from by as at
is are was were be been being this that these those it its you your we our they
their will would can could should may might must do does did done has have had
how what when where why who which than then so if not no about over under""".split())


# Longest-first suffix list; collapses word families (retry/retried/retries,
# deliver/delivery/delivered) to a shared root so a query matches related forms.
_SUFFIXES = sorted([
    "ization", "ational", "ication", "fulness", "ousness", "iveness",
    "ature", "ities", "ement", "ness", "tion", "sion", "ies", "ied", "ying",
    "ing", "ers", "er", "ed", "ly", "al", "s", "y", "e",
], key=len, reverse=True)


def stem(w: str) -> str:
    for suf in _SUFFIXES:
        if len(w) - len(suf) >= 3 and w.endswith(suf):
            return w[:-len(suf)]
    return w


def tokenize(text: str):
    return [stem(t) for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if t not in STOP and len(t) > 1]


def parse_frontmatter(text: str):
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    meta, key = {}, None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1] in (" ", "\t") and raw.strip().startswith("- ") and key:
            meta.setdefault(key, [])
            if isinstance(meta[key], list):
                meta[key].append(_scalar(raw.strip()[2:]))
            continue
        if ":" in raw:
            k, _, v = raw.partition(":")
            key, v = k.strip(), v.strip()
            if v == "":
                meta[key] = ""
            elif v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                meta[key] = [_scalar(x) for x in inner.split(",") if x.strip()] \
                    if inner else []
            else:
                meta[key] = _scalar(v)
    return meta, "\n".join(lines[end + 1:])


def _scalar(v: str):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


RESERVED = {"index.md", "log.md"}


def iter_pages(kb_root: str, include_raw: bool):
    for dirpath, dirnames, filenames in os.walk(kb_root):
        parts = set(os.path.relpath(dirpath, kb_root).split(os.sep))
        if not include_raw and "raw" in parts:
            continue
        for fn in filenames:
            if not fn.endswith(".md") or fn in RESERVED:
                continue
            yield os.path.join(dirpath, fn)


def score_page(meta, body, q_terms):
    q = q_terms
    if not q:
        return 0.0, {}
    title = tokenize(meta.get("title", ""))
    desc = tokenize(meta.get("description", ""))
    tags = meta.get("tags", [])
    tags = [tags] if isinstance(tags, str) and tags else (tags or [])
    tagtok = tokenize(" ".join(tags))
    typetok = tokenize(str(meta.get("type", "")))
    bodytok = tokenize(body)
    body_count = {}
    for t in bodytok:
        body_count[t] = body_count.get(t, 0) + 1

    total, matched = 0.0, {}
    for t in set(q):
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
            s += 1.0 + 0.3 * min(body_count[t] - 1, 5)  # diminishing returns
        if s:
            matched[t] = round(s, 2)
            total += s
    # Reward covering more distinct query terms.
    coverage = len(matched) / len(set(q))
    return total * (0.5 + 0.5 * coverage), matched


def snippet(body, q_terms, width=160):
    low = body.lower()
    for t in q_terms:
        i = low.find(t)
        if i != -1:
            start = max(0, i - width // 2)
            end = min(len(body), i + width // 2)
            frag = body[start:end].replace("\n", " ").strip()
            return ("…" if start else "") + frag + ("…" if end < len(body) else "")
    return body.replace("\n", " ").strip()[:width]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="+")
    ap.add_argument("--kb-root", default="kb")
    ap.add_argument("--domain", default=None, help="Restrict to kb/<domain>/.")
    ap.add_argument("--type", default=None, help="Restrict to a frontmatter type.")
    ap.add_argument("--include-raw", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = args.kb_root
    if args.domain:
        root = os.path.join(args.kb_root, args.domain)
    if not os.path.isdir(root):
        print(f"ERROR: {root} not found.", file=sys.stderr)
        return 2

    q_terms = tokenize(" ".join(args.query))
    # Raw (unstemmed) words for locating readable snippets in the body text.
    raw_words = [w for w in re.findall(r"[a-z0-9]+", " ".join(args.query).lower())
                 if w not in STOP and len(w) > 1]
    results = []
    for path in iter_pages(root, args.include_raw):
        try:
            with open(path, encoding="utf-8") as f:
                meta, body = parse_frontmatter(f.read())
        except (OSError, UnicodeDecodeError):
            continue
        if args.type and str(meta.get("type", "")).lower() != args.type.lower():
            continue
        s, matched = score_page(meta, body, q_terms)
        if s <= 0:
            continue
        results.append({
            "path": os.path.relpath(path, args.kb_root).replace(os.sep, "/"),
            "full_path": path,
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
        print(json.dumps({"query_terms": q_terms, "hits": results}, indent=2))
    else:
        if not results:
            print(f"No matches for: {' '.join(args.query)}")
            print("The knowledge base may not cover this yet — consider "
                  "ingesting a source with the kb-ingest skill.")
            return 0
        print(f"Query terms: {', '.join(q_terms)}   ({len(results)} hits)\n")
        for r in results:
            print(f"[{r['score']:>6}] {r['path']}")
            print(f"         {r['type']}: {r['title']}")
            if r["description"]:
                print(f"         {r['description']}")
            print(f"         …{r['snippet']}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
