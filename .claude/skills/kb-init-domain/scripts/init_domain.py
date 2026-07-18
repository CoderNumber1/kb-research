#!/usr/bin/env python3
"""Scaffold a new OKF domain (bundle) inside the knowledge base and register it.

Creates kb/<slug>/{domain.md, index.md, log.md, raw/index.md} and adds the
domain to the root kb/index.md catalog and kb/log.md. Deterministic and safe to
reason about; the kb-init-domain skill drives it.

Usage:
  init_domain.py --slug billing --title "Billing" \
      --description "How invoicing, payments, and dunning work." \
      --tags billing,payments --kb-root kb

Exit codes: 0 ok, 2 usage/precondition error.
"""
import argparse
import datetime as dt
import os
import re
import sys


def today() -> str:
    return dt.date.today().isoformat()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def yaml_list(items):
    return "[" + ", ".join(items) + "]"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="Directory-safe domain id.")
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", required=True,
                    help="One sentence describing the domain's scope. Used for "
                         "auto-detecting the target domain during ingest.")
    ap.add_argument("--tags", default="", help="Comma-separated tags.")
    ap.add_argument("--kb-root", default="kb")
    ap.add_argument("--force", action="store_true",
                    help="Proceed even if the domain directory already exists.")
    args = ap.parse_args()

    slug = slugify(args.slug)
    if not slug:
        print("ERROR: --slug produced an empty identifier.", file=sys.stderr)
        return 2

    kb_root = args.kb_root.rstrip("/")
    domain_dir = os.path.join(kb_root, slug)
    if os.path.exists(domain_dir) and not args.force:
        print(f"ERROR: {domain_dir} already exists. Use --force to reuse.",
              file=sys.stderr)
        return 2

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    os.makedirs(os.path.join(domain_dir, "raw"), exist_ok=True)

    # Ensure KB root files exist.
    _ensure_kb_root(kb_root)

    # domain.md — the auto-detection anchor (a first-class OKF concept).
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

**In scope:** _describe what belongs in this domain._

**Out of scope:** _describe what does not, and where it lives instead._

# Concept types

_List the kinds of concept pages this domain will hold (e.g. Entity, Playbook,
Reference, Metric). Add subdirectories as the domain grows._

# Entry points

_Link the most important pages here once they exist._

# Sources

Raw source material for this domain is snapshotted under [`raw/`](raw/index.md).
"""
    _write(os.path.join(domain_dir, "domain.md"), domain_md)

    # Domain index (progressive disclosure). No frontmatter (OKF §6).
    index_md = f"""# {args.title}

{args.description}

See [domain.md](domain.md) for scope and conventions.

# Concepts

<!-- Concept pages are listed here as they are ingested. None yet. -->

# Sources

* [Raw sources](raw/) - immutable snapshots of ingested material.
"""
    _write(os.path.join(domain_dir, "index.md"), index_md)

    log_md = f"""# {args.title} — Update Log

## {today()}
* **Initialization**: Created the {args.title} domain.
"""
    _write(os.path.join(domain_dir, "log.md"), log_md)

    raw_index = """# Raw Sources

Immutable snapshots of material ingested into this domain. Concept pages cite
back to these. Do not edit source snapshots after they are written.

<!-- Sources are listed here by the kb-ingest skill. None yet. -->
"""
    _write(os.path.join(domain_dir, "raw", "index.md"), raw_index)

    _register_in_root(kb_root, slug, args.title, args.description)

    print(f"OK: created domain '{slug}' at {domain_dir}")
    print("Files: domain.md, index.md, log.md, raw/index.md")
    print(f"Registered in {os.path.join(kb_root, 'index.md')} and appended to "
          f"{os.path.join(kb_root, 'log.md')}.")
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


def _register_in_root(kb_root: str, slug: str, title: str, desc: str) -> None:
    root_index = os.path.join(kb_root, "index.md")
    entry = f"* [{title}]({slug}/index.md) - {desc}"
    text = _read(root_index)
    if entry in text:
        pass
    elif "# Domains" in text:
        head, _, tail = text.partition("# Domains")
        # Drop the placeholder comment line if present.
        tail_lines = [ln for ln in tail.splitlines()
                      if ln.strip() != "<!-- Domains are registered here by the "
                      "kb-init-domain skill. None yet. -->"
                      and ln.strip() != "<!-- Domains registered here. -->"]
        tail = "\n".join(tail_lines)
        text = head + "# Domains" + tail.rstrip() + "\n" + entry + "\n"
        _write(root_index, text)
    else:
        _write(root_index, text.rstrip() + "\n\n# Domains\n\n" + entry + "\n")

    root_log = os.path.join(kb_root, "log.md")
    log = _read(root_log)
    stamp = f"## {today()}"
    line = f"* **Creation**: Established the [{title}]({slug}/index.md) domain."
    if stamp in log:
        # Add the entry under today's existing date heading.
        log = log.replace(stamp, stamp + "\n" + line, 1)
    else:
        # Insert a new date block above the newest existing dated entry, or at
        # the end of the header prose if there are none yet (newest-first order).
        lines = log.splitlines()
        insert_at = len(lines)
        for i, ln in enumerate(lines):
            if ln.startswith("## "):
                insert_at = i
                break
        block = [stamp, line, ""]
        lines[insert_at:insert_at] = block
        log = "\n".join(lines).rstrip() + "\n"
    _write(root_log, log)


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    raise SystemExit(main())
