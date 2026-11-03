"""OKF v0.2 concept-page conformance plus wiki-hygiene lint."""
import json
import os
import re
from datetime import datetime, timezone

from .common import KbError, as_string, is_raw_artifact, is_under, path_key, pyrepr, read_text, rel, write_text

RESERVED = {"index.md", "log.md"}
RECOMMENDED = ("title", "description")
STATUSES = {"draft", "stable", "deprecated"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FOOTNOTE_RE = re.compile(r"\[\^([^\]\s]+)\]")
CITATIONS_HEADING = re.compile(r"^#\s+Citations\s*$", re.M)
# Fenced blocks and inline code spans hold examples, not live links or footnotes.
CODE_RE = re.compile(r"^(```|~~~).*?^\1[^\n]*$|`[^`\n]+`", re.M | re.S)
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$")
SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)
RANK = {"ERROR": 0, "WARNING": 1, "INFO": 2}


def run(index, kb_root, domain, fix_index, stale_days):
    kb_root_full = os.path.abspath(kb_root)
    scan_root = os.path.join(kb_root_full, domain) if domain is not None else kb_root_full
    if not os.path.isdir(scan_root):
        raise KbError(f"ERROR: {scan_root} not found.")
    scan_root_full = os.path.abspath(scan_root)
    now = datetime.now(timezone.utc)

    findings = []

    def add(level, code, path, msg):
        findings.append((level, code, path, msg, len(findings)))

    concept_by_key = {}  # path_key -> page
    titles, resources = {}, {}
    link_targets = set()  # path_keys
    dir_children = {}  # dir path_key -> (dir, set of names)

    pages = sorted((p for p in index.get_pages(kb_root_full) if is_under(scan_root_full, p.full_path)),
                   key=lambda p: p.full_path)

    for page in pages:
        full, fm = page.full_path, page.fm
        # The Raw Source Archive is user-owned and opaque to lint.
        if is_raw_artifact(kb_root_full, full):
            continue
        r = rel(kb_root_full, full)
        if page.is_reserved:
            _lint_reserved(page, kb_root_full, r, add)
            continue
        if not fm.ok:
            add("ERROR", "frontmatter", r, "missing/unparseable frontmatter: " + fm.err)
            continue
        if fm.get_string("type").strip() == "":
            add("ERROR", "type", r, "frontmatter missing a non-empty `type`")

        concept_by_key[path_key(full)] = page
        dir_children.setdefault(path_key(page.dir_full_path), (page.dir_full_path, set()))[1].add(page.name)

        for field in RECOMMENDED:
            if fm.get_string(field).strip() == "":
                add("INFO", "recommended", r, f"missing recommended field `{field}`")

        title = fm.get_string("title")
        if title != "":
            titles.setdefault(title, []).append(r)
        resource = fm.get_string("resource")
        if resource != "":
            resources.setdefault(resource, []).append(r)

        _lint_lifecycle(fm, r, now, stale_days, add)
        _lint_trust(fm, r, add)
        prose = CODE_RE.sub("", fm.body)
        source_ids = _lint_sources(fm, page, kb_root_full, r, link_targets, add)
        _lint_footnotes(fm, prose, source_ids, r, add)

        # A link asserts a relationship only when it comes from a concept page:
        # domain.md routing/entry-point links never resolve an orphan.
        counts_for_graph = page.name != "domain.md"
        for m in LINK_RE.finditer(prose):
            target = m.group(1)
            resolved = _resolve(target, full, kb_root_full)
            if resolved is None:
                continue
            if is_under(kb_root_full, resolved) and is_raw_artifact(kb_root_full, resolved):
                add("WARNING", "raw-link", r,
                    f"body links into the Raw Source Archive ({target}); cite it from `sources` instead")
                continue
            if os.path.exists(resolved):
                if counts_for_graph:
                    link_targets.add(path_key(resolved))
            else:
                add("WARNING", "broken-link", r, f"link target does not exist: {target}")

    for key, page in concept_by_key.items():
        if page.name == "domain.md":
            continue
        if key not in link_targets:
            add("WARNING", "orphan", rel(kb_root_full, page.full_path), "no concept page links here (orphaned)")

    for t, ps in titles.items():
        if len(ps) > 1:
            ps = sorted(ps)
            add("WARNING", "dup-title", ps[0], "title " + pyrepr(t) + " shared by: " + ", ".join(ps))
    for res, ps in resources.items():
        if len(ps) > 1:
            ps = sorted(ps)
            add("WARNING", "dup-resource", ps[0], "resource " + pyrepr(res) + " shared by: " + ", ".join(ps))

    wrote = False
    for d, children in dir_children.values():
        concepts = sorted(c for c in children if c not in RESERVED and c != "domain.md")
        index_path = os.path.join(d, "index.md")
        exists = os.path.isfile(index_path)
        listed = set()
        if exists:
            for m in LINK_RE.finditer(read_text(index_path)):
                listed.add(os.path.basename(m.group(1).split("#")[0].strip().rstrip("/")))
        missing = [c for c in concepts if c not in listed]
        if missing and exists:
            add("WARNING", "index-drift", rel(kb_root_full, index_path), "index.md omits: " + ", ".join(missing))
        if fix_index and exists:
            _rewrite_index(index_path, d, concepts, concept_by_key)
            wrote = True
    if wrote:
        index.invalidate(kb_root_full)

    counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
    for f in findings:
        counts[f[0]] += 1
    findings.sort(key=lambda f: (RANK[f[0]], f[1], f[2], f[4]))
    result = {
        "summary": counts,
        "conformant": counts["ERROR"] == 0,
        "findings": [{"level": f[0], "code": f[1], "path": f[2], "msg": f[3]} for f in findings],
    }
    return json.dumps(result, ensure_ascii=False)


def _lint_reserved(page, kb_root_full, r, add):
    fm = page.fm
    if page.name == "index.md":
        is_root = path_key(os.path.dirname(page.full_path)) == path_key(kb_root_full)
        only_okf = all(k == "okf_version" for k in fm.meta)
        if fm.ok and len(fm.meta) > 0 and not (is_root and only_okf):
            add("ERROR", "index-frontmatter", r,
                "index.md must not carry frontmatter (except okf_version in the bundle-root index.md)")
        if is_root and fm.ok and fm.has("okf_version") and fm.get_string("okf_version") != "0.2":
            add("INFO", "okf-version", r,
                f"bundle declares okf_version {pyrepr(fm.get_string('okf_version'))}; this plugin targets 0.2")
    elif page.name == "log.md":
        for line in page.raw_text.split("\n"):
            if line.startswith("## ") and not ISO_DATE.match(line[3:].strip()):
                add("WARNING", "log-date", r, "log heading is not ISO YYYY-MM-DD: " + pyrepr(line.strip()))


def _lint_lifecycle(fm, r, now, stale_days, add):
    if fm.has("status") and fm.get_string("status") not in STATUSES:
        add("WARNING", "status", r, f"status {pyrepr(fm.get_string('status'))} is not one of draft, stable, deprecated")

    if fm.has("stale_after"):
        raw = fm.get_string("stale_after")
        stale_after = _instant(raw)
        if stale_after is None:
            add("WARNING", "datetime", r, "stale_after is not an ISO 8601 datetime with a UTC offset: " + pyrepr(raw))
        elif now >= stale_after:
            add("INFO", "stale", r, f"stale since {raw} (stale_after)")

    # Freshness: v0.2 generated.at, falling back to the legacy v0.1 timestamp.
    gen = fm.raw("generated")
    generated_at = as_string(gen.get("at")) if isinstance(gen, dict) else ""
    legacy = fm.get_string("timestamp")
    if not fm.has("generated"):
        if legacy != "":
            add("INFO", "legacy", r, "uses the v0.1 `timestamp`; v0.2 records it as `generated: { by, at }`")
        else:
            add("INFO", "recommended", r, "missing recommended field `generated`")
    if legacy != "" and _legacy_instant(legacy) is None:
        add("WARNING", "timestamp", r, "unparseable timestamp: " + pyrepr(legacy))

    if stale_days != 0:
        basis = generated_at if generated_at != "" else legacy
        changed = _legacy_instant(basis) if basis != "" else None
        if changed is not None:
            age = int((now - changed).total_seconds() // 86400)
            if age > stale_days:
                add("INFO", "stale", r, f"last changed {age} days ago")


def _lint_trust(fm, r, add):
    if fm.has("generated"):
        gen = fm.raw("generated")
        if not isinstance(gen, dict):
            add("WARNING", "generated", r, "`generated` must be a mapping with `by` (and usually `at`)")
        else:
            if as_string(gen.get("by")).strip() == "":
                add("WARNING", "generated", r, "`generated.by` is required (an actor, e.g. agent/model or human:<id>)")
            at = as_string(gen.get("at"))
            if at != "" and _instant(at) is None:
                add("WARNING", "datetime", r, "generated.at is not an ISO 8601 datetime with a UTC offset: " + pyrepr(at))

    if fm.has("verified"):
        raw = fm.raw("verified")
        # A bare mapping is a one-element list (OKF v0.2 §5.2).
        for ev in (raw if isinstance(raw, list) else [raw]):
            if not isinstance(ev, dict):
                add("WARNING", "verified", r, "each `verified` entry must be a mapping with `by` and `at`")
                continue
            if as_string(ev.get("by")).strip() == "":
                add("WARNING", "verified", r, "a `verified` entry is missing `by`")
            at = as_string(ev.get("at"))
            if at == "":
                add("WARNING", "verified", r, "a `verified` entry is missing `at`")
            elif _instant(at) is None:
                add("WARNING", "datetime", r, "verified.at is not an ISO 8601 datetime with a UTC offset: " + pyrepr(at))


def _lint_sources(fm, page, kb_root_full, r, link_targets, add):
    ids = set()
    if not fm.has("sources"):
        return ids
    entries = fm.raw("sources")
    if not isinstance(entries, list):
        add("WARNING", "sources", r, "`sources` must be a list of entries")
        return ids
    for entry in entries:
        if not isinstance(entry, dict):
            add("WARNING", "sources", r, "each `sources` entry must be a mapping with `resource`")
            continue
        sid = as_string(entry.get("id"))
        if sid != "":
            if sid in ids:
                add("WARNING", "sources", r, f"duplicate sources id {pyrepr(sid)}")
            ids.add(sid)
        res = as_string(entry.get("resource")).strip()
        if res == "":
            add("WARNING", "sources", r, "a `sources` entry is missing `resource`")
            continue
        last_modified = as_string(entry.get("last_modified"))
        if last_modified != "" and _instant(last_modified) is None:
            add("WARNING", "datetime", r,
                "sources.last_modified is not an ISO 8601 datetime with a UTC offset: " + pyrepr(last_modified))
        # A resource is a path only when it looks like one; otherwise it is a
        # URL or a scope descriptor (e.g. "conversation on 2026-10-26").
        if not _looks_like_path(res):
            continue
        resolved = _resolve(res, page.full_path, kb_root_full)
        if resolved is None:
            continue
        if not os.path.exists(resolved):
            add("WARNING", "broken-source", r, f"sources resource does not exist: {res}")
        elif page.name != "domain.md" and not is_raw_artifact(kb_root_full, resolved):
            link_targets.add(path_key(resolved))  # lineage edge (OKF v0.2 §5.1)
    return ids


def _lint_footnotes(fm, prose, source_ids, r, add):
    reported = set()
    for m in FOOTNOTE_RE.finditer(prose):
        label = m.group(1)
        if label not in source_ids and label not in reported:
            reported.add(label)
            add("WARNING", "footnote", r, f"footnote [^{label}] has no matching `sources` id")
    if not fm.has("sources") and CITATIONS_HEADING.search(fm.body):
        add("INFO", "legacy", r, "uses a v0.1 `# Citations` list; v0.2 records provenance in `sources` with [^id] footnotes")


def _parse_iso(value):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _instant(value):
    """A v0.2 datetime: ISO 8601 with an explicit UTC offset."""
    return _parse_iso(value) if ISO_INSTANT.match(value) else None


def _legacy_instant(value):
    """A lenient legacy datetime; a missing offset means UTC."""
    return _parse_iso(value.strip())


def _looks_like_path(value):
    return (not SCHEME_RE.match(value) and " " not in value
            and (value.startswith(("/", "./", "../")) or value.lower().endswith(".md")))


def _resolve(target, page_path, kb_root_full):
    t = target.split("#")[0].strip()
    if t == "" or SCHEME_RE.match(t) or t.startswith("mailto:"):
        return None
    if t.startswith("/"):
        return os.path.abspath(os.path.join(kb_root_full, t.lstrip("/")))
    return os.path.abspath(os.path.join(os.path.dirname(page_path), t))


def _rewrite_index(index_path, d, concepts, concept_by_key):
    lines = ["", "# Concepts", ""]
    for c in concepts:
        page = concept_by_key.get(path_key(os.path.join(d, c)))
        title = page.fm.get_string("title") if page is not None else ""
        title = title if title != "" else c[:-3]
        desc = page.fm.get_string("description") if page is not None else ""
        lines.append(f"* [{title}]({c})" + (f" - {desc}" if desc != "" else ""))
    block = "\n".join(lines) + "\n"
    text = read_text(index_path)
    if "# Concepts" in text:
        at = text.index("# Concepts")
        head, rest = text[:at], text[at:]
        nl = rest.find("\n# ")
        tail = rest[nl:] if nl >= 0 else ""
        text = head.rstrip() + "\n" + block + tail
    else:
        text = text.rstrip() + "\n" + block
    write_text(index_path, text)
