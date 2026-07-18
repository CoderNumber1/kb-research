#!/usr/bin/env python3
"""Scaffold an OKF domain (or nested sub-domain) in the KB and register it.

Creates <kb>/<slug>/{domain.md, index.md, log.md, raw/index.md}. A top-level
domain is registered in the root kb/index.md catalog and kb/log.md. A nested
sub-domain (slug containing "/", or via --parent) is registered under its
parent domain's index.md ("# Sub-domains") and log.md instead.

The KB root is resolved from --kb-root, else the $KB_ROOT env var, else by
searching the working directory; if none is found a new bundle is created at
./kb.

Usage:
  init_domain.py --slug billing --title "Billing" --description "..."
  init_domain.py --slug billing/eu --title "EU Billing" --description "..."
  init_domain.py --parent billing --slug eu --title "EU Billing" --description "..."

Exit codes: 0 ok, 2 usage/precondition error.
"""
import argparse
import datetime as dt
import os
import re
import sys

from kb_common import find_kb_root

PLACEHOLDERS = {
    "<!-- Domains are registered here by the kb-init-domain skill. None yet. -->",
    "<!-- Domains registered here. -->",
    "<!-- Sub-domains are registered here by the kb-init-domain skill. None yet. -->",
}


def today() -> str:
    return dt.date.today().isoformat()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.strip().lower()).strip("-")


def slug_segments(raw: str):
    return [seg for seg in (slugify(p) for p in raw.split("/")) if seg]


def yaml_list(items):
    return "[" + ", ".join(items) + "]"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True,
                    help="Domain id. May be a path (e.g. billing/eu) to nest.")
    ap.add_argument("--parent", default="",
                    help="Optional parent domain path to nest under.")
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", required=True,
                    help="One sentence describing the domain's scope. Used for "
                         "auto-detecting the target domain during ingest.")
    ap.add_argument("--tags", default="", help="Comma-separated tags.")
    ap.add_argument("--kb-root", default=None,
                    help="KB root. Defaults to a detected bundle, else ./kb.")
    ap.add_argument("--force", action="store_true",
                    help="Proceed even if the domain directory already exists.")
    args = ap.parse_args()

    raw = f"{args.parent}/{args.slug}" if args.parent.strip() else args.slug
    segments = slug_segments(raw)
    if not segments:
        print("ERROR: --slug produced an empty identifier.", file=sys.stderr)
        return 2

    slug = "/".join(segments)
    is_sub = len(segments) > 1
    parent_segments = segments[:-1]
    leaf = segments[-1]

    # Resolve KB root: explicit, else detected existing bundle, else new ./kb.
    kb_root = (args.kb_root or find_kb_root() or "kb").rstrip("/")

    domain_dir = os.path.join(kb_root, *segments)
    if os.path.exists(domain_dir) and not args.force:
        print(f"ERROR: {domain_dir} already exists. Use --force to reuse.",
              file=sys.stderr)
        return 2

    _ensure_kb_root(kb_root)

    if is_sub:
        parent_domain_md = os.path.join(kb_root, *parent_segments, "domain.md")
        if not os.path.isfile(parent_domain_md):
            print(f"ERROR: parent domain '{'/'.join(parent_segments)}' not found "
                  f"(expected {parent_domain_md}). Create it first with "
                  "kb-init-domain.", file=sys.stderr)
            return 2

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    os.makedirs(os.path.join(domain_dir, "raw"), exist_ok=True)
    kind = "sub-domain" if is_sub else "domain"

    domain_md = f"""---
type: Domain
title: {args.title}
description: {args.description}
slug: {slug}
tags: {yaml_list(tags) if tags else "[]"}
status: active
timestamp: {now_iso()}
---

# Scope

{args.description}

**In scope:** _describe what belongs in this {kind}._

**Out of scope:** _describe what does not, and where it lives instead._

# Concept types

_List the kinds of concept pages this {kind} will hold (e.g. Entity, Playbook,
Reference, Metric). Add subdirectories (or nested sub-domains) as it grows._

# Entry points

_Link the most important pages here once they exist._

# Sources

Raw source material for this {kind} is snapshotted under [`raw/`](raw/index.md).
"""
    _write(os.path.join(domain_dir, "domain.md"), domain_md)

    index_md = f"""# {args.title}

{args.description}

See [domain.md](domain.md) for scope and conventions.

# Concepts

<!-- Concept pages are listed here as they are ingested. None yet. -->

# Sources

* [Raw sources](raw/) - immutable snapshots of ingested material.
"""
    _write(os.path.join(domain_dir, "index.md"), index_md)

    _write(os.path.join(domain_dir, "log.md"),
           f"# {args.title} — Update Log\n\n## {today()}\n"
           f"* **Initialization**: Created the {args.title} {kind}.\n")

    _write(os.path.join(domain_dir, "raw", "index.md"),
           "# Raw Sources\n\nImmutable snapshots of material ingested here. "
           "Concept pages cite back to these. Do not edit source snapshots after "
           "they are written.\n\n<!-- Sources are listed here by the kb-ingest "
           "skill. None yet. -->\n")

    if is_sub:
        parent_dir = os.path.join(kb_root, *parent_segments)
        _register_entry(os.path.join(parent_dir, "index.md"), "# Sub-domains",
                        f"{leaf}/index.md", args.title, args.description)
        _append_log(os.path.join(parent_dir, "log.md"),
                    f"* **Creation**: Established the "
                    f"[{args.title}]({leaf}/index.md) sub-domain.")
        reg = (f"Registered as a sub-domain under '{'/'.join(parent_segments)}' "
               f"in {os.path.join(parent_dir, 'index.md')}.")
    else:
        _register_entry(os.path.join(kb_root, "index.md"), "# Domains",
                        f"{slug}/index.md", args.title, args.description)
        _append_log(os.path.join(kb_root, "log.md"),
                    f"* **Creation**: Established the "
                    f"[{args.title}]({slug}/index.md) domain.")
        reg = f"Registered in {os.path.join(kb_root, 'index.md')}."

    print(f"OK: created {kind} '{slug}' at {domain_dir}")
    print("Files: domain.md, index.md, log.md, raw/index.md")
    print(reg)
    return 0


def _ensure_kb_root(kb_root: str) -> None:
    os.makedirs(kb_root, exist_ok=True)
    root_index = os.path.join(kb_root, "index.md")
    if not os.path.exists(root_index):
        _write(root_index, '---\nokf_version: "0.1"\n---\n\n# Knowledge Base\n\n'
                           "# Domains\n\n<!-- Domains registered here. -->\n")
    root_log = os.path.join(kb_root, "log.md")
    if not os.path.exists(root_log):
        _write(root_log, "# Knowledge Base Log\n\nNewest first.\n")


def _register_entry(index_path, heading, link_target, title, desc) -> None:
    entry = f"* [{title}]({link_target}) - {desc}"
    if not os.path.exists(index_path):
        _write(index_path, f"# {title}'s parent\n\n{heading}\n\n{entry}\n")
        return
    lines = [ln for ln in _read(index_path).splitlines()
             if ln.strip() not in PLACEHOLDERS]
    if entry in lines:
        return
    hi = next((i for i, ln in enumerate(lines) if ln.strip() == heading), None)
    if hi is None:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", heading, "", entry]
    else:
        end = next((j for j in range(hi + 1, len(lines))
                    if lines[j].startswith("# ")), len(lines))
        ins = end
        while ins - 1 > hi and not lines[ins - 1].strip():
            ins -= 1
        lines[ins:ins] = [entry]
    _write(index_path, "\n".join(lines) + "\n")


def _append_log(log_path, line) -> None:
    if not os.path.exists(log_path):
        _write(log_path, f"# Update Log\n\n## {today()}\n{line}\n")
        return
    log = _read(log_path)
    stamp = f"## {today()}"
    if stamp in log:
        log = log.replace(stamp, stamp + "\n" + line, 1)
    else:
        lines = log.splitlines()
        insert_at = next((i for i, ln in enumerate(lines)
                          if ln.startswith("## ")), len(lines))
        lines[insert_at:insert_at] = [stamp, line, ""]
        log = "\n".join(lines).rstrip() + "\n"
    _write(log_path, log)


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    raise SystemExit(main())
