#!/usr/bin/env python3
"""Lint the knowledge base for OKF conformance and LLM-wiki hygiene.

Two tiers of findings:
  * ERROR   — OKF v0.1 conformance failures (§9): a non-reserved .md without
              parseable frontmatter, or without a non-empty `type`; frontmatter
              in a non-root index.md.
  * WARNING / INFO — wiki-health issues the OKF spec tolerates but that degrade
              a knowledge base over time: broken cross-links, orphaned pages,
              index drift, missing recommended fields, non-ISO log dates, stale
              pages, duplicate titles/resources.

Usage:
  kb_lint.py                       # lint kb/, human-readable report
  kb_lint.py --kb-root kb --json   # machine-readable
  kb_lint.py --domain billing      # lint one domain
  kb_lint.py --stale-days 365      # flag pages older than N days (default off)
  kb_lint.py --fix-index           # regenerate index.md concept lists in place

Exit code: 0 if no ERRORs, 1 if any ERROR, 2 on bad invocation.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

RESERVED = {"index.md", "log.md"}
RECOMMENDED = ["title", "description", "timestamp"]
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def parse_frontmatter(text: str):
    """Return (meta, body, ok, err). ok=False means unparseable/missing FM."""
    if not text.startswith("---"):
        return {}, text, False, "no frontmatter block"
    lines = text.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text, False, "unterminated frontmatter block"
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
        else:
            return {}, "\n".join(lines[end + 1:]), False, \
                f"unparseable frontmatter line: {raw!r}"
    return meta, "\n".join(lines[end + 1:]), True, ""


def _scalar(v: str):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


class Finding:
    __slots__ = ("level", "code", "path", "msg")

    def __init__(self, level, code, path, msg):
        self.level, self.code, self.path, self.msg = level, code, path, msg

    def as_dict(self):
        return {"level": self.level, "code": self.code,
                "path": self.path, "msg": self.msg}


def rel(kb_root, path):
    return os.path.relpath(path, kb_root).replace(os.sep, "/")


def resolve_link(target, page_path, kb_root):
    """Resolve an OKF cross-link to a filesystem path, or None if external."""
    t = target.split("#")[0].strip()
    if not t or re.match(r"^[a-z][a-z0-9+.-]*://", t) or t.startswith("mailto:"):
        return None  # external / anchor-only
    if t.startswith("/"):
        return os.path.normpath(os.path.join(kb_root, t.lstrip("/")))
    return os.path.normpath(os.path.join(os.path.dirname(page_path), t))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb-root", default="kb")
    ap.add_argument("--domain", default=None)
    ap.add_argument("--stale-days", type=int, default=0,
                    help="Flag pages whose timestamp is older than N days (0=off).")
    ap.add_argument("--fix-index", action="store_true",
                    help="Regenerate the '# Concepts' list in each index.md.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    scan_root = args.kb_root
    if args.domain:
        scan_root = os.path.join(args.kb_root, args.domain)
    if not os.path.isdir(scan_root):
        print(f"ERROR: {scan_root} not found.", file=sys.stderr)
        return 2

    findings = []
    concept_pages = {}   # full_path -> meta
    all_md = []          # every .md path
    titles = {}          # title -> [paths]
    resources = {}       # resource -> [paths]
    link_targets = set() # resolved existing concept paths that are linked to
    dir_children = {}    # dir -> set of concept filenames (for index drift)

    for dirpath, _, filenames in os.walk(scan_root):
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dirpath, fn)
            all_md.append(full)
            with open(full, encoding="utf-8") as f:
                text = f.read()

            if fn in RESERVED:
                _lint_reserved(fn, full, text, args.kb_root, findings)
                continue

            meta, body, ok, err = parse_frontmatter(text)
            r = rel(args.kb_root, full)
            if not ok:
                findings.append(Finding("ERROR", "frontmatter", r,
                                        f"missing/unparseable frontmatter: {err}"))
                continue
            if not str(meta.get("type", "")).strip():
                findings.append(Finding("ERROR", "type", r,
                                        "frontmatter missing a non-empty `type`"))
            concept_pages[full] = meta
            dir_children.setdefault(dirpath, set()).add(fn)

            for field in RECOMMENDED:
                if not str(meta.get(field, "")).strip():
                    findings.append(Finding("INFO", "recommended", r,
                                            f"missing recommended field `{field}`"))

            t = meta.get("title")
            if t:
                titles.setdefault(t, []).append(r)
            res = meta.get("resource")
            if res:
                resources.setdefault(res, []).append(r)

            if args.stale_days and meta.get("timestamp"):
                _check_stale(meta["timestamp"], r, args.stale_days, findings)

            # Cross-links.
            for m in LINK_RE.finditer(body):
                target = m.group(1)
                resolved = resolve_link(target, full, args.kb_root)
                if resolved is None:
                    continue
                if os.path.exists(resolved):
                    link_targets.add(os.path.normpath(resolved))
                else:
                    findings.append(Finding("WARNING", "broken-link", r,
                                            f"link target does not exist: {target}"))

    # Orphans: concept pages nothing links to (and not a domain.md/index anchor).
    for full, meta in concept_pages.items():
        base = os.path.basename(full)
        if base in ("domain.md",):
            continue
        if os.path.normpath(full) not in link_targets:
            findings.append(Finding("WARNING", "orphan", rel(args.kb_root, full),
                                    "no other page links here (orphaned)"))

    # Duplicate titles / resources.
    for t, paths in titles.items():
        if len(paths) > 1:
            findings.append(Finding("WARNING", "dup-title", paths[0],
                                    f"title {t!r} shared by: {', '.join(paths)}"))
    for res, paths in resources.items():
        if len(paths) > 1:
            findings.append(Finding("WARNING", "dup-resource", paths[0],
                                    f"resource {res!r} shared by: {', '.join(paths)}"))

    # Index drift + optional regeneration.
    _lint_indexes(scan_root, args.kb_root, dir_children, concept_pages,
                  findings, args.fix_index)

    return _report(findings, args)


def _lint_reserved(fn, full, text, kb_root, findings):
    r = rel(kb_root, full)
    meta, _, ok, _ = parse_frontmatter(text)
    if fn == "index.md":
        is_root = os.path.dirname(os.path.normpath(full)) == os.path.normpath(kb_root)
        if ok and meta:
            allowed = is_root and set(meta) <= {"okf_version"}
            if not allowed:
                findings.append(Finding("ERROR", "index-frontmatter", r,
                    "index.md must not carry frontmatter (except okf_version in "
                    "the bundle-root index.md) — OKF §6/§11"))
    elif fn == "log.md":
        for line in text.split("\n"):
            if line.startswith("## "):
                if not ISO_DATE.match(line[3:].strip()):
                    findings.append(Finding("WARNING", "log-date", r,
                        f"log heading is not ISO YYYY-MM-DD: {line.strip()!r}"))


def _check_stale(ts, r, stale_days, findings):
    try:
        s = str(ts).replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(s)
        if parsed.tzinfo:
            parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
        age = (dt.datetime.utcnow() - parsed).days
        if age > stale_days:
            findings.append(Finding("INFO", "stale", r,
                                    f"last updated {age} days ago"))
    except (ValueError, TypeError):
        findings.append(Finding("WARNING", "timestamp", r,
                                f"unparseable timestamp: {ts!r}"))


def _lint_indexes(scan_root, kb_root, dir_children, concept_pages, findings, fix):
    for dirpath, children in dir_children.items():
        # concepts that should appear in this dir's index (exclude domain.md self
        # and reserved files)
        concepts = sorted(c for c in children if c not in RESERVED)
        index_path = os.path.join(dirpath, "index.md")
        listed = set()
        if os.path.isfile(index_path):
            with open(index_path, encoding="utf-8") as f:
                itext = f.read()
            for m in LINK_RE.finditer(itext):
                tgt = m.group(1).split("#")[0].strip().rstrip("/")
                listed.add(os.path.basename(tgt))
        missing = [c for c in concepts if c not in listed and c != "domain.md"]
        if missing and os.path.isfile(index_path):
            findings.append(Finding("WARNING", "index-drift",
                rel(kb_root, index_path),
                f"index.md omits: {', '.join(missing)}"))
        if fix and os.path.isfile(index_path):
            _regenerate_index(index_path, concepts, concept_pages, dirpath)


def _regenerate_index(index_path, concepts, concept_pages, dirpath):
    lines = ["", "# Concepts", ""]
    for c in concepts:
        if c == "domain.md":
            continue
        meta = concept_pages.get(os.path.join(dirpath, c), {})
        title = meta.get("title") or c[:-3]
        desc = meta.get("description", "")
        lines.append(f"* [{title}]({c})" + (f" - {desc}" if desc else ""))
    block = "\n".join(lines) + "\n"
    with open(index_path, encoding="utf-8") as f:
        text = f.read()
    if "# Concepts" in text:
        head, _, rest = text.partition("# Concepts")
        # Cut until the next top-level heading after the Concepts section.
        after = ""
        nl = rest.find("\n# ")
        if nl != -1:
            after = rest[nl:]
        text = head.rstrip() + "\n" + block + after
    else:
        text = text.rstrip() + "\n" + block
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(text)


def _report(findings, args):
    order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    findings.sort(key=lambda f: (order[f.level], f.code, f.path))
    counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
    for f in findings:
        counts[f.level] += 1

    if args.json:
        print(json.dumps({
            "summary": counts,
            "conformant": counts["ERROR"] == 0,
            "findings": [f.as_dict() for f in findings],
        }, indent=2))
    else:
        if not findings:
            print("✓ Knowledge base is clean — OKF-conformant, no hygiene issues.")
        else:
            for f in findings:
                print(f"{f.level:<7} [{f.code}] {f.path}\n         {f.msg}")
            print()
            print(f"Summary: {counts['ERROR']} error(s), "
                  f"{counts['WARNING']} warning(s), {counts['INFO']} info.")
            print("OKF-conformant." if counts["ERROR"] == 0
                  else "NOT OKF-conformant — fix the errors above.")
    return 1 if counts["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
