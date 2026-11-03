"""Consolidation-candidate clustering over concept pages."""
import json
import os
import re

from .common import KbError, is_under, net_round


def run(index, kb_root, min_sim, min_shared, max_postings, limit, include_raw, domain):
    kb_root_full = os.path.abspath(kb_root)
    scan_root = os.path.join(kb_root_full, domain) if domain is not None else kb_root_full
    if not os.path.isdir(scan_root):
        raise KbError(f"ERROR: {scan_root} not found.")
    scan_root_full = os.path.abspath(scan_root)

    pages = _load_pages(index, kb_root_full, scan_root_full, include_raw)
    edges = _candidate_edges(pages, min_sim, min_shared, max_postings)
    within_edges = [e for e in edges if pages[e[0]]["domain"] == pages[e[1]]["domain"]]
    within = _clusters(pages, within_edges)[:limit]
    cross = [c for c in _clusters(pages, edges) if c["scope"] == "cross-domain"][:limit]

    return json.dumps({
        "kb_root": kb_root,
        "params": {"min_similarity": min_sim, "min_shared_terms": min_shared, "max_postings": max_postings},
        "pages_analyzed": len(pages),
        "within_domain": within,
        "cross_domain": cross,
        "summary": {
            "within_domain_groups": len(within),
            "cross_domain_groups": len(cross),
            "est_total_saving_bytes": sum(c["est_saving_bytes"] for c in within + cross),
        },
    }, ensure_ascii=False)


def _load_pages(index, kb_root_full, scan_root_full, include_raw):
    pages = []
    for page in index.get_pages(kb_root_full):
        if page.is_reserved or page.name == "domain.md":
            continue
        if not is_under(scan_root_full, page.full_path):
            continue
        rel_dir = os.path.relpath(page.dir_full_path, scan_root_full)
        if not include_raw and "raw" in re.split(r"[\\/]", rel_dir):
            continue
        pages.append({
            "path": page.rel_path,
            "domain": _page_domain(kb_root_full, page.full_path),
            "tokens": page.blob_tokens,
            "bytes": page.byte_count,
        })
    pages.sort(key=lambda p: p["path"])
    return pages


def _page_domain(kb_root_full, page_path):
    """Nearest ancestor directory (relative to the root) that holds a domain.md."""
    d = os.path.dirname(page_path)
    root = os.path.abspath(kb_root_full)
    while True:
        if os.path.isfile(os.path.join(d, "domain.md")):
            r = os.path.relpath(d, kb_root_full).replace("\\", "/")
            return "" if r == "." else r
        parent = os.path.dirname(d)
        if os.path.abspath(d) == root or not parent or parent == d:
            return ""
        d = parent


def _candidate_edges(pages, min_sim, min_shared, max_postings):
    postings = {}
    for i, p in enumerate(pages):
        for t in p["tokens"]:
            postings.setdefault(t, []).append(i)
    shared = {}
    for plist in postings.values():
        if len(plist) < 2 or len(plist) > max_postings:
            continue
        for a in range(len(plist)):
            for b in range(a + 1, len(plist)):
                key = (plist[a], plist[b])
                shared[key] = shared.get(key, 0) + 1
    edges = []
    for (i, j), count in shared.items():
        if count < min_shared:
            continue
        ti, tj = pages[i]["tokens"], pages[j]["tokens"]
        inter = len(ti & tj)
        union = len(ti) + len(tj) - inter
        jac = inter / union if union else 0.0
        if jac >= min_sim:
            edges.append((i, j, jac))
    return edges


def _clusters(pages, edges):
    parent = list(range(max(len(pages), 1)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j, _ in edges:
        ra, rb = find(i), find(j)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    jac_by_root, members_by_root = {}, {}
    for i, _, jac in edges:
        jac_by_root.setdefault(find(i), []).append(jac)
    for idx in range(len(pages)):
        members_by_root.setdefault(find(idx), []).append(idx)

    clusters = []
    for r, members in members_by_root.items():
        if len(members) < 2:
            continue
        members = sorted(members, key=lambda m: pages[m]["path"])
        jacs = jac_by_root.get(r, [])
        domains = sorted({pages[m]["domain"] for m in members})
        total = sum(pages[m]["bytes"] for m in members)
        biggest = max(pages[m]["bytes"] for m in members)
        clusters.append({
            "members": [pages[m]["path"] for m in members],
            "domains": domains,
            "scope": "within-domain" if len(domains) == 1 else "cross-domain",
            "jaccard_min": net_round(min(jacs), 3) if jacs else 0.0,
            "jaccard_max": net_round(max(jacs), 3) if jacs else 0.0,
            "total_bytes": total,
            "est_saving_bytes": total - biggest,
        })
    clusters.sort(key=lambda c: (-c["est_saving_bytes"], c["members"][0]))
    return clusters
