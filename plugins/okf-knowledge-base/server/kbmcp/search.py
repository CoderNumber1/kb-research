"""Ranked concept-page search with snippets."""
import json
import os

from .common import KbError, is_raw_artifact, is_under, net_round, raw_words, tokens


def run(index, kb_root, query, domain, type_, limit, include_raw):
    kb_root_full = os.path.abspath(kb_root)
    scan_root = os.path.join(kb_root_full, domain) if domain is not None else kb_root_full
    if not os.path.isdir(scan_root):
        raise KbError(f"ERROR: {scan_root} not found.")
    scan_root_full = os.path.abspath(scan_root)

    q_terms = tokens(query)
    unique_q = list(dict.fromkeys(q_terms))
    words = raw_words(query)

    hits = []
    for page in index.get_pages(kb_root_full):
        if page.is_reserved or not is_under(scan_root_full, page.full_path):
            continue
        if is_raw_artifact(kb_root_full, page.full_path) and not include_raw:
            continue
        if type_ is not None and page.fm.get_string("type").lower() != type_.lower():
            continue
        score, matched = _score(page, unique_q)
        if score <= 0:
            continue
        title = page.fm.get_string("title")
        rounded = net_round(score, 2)
        hits.append((rounded, page.rel_path, {
            "path": page.rel_path,
            "title": title if title != "" else page.name[:-3],
            "type": page.fm.get_string("type"),
            "description": page.fm.get_string("description"),
            "score": rounded,
            "matched_terms": matched,
            "snippet": _snippet(page.fm.body, words),
        }))

    hits.sort(key=lambda h: (-h[0], h[1]))
    return json.dumps({
        "kb_root": kb_root,
        "query_terms": q_terms,
        "hits": [h[2] for h in hits[:limit]],
    }, ensure_ascii=False)


def _score(page, unique_q):
    matched = {}
    if not unique_q:
        return 0.0, matched
    total, matched_count = 0.0, 0
    for t in unique_q:
        s = 0.0
        if t in page.title_tokens:
            s += 6.0
        if t in page.tag_tokens:
            s += 4.0
        if t in page.type_tokens:
            s += 3.0
        if t in page.desc_tokens:
            s += 3.0
        c = page.body_token_counts.get(t)
        if c:
            s += 1.0 + 0.3 * min(c - 1, 5)
        if s > 0:
            matched[t] = net_round(s, 2)
            total += s
            matched_count += 1
    coverage = matched_count / len(unique_q)
    return total * (0.5 + 0.5 * coverage), matched


# Snippet windows are measured in UTF-16 code units, as .NET strings are, so an
# emoji (two units) shifts the window exactly as it does in the C# server.

def _utf16(s):
    return s.encode("utf-16-le", "surrogatepass")


def _cut16(b, start, end):
    return b[start * 2:end * 2].decode("utf-16-le", "replace")


def _find16(haystack, needle):
    i = haystack.find(needle)
    while i >= 0 and i % 2:
        i = haystack.find(needle, i + 1)
    return i // 2 if i >= 0 else -1


def _snippet(body, words, width=160):
    body16 = _utf16(body)
    n = len(body16) // 2
    # Per-character lowering keeps indices aligned (like .NET ToLowerInvariant).
    low16 = _utf16("".join(c.lower() if len(c.lower()) == 1 else c for c in body))
    for w in words:
        i = _find16(low16, _utf16(w))
        if i >= 0:
            start = max(0, i - width // 2)
            end = min(n, i + width // 2)
            frag = _cut16(body16, start, end).replace("\n", " ").strip()
            return ("…" if start != 0 else "") + frag + ("…" if end < n else "")
    flat16 = _utf16(body.replace("\n", " ").strip())
    return _cut16(flat16, 0, width) if len(flat16) // 2 > width else flat16.decode("utf-16-le", "replace")
