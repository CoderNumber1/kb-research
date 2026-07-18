"""Shared helpers for the OKF knowledge-base scripts.

Co-located with the other scripts so they can `import kb_common` directly (the
script's own directory is always on sys.path). Zero third-party dependencies —
pure stdlib, so the plugin runs anywhere Python 3 does.
"""
import os
import re

# --- text normalization ----------------------------------------------------

STOP = set("""a an the of to in on for and or but with without into from by as at
is are was were be been being this that these those it its it's you your we our
they their he she his her them us i me my mine ours yours will would can could
should may might must do does did done has have had how what when where why who
whom which whose than then so if else not no yes about over under again further
more most other some such only own same too very just also can't cannot""".split())

# Longest-first suffix list; collapses word families (verify/verified/
# verification, sign/signed/signature, retry/retried/retries) to a shared root
# so keyword overlap between a source and a domain — or a query and a page —
# actually lands. Crude but consistent, which is all token-bag matching needs.
_SUFFIXES = sorted([
    "ization", "ational", "ication", "fulness", "ousness", "iveness",
    "ature", "ities", "ement", "ness", "tion", "sion", "ies", "ied", "ying",
    "ing", "ers", "er", "ed", "ly", "al", "s", "y", "e",
], key=len, reverse=True)


def stem(word: str) -> str:
    for suf in _SUFFIXES:
        if len(word) - len(suf) >= 3 and word.endswith(suf):
            return word[:-len(suf)]
    return word


def tokenize(text: str):
    """Lowercase, split on non-alphanumerics, drop stopwords/short tokens, stem."""
    return [stem(t) for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if t not in STOP and len(t) > 1]


# --- frontmatter parsing ---------------------------------------------------

def _scalar(v: str):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def parse_frontmatter(text: str):
    """Parse leading YAML-ish frontmatter.

    Returns (meta, body, ok, err). Lenient: it keeps going past a malformed
    line and still returns whatever parsed, but reports ok=False so the linter
    can flag it. Handles scalars, inline lists [a, b], and block lists.
    """
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
    meta, key, ok, err = {}, None, True, ""
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
            ok, err = False, f"unparseable frontmatter line: {raw!r}"
    return meta, "\n".join(lines[end + 1:]), ok, err


def frontmatter(text: str):
    """Convenience: just (meta, body), for callers that don't need ok/err."""
    meta, body, _ok, _err = parse_frontmatter(text)
    return meta, body


# --- knowledge-base discovery ----------------------------------------------

def is_bundle_root(path: str) -> bool:
    """True if `path` looks like an OKF bundle root: an index.md declaring
    okf_version, or a directory that directly contains domain directories."""
    if not os.path.isdir(path):
        return False
    index = os.path.join(path, "index.md")
    if os.path.isfile(index):
        try:
            meta, _ = frontmatter(open(index, encoding="utf-8").read())
            if str(meta.get("okf_version", "")).strip():
                return True
        except OSError:
            pass
    try:
        for name in os.listdir(path):
            if os.path.isfile(os.path.join(path, name, "domain.md")):
                return True
    except OSError:
        pass
    return False


def find_kb_root(explicit=None, start=None):
    """Resolve the knowledge-base root.

    Order: an explicit path, then the $KB_ROOT env var, then a search from
    `start` (default: cwd) upward through ancestor directories — preferring a
    `kb/` child bundle, else the directory itself. Returns an absolute path, or
    None if no bundle is found. This is what lets the plugin 'detect and use a
    KB when present in the working directory'.
    """
    if explicit:
        return explicit
    env = os.environ.get("KB_ROOT")
    if env:
        return env
    cur = os.path.abspath(start or os.getcwd())
    while True:
        child = os.path.join(cur, "kb")
        if is_bundle_root(child):
            return child
        if is_bundle_root(cur):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent
