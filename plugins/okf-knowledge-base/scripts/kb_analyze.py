#!/usr/bin/env python3
"""Find consolidation candidates in the knowledge base: pages whose content
overlaps enough that they may be merged to reduce duplication.

Deterministic and dependency-free. For every concept page it builds a set of
stemmed tokens (title + tags + description + body), finds candidate pairs via an
inverted index (skipping over-common terms), scores each candidate pair with
exact Jaccard similarity, and unions pairs above the threshold into clusters.
Clusters are split into **within-domain** (all members in one (sub-)domain) and
**cross-domain** groups. This is the analysis half of the kb-consolidate skill;
the agent applies semantic judgement and drives the recommend/apply flow.

Usage:
  kb_analyze.py [--kb-root PATH] [--domain SLUG] [--json]
                [--min-similarity 0.4] [--min-shared-terms 4]
                [--max-df-ratio 0.5] [--limit 50] [--include-raw]

Exit codes: 0 ok, 2 no KB / bad path.
"""
import argparse
import json
import os
import sys

from kb_common import find_kb_root, frontmatter, tokenize

RESERVED = {"index.md", "log.md"}


def page_domain(kb_root, page_path):
    """Nearest ancestor directory (relative to kb_root) that holds a domain.md."""
    d = os.path.dirname(page_path)
    root = os.path.abspath(kb_root)
    while True:
        if os.path.isfile(os.path.join(d, "domain.md")):
            rel = os.path.relpath(d, kb_root).replace(os.sep, "/")
            return rel if rel != "." else ""
        parent = os.path.dirname(d)
        if os.path.abspath(d) == root or parent == d:
            return ""
        d = parent


def load_pages(kb_root, scan_root, include_raw):
    pages = []
    for dirpath, _dirs, filenames in os.walk(scan_root):
        parts = set(os.path.relpath(dirpath, scan_root).split(os.sep))
        if not include_raw and "raw" in parts:
            continue
        for fn in sorted(filenames):
            if not fn.endswith(".md") or fn in RESERVED or fn == "domain.md":
                continue
            full = os.path.join(dirpath, fn)
            try:
                text = open(full, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            meta, body = frontmatter(text)
            tags = meta.get("tags", [])
            if isinstance(tags, str):
                tags = [tags] if tags else []
            blob = " ".join([str(meta.get("title", "")), " ".join(tags),
                             str(meta.get("description", "")), body])
            pages.append({
                "path": os.path.relpath(full, kb_root).replace(os.sep, "/"),
                "domain": page_domain(kb_root, full),
                "tokens": set(tokenize(blob)),
                "bytes": len(text.encode("utf-8")),
            })
    pages.sort(key=lambda p: p["path"])
    return pages


class UnionFind:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def candidate_edges(pages, min_sim, min_shared, max_postings):
    postings = {}
    for i, pg in enumerate(pages):
        for t in pg["tokens"]:
            postings.setdefault(t, []).append(i)
    # Count shared terms per candidate pair. Terms whose postings list is huge
    # are skipped only to bound cost on large KBs (an absolute cap, so small KBs
    # — where a duplicated term may appear in most pages — are unaffected).
    shared = {}
    for _t, plist in postings.items():
        if len(plist) < 2 or len(plist) > max_postings:
            continue
        for a in range(len(plist)):
            for b in range(a + 1, len(plist)):
                key = (plist[a], plist[b])
                shared[key] = shared.get(key, 0) + 1
    edges = []
    for (i, j) in sorted(shared):
        if shared[(i, j)] < min_shared:
            continue
        ti, tj = pages[i]["tokens"], pages[j]["tokens"]
        inter = len(ti & tj)
        union = len(ti | tj)
        jac = inter / union if union else 0.0
        if jac >= min_sim:
            edges.append((i, j, jac))
    return edges


def build_clusters(pages, edges):
    uf = UnionFind(len(pages))
    for i, j, _ in edges:
        uf.union(i, j)
    edges_by_root = {}
    for i, j, jac in edges:
        edges_by_root.setdefault(uf.find(i), []).append(jac)
    members_by_root = {}
    for idx in range(len(pages)):
        members_by_root.setdefault(uf.find(idx), []).append(idx)

    clusters = []
    for root, members in members_by_root.items():
        if len(members) < 2:
            continue
        members = sorted(members, key=lambda m: pages[m]["path"])
        jacs = edges_by_root.get(root, [])
        domains = sorted({pages[m]["domain"] for m in members})
        total = sum(pages[m]["bytes"] for m in members)
        biggest = max(pages[m]["bytes"] for m in members)
        clusters.append({
            "members": [pages[m]["path"] for m in members],
            "domains": domains,
            "scope": "within-domain" if len(domains) == 1 else "cross-domain",
            "jaccard_min": round(min(jacs), 3) if jacs else 0.0,
            "jaccard_max": round(max(jacs), 3) if jacs else 0.0,
            "total_bytes": total,
            "est_saving_bytes": total - biggest,
        })
    clusters.sort(key=lambda c: (-c["est_saving_bytes"], c["members"][0]))
    return clusters


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb-root", default=None)
    ap.add_argument("--domain", default=None)
    ap.add_argument("--min-similarity", type=float, default=0.4)
    ap.add_argument("--min-shared-terms", type=int, default=4)
    ap.add_argument("--max-postings", type=int, default=200,
                    help="Skip candidate generation for a term appearing in more "
                         "than this many pages (cost bound on large KBs).")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--include-raw", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    kb_root = find_kb_root(args.kb_root)
    if not kb_root:
        print("ERROR: no knowledge base found. Create one with kb-init-domain.",
              file=sys.stderr)
        return 2
    scan_root = os.path.join(kb_root, args.domain) if args.domain else kb_root
    if not os.path.isdir(scan_root):
        print(f"ERROR: {scan_root} not found.", file=sys.stderr)
        return 2

    pages = load_pages(kb_root, scan_root, args.include_raw)
    edges = candidate_edges(pages, args.min_similarity, args.min_shared_terms,
                            args.max_postings)
    # Within-domain groups come from same-domain edges only; cross-domain groups
    # are components of the full graph that span more than one domain. A page can
    # appear in both (a local twin and a copy in another domain).
    within_edges = [(i, j, w) for (i, j, w) in edges
                    if pages[i]["domain"] == pages[j]["domain"]]
    within = build_clusters(pages, within_edges)[:args.limit]
    cross = [c for c in build_clusters(pages, edges)
             if c["scope"] == "cross-domain"][:args.limit]

    result = {
        "kb_root": kb_root,
        "params": {"min_similarity": args.min_similarity,
                   "min_shared_terms": args.min_shared_terms,
                   "max_postings": args.max_postings},
        "pages_analyzed": len(pages),
        "within_domain": within,
        "cross_domain": cross,
        "summary": {
            "within_domain_groups": len(within),
            "cross_domain_groups": len(cross),
            "est_total_saving_bytes": sum(c["est_saving_bytes"] for c in within + cross),
        },
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_human(result)
    return 0


def _print_human(result):
    print(f"Analyzed {result['pages_analyzed']} pages in {result['kb_root']}")
    s = result["summary"]
    print(f"Within-domain groups: {s['within_domain_groups']}   "
          f"Cross-domain groups: {s['cross_domain_groups']}   "
          f"Est. savings: {s['est_total_saving_bytes']} bytes\n")
    for label, key in (("WITHIN-DOMAIN", "within_domain"),
                       ("CROSS-DOMAIN", "cross_domain")):
        if not result[key]:
            continue
        print(f"== {label} consolidation candidates ==")
        for c in result[key]:
            dom = c["domains"][0] if c["scope"] == "within-domain" else ", ".join(c["domains"])
            print(f"  [{dom}] jaccard {c['jaccard_min']}–{c['jaccard_max']}, "
                  f"~{c['est_saving_bytes']} bytes savings:")
            for m in c["members"]:
                print(f"      - {m}")
        print()
    if not result["within_domain"] and not result["cross_domain"]:
        print("No consolidation candidates above the similarity threshold.")


if __name__ == "__main__":
    raise SystemExit(main())
