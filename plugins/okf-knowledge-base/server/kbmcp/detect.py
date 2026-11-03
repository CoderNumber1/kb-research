"""Ranks or lists KB domains for a topic. Deprecated domains are listed but never routed to."""
import json
import os

from .common import net_round, tokens


def run(index, kb_root, query, list_, limit):
    kb_root_full = os.path.abspath(kb_root)
    domains = _load_domains(index, kb_root_full)

    if not domains:
        return json.dumps({
            "domains": [],
            "note": f"No domains found under {kb_root}. Create one with kb-init-domain.",
        }, ensure_ascii=False)

    if list_ or not query:
        return json.dumps({"kb_root": kb_root, "domains": [
            {"slug": d["slug"], "title": d["title"], "description": d["description"],
             "tags": d["tags"], "status": d["status"]}
            for d in domains
        ]}, ensure_ascii=False)

    q_terms = tokens(query)
    scored = [(d,) + _score(d, q_terms) for d in domains if d["status"] != "deprecated"]
    scored.sort(key=lambda x: (-x[1], x[0]["slug"]))
    ranked = scored[:limit]
    top = ranked[0][1] if len(ranked) >= 1 else 0.0
    runner = ranked[1][1] if len(ranked) >= 2 else 0.0
    if top >= 0.5 and (top - runner) >= 0.2:
        confidence = "high"
    elif top >= 0.25:
        confidence = "medium"
    else:
        confidence = "low"
    recommendation = ranked[0][0]["slug"] if confidence != "low" and ranked else None

    return json.dumps({
        "kb_root": kb_root,
        "query_terms": q_terms,
        "confidence": confidence,
        "recommendation": recommendation,
        "ranking": [
            {"slug": d["slug"], "title": d["title"], "score": net_round(score, 3),
             "matched_terms": matched, "description": d["description"]}
            for d, score, matched in ranked
        ],
    }, ensure_ascii=False)


def _load_domains(index, kb_root_full):
    domains = []
    if not os.path.isdir(kb_root_full):
        return domains
    for page in index.get_pages(kb_root_full):
        if page.name != "domain.md":
            continue
        slug = os.path.relpath(page.dir_full_path, kb_root_full).replace("\\", "/")
        if slug == ".":
            continue
        title = page.fm.get_string("title")
        status = page.fm.get_string("status")
        domains.append({
            "slug": slug,
            "title": title if title != "" else slug,
            "description": page.fm.get_string("description"),
            "tags": page.fm.get_list("tags"),
            "status": status if status != "" else "stable",  # OKF v0.2 §5.4 default
            "strong": page.strong_tokens,
            "weak": page.weak_tokens,
        })
    domains.sort(key=lambda d: d["slug"])
    return domains


def _score(d, q_terms):
    q = set(q_terms)
    if not q:
        return 0.0, []
    strong = sorted(t for t in q if t in d["strong"])
    weak = sorted(t for t in q if t not in d["strong"] and t in d["weak"])
    return (3.0 * len(strong) + 1.0 * len(weak)) / len(q), strong + weak
