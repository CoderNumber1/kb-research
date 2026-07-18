#!/usr/bin/env python3
"""Lint the knowledge base for OKF conformance and LLM-wiki hygiene.

ERROR   = OKF v0.1 conformance failures (§9): a non-reserved .md without
          parseable frontmatter or without a non-empty `type`; frontmatter in a
          non-root index.md.
WARNING / INFO = hygiene the spec tolerates but that degrades a KB over time:
          broken cross-links, orphaned pages, index drift, missing recommended
          fields, non-ISO log dates, duplicates, stale pages.

The KB root is resolved from --kb-root, else $KB_ROOT, else the working
directory.

Usage:
  kb_lint.py [--kb-root PATH] [--domain SLUG] [--json]
             [--stale-days N] [--fix-index]

Exit code: 0 if no ERRORs, 1 if any ERROR, 2 on bad invocation / no KB.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

from kb_common import find_kb_root, parse_frontmatter

RESERVED = {"index.md", "log.md"}
RECOMMENDED = ["title", "description", "timestamp"]
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


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
    t = target.split("#")[0].strip()
    if not t or re.match(r"^[a-z][a-z0-9+.-]*://", t) or t.startswith("mailto:"):
        return None
    if t.startswith("/"):
        return os.path.normpath(os.path.join(kb_root, t.lstrip("/")))
    return os.path.normpath(os.path.join(os.path.dirname(page_path), t))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb-root", default=None)
    ap.add_argument("--domain", default=None)
    ap.add_argument("--stale-days", type=int, default=0)
    ap.add_argument("--fix-index", action="store_true")
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

    findings = []
    concept_pages, titles, resources = {}, {}, {}
    link_targets, dir_children = set(), {}

    for dirpath, _dirs, filenames in os.walk(scan_root):
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dirpath, fn)
            with open(full, encoding="utf-8") as f:
                text = f.read()

            if fn in RESERVED:
                _lint_reserved(fn, full, text, kb_root, findings)
                continue

            meta, body, ok, err = parse_frontmatter(text)
            r = rel(kb_root, full)
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

            if meta.get("title"):
                titles.setdefault(meta["title"], []).append(r)
            if meta.get("resource"):
                resources.setdefault(meta["resource"], []).append(r)

            if args.stale_days and meta.get("timestamp"):
                _check_stale(meta["timestamp"], r, args.stale_days, findings)

            for m in LINK_RE.finditer(body):
                resolved = resolve_link(m.group(1), full, kb_root)
                if resolved is None:
                    continue
                if os.path.exists(resolved):
                    link_targets.add(os.path.normpath(resolved))
                else:
                    findings.append(Finding("WARNING", "broken-link", r,
                                    f"link target does not exist: {m.group(1)}"))

    for full in concept_pages:
        if os.path.basename(full) == "domain.md":
            continue
        if os.path.normpath(full) not in link_targets:
            findings.append(Finding("WARNING", "orphan", rel(kb_root, full),
                                    "no other page links here (orphaned)"))

    for t, paths in titles.items():
        if len(paths) > 1:
            findings.append(Finding("WARNING", "dup-title", paths[0],
                                    f"title {t!r} shared by: {', '.join(paths)}"))
    for res, paths in resources.items():
        if len(paths) > 1:
            findings.append(Finding("WARNING", "dup-resource", paths[0],
                                f"resource {res!r} shared by: {', '.join(paths)}"))

    _lint_indexes(kb_root, dir_children, concept_pages, findings, args.fix_index)
    return _report(findings, args)


def _lint_reserved(fn, full, text, kb_root, findings):
    r = rel(kb_root, full)
    meta, _, ok, _ = parse_frontmatter(text)
    if fn == "index.md":
        is_root = os.path.dirname(os.path.normpath(full)) == os.path.normpath(kb_root)
        if ok and meta and not (is_root and set(meta) <= {"okf_version"}):
            findings.append(Finding("ERROR", "index-frontmatter", r,
                "index.md must not carry frontmatter (except okf_version in the "
                "bundle-root index.md) — OKF §6/§11"))
    elif fn == "log.md":
        for line in text.split("\n"):
            if line.startswith("## ") and not ISO_DATE.match(line[3:].strip()):
                findings.append(Finding("WARNING", "log-date", r,
                    f"log heading is not ISO YYYY-MM-DD: {line.strip()!r}"))


def _check_stale(ts, r, stale_days, findings):
    try:
        parsed = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if parsed.tzinfo:
            parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
        age = (dt.datetime.utcnow() - parsed).days
        if age > stale_days:
            findings.append(Finding("INFO", "stale", r,
                                    f"last updated {age} days ago"))
    except (ValueError, TypeError):
        findings.append(Finding("WARNING", "timestamp", r,
                                f"unparseable timestamp: {ts!r}"))


def _lint_indexes(kb_root, dir_children, concept_pages, findings, fix):
    for dirpath, children in dir_children.items():
        concepts = sorted(c for c in children
                          if c not in RESERVED and c != "domain.md")
        index_path = os.path.join(dirpath, "index.md")
        listed = set()
        if os.path.isfile(index_path):
            for m in LINK_RE.finditer(open(index_path, encoding="utf-8").read()):
                listed.add(os.path.basename(m.group(1).split("#")[0].strip().rstrip("/")))
        missing = [c for c in concepts if c not in listed]
        if missing and os.path.isfile(index_path):
            findings.append(Finding("WARNING", "index-drift",
                rel(kb_root, index_path), f"index.md omits: {', '.join(missing)}"))
        if fix and os.path.isfile(index_path):
            _regenerate_index(index_path, concepts, concept_pages, dirpath)


def _regenerate_index(index_path, concepts, concept_pages, dirpath):
    lines = ["", "# Concepts", ""]
    for c in concepts:
        meta = concept_pages.get(os.path.join(dirpath, c), {})
        title = meta.get("title") or c[:-3]
        desc = meta.get("description", "")
        lines.append(f"* [{title}]({c})" + (f" - {desc}" if desc else ""))
    block = "\n".join(lines) + "\n"
    text = open(index_path, encoding="utf-8").read()
    if "# Concepts" in text:
        head, _, rest = text.partition("# Concepts")
        nl = rest.find("\n# ")
        text = head.rstrip() + "\n" + block + (rest[nl:] if nl != -1 else "")
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
        print(json.dumps({"summary": counts, "conformant": counts["ERROR"] == 0,
                          "findings": [f.as_dict() for f in findings]}, indent=2))
    elif not findings:
        print("✓ Knowledge base is clean — OKF-conformant, no hygiene issues.")
    else:
        for f in findings:
            print(f"{f.level:<7} [{f.code}] {f.path}\n         {f.msg}")
        print(f"\nSummary: {counts['ERROR']} error(s), {counts['WARNING']} "
              f"warning(s), {counts['INFO']} info.")
        print("OKF-conformant." if counts["ERROR"] == 0
              else "NOT OKF-conformant — fix the errors above.")
    return 1 if counts["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
