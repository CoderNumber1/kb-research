#!/usr/bin/env python3
"""Rank knowledge-base domains by how well they match a source's topic.

Reads every kb/<domain>/domain.md, extracts its description, tags, and title,
and scores each against query terms (keyword overlap, with title/tags/type
weighted higher than free description text). This gives the kb-ingest skill a
deterministic baseline for auto-selecting a target domain; the agent makes the
final call, using semantic judgement the script can't.

Usage:
  detect_domain.py --query "stripe webhook signature verification failed"
  detect_domain.py --list                 # dump all domains + descriptions
  detect_domain.py --query "..." --json    # machine-readable ranking

Exit codes: 0 ok, 2 error, 3 no domains found.
"""
import argparse
import json
import os
import re
import sys

STOP = set("""a an the of to in on for and or but with without into from by as at
is are was were be been being this that these those it its it's you your we our
they their he she his her them us i me my mine ours yours will would can could
should may might must do does did done has have had how what when where why who
whom which whose than then so if else not no yes about over under again further
more most other some such only own same too very just also can't cannot""".split())


# Longest-first suffix list. Crude but consistent: it collapses word families
# (verify/verified/verification, sign/signed/signature, webhook/webhooks) to a
# shared root so keyword overlap between a source and a domain actually lands.
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
    """Return (meta dict, body str). Tolerant, stdlib-only YAML-ish subset."""
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


def load_domains(kb_root: str):
    """Discover every domain in the bundle — any directory holding a domain.md,
    at any depth. Nested sub-domains are returned with a bundle-relative slug
    like 'billing/eu', so ingest can route a source to the most specific match."""
    domains = []
    if not os.path.isdir(kb_root):
        return domains
    for dirpath, _dirnames, filenames in os.walk(kb_root):
        if "domain.md" not in filenames:
            continue
        rel = os.path.relpath(dirpath, kb_root).replace(os.sep, "/")
        if rel == ".":
            continue  # the bundle root is not itself a domain
        dmd = os.path.join(dirpath, "domain.md")
        with open(dmd, encoding="utf-8") as f:
            meta, body = parse_frontmatter(f.read())
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [tags] if tags else []
        domains.append({
            "slug": rel,  # derived from location — authoritative over frontmatter
            "dir": dirpath,
            "title": meta.get("title", rel),
            "description": meta.get("description", ""),
            "tags": tags,
            "status": meta.get("status", "active"),
            # Weighted term bag: strong signals (title/tags) tokenized, plus the
            # description and the domain-page body for broader recall.
            "_strong": tokenize(meta.get("title", "") + " " +
                                " ".join(tags)),
            "_weak": tokenize(meta.get("description", "") + " " + body),
        })
    domains.sort(key=lambda d: d["slug"])
    return domains


def score(domain, q_terms):
    q = set(q_terms)
    if not q:
        return 0.0, []
    strong = set(domain["_strong"])
    weak = set(domain["_weak"])
    hits_strong = q & strong
    hits_weak = (q & weak) - hits_strong
    raw = 3.0 * len(hits_strong) + 1.0 * len(hits_weak)
    matched = sorted(hits_strong) + sorted(hits_weak)
    return raw / len(q), matched  # normalize by query size -> 0..~ range


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="", help="Topic terms distilled from the "
                    "source (title, key entities, keywords).")
    ap.add_argument("--kb-root", default="kb")
    ap.add_argument("--list", action="store_true",
                    help="List all domains and their descriptions, then exit.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()

    domains = load_domains(args.kb_root)
    if not domains:
        msg = f"No domains found under {args.kb_root}/. Create one with the " \
              "kb-init-domain skill."
        print(json.dumps({"domains": [], "note": msg}) if args.json else msg)
        return 3

    if args.list or not args.query:
        out = [{"slug": d["slug"], "title": d["title"],
                "description": d["description"], "tags": d["tags"],
                "status": d["status"]} for d in domains]
        if args.json:
            print(json.dumps({"domains": out}, indent=2))
        else:
            print("Domains:")
            for d in out:
                tg = f"  tags: {', '.join(d['tags'])}" if d["tags"] else ""
                print(f"  - {d['slug']} — {d['title']}: {d['description']}{tg}")
        return 0

    q_terms = tokenize(args.query)
    ranked = []
    for d in domains:
        s, matched = score(d, q_terms)
        ranked.append((s, matched, d))
    ranked.sort(key=lambda x: x[0], reverse=True)
    ranked = ranked[:args.limit]

    top = ranked[0][0] if ranked else 0.0
    runner = ranked[1][0] if len(ranked) > 1 else 0.0
    # Heuristic confidence: needs a real top score and separation from #2.
    if top >= 0.5 and (top - runner) >= 0.2:
        confidence = "high"
    elif top >= 0.25:
        confidence = "medium"
    else:
        confidence = "low"

    result = {
        "query_terms": q_terms,
        "confidence": confidence,
        "recommendation": ranked[0][2]["slug"] if confidence != "low" and ranked
                          else None,
        "ranking": [{"slug": d["slug"], "title": d["title"],
                     "score": round(s, 3), "matched_terms": matched,
                     "description": d["description"]}
                    for s, matched, d in ranked],
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Query terms: {', '.join(q_terms) or '(none)'}")
        print(f"Confidence: {confidence}"
              + (f"  ->  recommend '{result['recommendation']}'"
                 if result["recommendation"] else "  ->  no clear match"))
        print("Ranking:")
        for r in result["ranking"]:
            print(f"  {r['score']:>5}  {r['slug']:<20} "
                  f"matched: {', '.join(r['matched_terms']) or '-'}")
        if confidence == "low":
            print("\nNo confident match. Consider asking the user, or creating a "
                  "new domain with the kb-init-domain skill.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
