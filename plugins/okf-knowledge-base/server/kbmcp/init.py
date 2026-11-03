"""Creates a KB root (with its capture directive) and scaffolds OKF v0.2 domains."""
import os
import re
from datetime import datetime, timezone

from .common import KbError, read_text, write_text, yaml_scalar

# Actor (OKF v0.2 §7) recorded in generated.by for files this tool writes.
ACTOR = "okf-knowledge-base/0.2.0"

# The directive texts live beside this server in the plugin's references/ folder.
REFERENCES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "references")

PLACEHOLDERS = {
    "<!-- Domains are registered here by the kb-init-domain skill. None yet. -->",
    "<!-- Domains registered here. -->",
    "<!-- Sub-domains are registered here by the kb-init-domain skill. None yet. -->",
}
DIRECTIVE_BLOCK = re.compile(r"<knowledge-base>.*?</knowledge-base>", re.S)
NON_SLUG = re.compile(r"[^a-z0-9]+")


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(s):
    return NON_SLUG.sub("-", s.strip().lower()).strip("-")


def _split_lines(t):
    return t.replace("\r\n", "\n").rstrip("\n").split("\n")


def init_kb(index, kb_root, capture_mode, instructions_file):
    """Creates the KB root files if absent and writes (or replaces) the capture
    directive block in the instructions file. Safe to re-run: switching capture
    mode or picking up a newer directive replaces the block in place."""
    resource = {"automatic": "sentinel-automatic.md", "agent": "sentinel-search.md"}.get(capture_mode)
    if resource is None:
        raise KbError(f"ERROR: capture_mode must be 'automatic' or 'agent', not '{capture_mode}'.")

    kb_root_full = os.path.abspath(kb_root)
    report = []
    os.makedirs(kb_root_full, exist_ok=True)
    root_index = os.path.join(kb_root_full, "index.md")
    if not os.path.isfile(root_index):
        write_text(root_index, '---\nokf_version: "0.2"\n---\n\n# Knowledge Base\n\n# Domains\n\n<!-- Domains registered here. -->\n')
        report.append(f"Created {root_index}.")
    root_log = os.path.join(kb_root_full, "log.md")
    if not os.path.isfile(root_log):
        write_text(root_log, f"# Knowledge Base Log\n\n## {_today()}\n* **Initialization**: Created the knowledge base.\n")
        report.append(f"Created {root_log}.")
    if not report:
        report.append(f"KB root {kb_root_full} already exists; left unchanged.")

    target = os.path.abspath(instructions_file if instructions_file
                             else os.path.join(os.path.dirname(kb_root_full.rstrip("/\\")) or ".", "CLAUDE.md"))
    try:
        kb_path = os.path.relpath(kb_root_full, os.path.dirname(target))
    except ValueError:  # different drives
        kb_path = kb_root_full
    block = _load_directive(resource).replace("{{kb_path}}", kb_path.replace("\\", "/") + "/")
    report.append(_write_directive(target, block) + f" ({capture_mode} capture)")

    index.invalidate(kb_root_full)
    return "OK: " + "\n".join(report)


def _load_directive(name):
    path = os.path.join(REFERENCES, name)
    if not os.path.isfile(path):
        raise KbError(f"ERROR: directive {path} is missing from this plugin.")
    return read_text(path).replace("\r\n", "\n").strip("\n")


def _write_directive(path, block):
    if not os.path.isfile(path):
        write_text(path, block + "\n")
        return f"Wrote the capture directive to new file {path}."
    existing = read_text(path).replace("\r\n", "\n")
    m = DIRECTIVE_BLOCK.search(existing)
    if m:
        if m.group(0) == block:
            return f"Capture directive in {path} is already current."
        write_text(path, existing[:m.start()] + block + existing[m.end():])
        return f"Replaced the capture directive in {path}."
    trimmed = existing.rstrip("\n")
    write_text(path, trimmed + ("\n\n" if trimmed else "") + block + "\n")
    return f"Appended the capture directive to {path}."


def init_domain(index, kb_root, slug_arg, title, desc, parent, tags_arg, force):
    raw = f"{parent}/{slug_arg}" if parent else slug_arg
    segments = [s for s in (_slugify(x) for x in raw.split("/")) if s]
    if not segments:
        raise KbError("ERROR: slug produced an empty identifier.")
    slug = "/".join(segments)
    is_sub = len(segments) > 1
    parent_segments = segments[:-1]
    leaf = segments[-1]

    kb_root_full = os.path.abspath(kb_root)
    if not os.path.isfile(os.path.join(kb_root_full, "index.md")):
        raise KbError(f"ERROR: no knowledge base at {kb_root_full} (missing index.md). Initialize it with kb-init first.")

    domain_dir = os.path.join(kb_root_full, *segments)
    if os.path.isdir(domain_dir) and not force:
        raise KbError(f"ERROR: {domain_dir} already exists. Use force to reuse.")
    if is_sub:
        parent_domain_md = os.path.join(kb_root_full, *parent_segments, "domain.md")
        if not os.path.isfile(parent_domain_md):
            raise KbError(f"ERROR: parent domain '{'/'.join(parent_segments)}' not found "
                          f"(expected {parent_domain_md}). Create it first with kb-init-domain.")

    tags = [t.strip() for t in (tags_arg or "").split(",") if t.strip()]
    kind = "sub-domain" if is_sub else "domain"
    tag_str = "[" + ", ".join(yaml_scalar(t) for t in tags) + "]"

    write_text(os.path.join(domain_dir, "domain.md"),
               "---\n"
               "type: Domain\n"
               f"title: {yaml_scalar(title)}\n"
               f"description: {yaml_scalar(desc)}\n"
               f"slug: {slug}\n"
               f"tags: {tag_str}\n"
               f"generated: {{ by: {ACTOR}, at: {_now_iso()} }}\n"
               "---\n\n"
               "# Scope\n\n"
               f"{desc}\n\n"
               f"**In scope:** _describe what belongs in this {kind}._\n\n"
               "**Out of scope:** _describe what does not, and where it lives instead._\n\n"
               "# Concept types\n\n"
               f"_List the kinds of concept pages this {kind} will hold (e.g. Entity, Playbook,\n"
               "Reference, Metric). Add subdirectories (or nested sub-domains) as it grows._\n\n"
               "# Entry points\n\n"
               "_Link the most important pages here once they exist._\n")
    write_text(os.path.join(domain_dir, "index.md"),
               f"# {title}\n\n"
               f"{desc}\n\n"
               "See [domain.md](domain.md) for scope and conventions.\n\n"
               "# Concepts\n\n"
               "<!-- Concept pages are listed here as they are ingested. None yet. -->\n")
    write_text(os.path.join(domain_dir, "log.md"),
               f"# {title} — Update Log\n\n## {_today()}\n* **Initialization**: Created the {title} {kind}.\n")

    if is_sub:
        parent_dir = os.path.join(kb_root_full, *parent_segments)
        _register(os.path.join(parent_dir, "index.md"), "# Sub-domains", f"{leaf}/index.md", title, desc)
        _add_log_line(os.path.join(parent_dir, "log.md"),
                      f"* **Creation**: Established the [{title}]({leaf}/index.md) sub-domain.")
        reg = f"Registered as a sub-domain under '{'/'.join(parent_segments)}' in {os.path.join(parent_dir, 'index.md')}."
    else:
        _register(os.path.join(kb_root_full, "index.md"), "# Domains", f"{slug}/index.md", title, desc)
        _add_log_line(os.path.join(kb_root_full, "log.md"),
                      f"* **Creation**: Established the [{title}]({slug}/index.md) domain.")
        reg = f"Registered in {os.path.join(kb_root_full, 'index.md')}."

    index.invalidate(kb_root_full)
    return f"OK: created {kind} '{slug}' at {domain_dir}\nFiles: domain.md, index.md, log.md\n{reg}"


def _register(index_path, heading, link_target, title, desc):
    entry = f"* [{title}]({link_target}) - {desc}"
    if not os.path.isfile(index_path):
        write_text(index_path, f"# {title}'s parent\n\n{heading}\n\n{entry}\n")
        return
    lines = [l for l in _split_lines(read_text(index_path)) if l.strip() not in PLACEHOLDERS]
    if entry in lines:
        return
    hi = next((i for i, l in enumerate(lines) if l.strip() == heading), -1)
    if hi < 0:
        while lines and lines[-1].strip() == "":
            lines.pop()
        lines += ["", heading, "", entry]
    else:
        end = next((j for j in range(hi + 1, len(lines)) if lines[j].startswith("# ")), len(lines))
        ins = end
        while ins - 1 > hi and lines[ins - 1].strip() == "":
            ins -= 1
        lines.insert(ins, entry)
    write_text(index_path, "\n".join(lines) + "\n")


def _add_log_line(log_path, line):
    if not os.path.isfile(log_path):
        write_text(log_path, f"# Update Log\n\n## {_today()}\n{line}\n")
        return
    log = read_text(log_path)
    stamp = f"## {_today()}"
    if stamp in log:
        idx = log.index(stamp)
        log = log[:idx] + stamp + "\n" + line + log[idx + len(stamp):]
    else:
        lines = _split_lines(log)
        at = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
        merged = lines[:at] + [stamp, line, ""] + lines[at:]
        log = "\n".join(merged).rstrip("\n") + "\n"
    write_text(log_path, log)
