"""Parsed pages and the persistent page cache.

The cache keys each file on (mtime, size), so repeated search/detect/lint/analyze
calls re-parse only the files that changed.
"""
import os

from .common import parse_frontmatter, read_text, token_set, tokens

RESERVED = {"index.md", "log.md"}


class Page:
    __slots__ = (
        "full_path", "rel_path", "name", "dir_full_path", "raw_text", "byte_count", "fm", "is_reserved",
        "title_tokens", "desc_tokens", "tag_tokens", "type_tokens", "body_token_counts", "blob_tokens",
        "strong_tokens", "weak_tokens",
    )


def build_page(kb_root_full, full_path, text):
    fm = parse_frontmatter(text)
    name = os.path.basename(full_path)
    tags_joined = " ".join(fm.get_list("tags"))
    counts = {}
    for t in tokens(fm.body):
        counts[t] = counts.get(t, 0) + 1
    title, desc = fm.get_string("title"), fm.get_string("description")

    p = Page()
    p.full_path = full_path
    p.rel_path = os.path.relpath(full_path, kb_root_full).replace("\\", "/")
    p.name = name
    p.dir_full_path = os.path.dirname(full_path)
    p.raw_text = text
    p.byte_count = len(text.encode("utf-8"))
    p.fm = fm
    p.is_reserved = name in RESERVED
    p.title_tokens = token_set(title)
    p.desc_tokens = token_set(desc)
    p.tag_tokens = token_set(tags_joined)
    p.type_tokens = token_set(fm.get_string("type"))
    p.body_token_counts = counts
    p.blob_tokens = token_set(" ".join([title, tags_joined, desc, fm.body]))
    p.strong_tokens = token_set(title + " " + tags_joined)
    p.weak_tokens = token_set(desc + " " + fm.body)
    return p


def _is_markdown(name):
    return name.lower().endswith(".md") if os.name == "nt" else name.endswith(".md")


class KbIndex:
    def __init__(self):
        self._roots = {}

    def get_pages(self, kb_root_full):
        """Every *.md page under the root, reusing cached parses for unchanged files."""
        root = os.path.abspath(kb_root_full)
        cache = self._roots.setdefault(os.path.normcase(root), {})
        present = set()
        pages = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            for fn in sorted(filenames):
                if not _is_markdown(fn):
                    continue
                full = os.path.join(dirpath, fn)
                key = os.path.normcase(full)
                present.add(key)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                hit = cache.get(key)
                if hit and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
                    pages.append(hit[2])
                    continue
                try:
                    text = read_text(full)
                except OSError:
                    continue
                page = build_page(root, full, text)
                cache[key] = (st.st_mtime_ns, st.st_size, page)
                pages.append(page)
        for stale in [k for k in cache if k not in present]:
            del cache[stale]
        return pages

    def invalidate(self, kb_root_full):
        """Drops a whole root (used after mutating operations)."""
        self._roots.pop(os.path.normcase(os.path.abspath(kb_root_full)), None)
