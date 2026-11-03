"""Shared text handling: YAML frontmatter parsing, stemming, tokenization, and path helpers."""
import os
import re
import unicodedata


class KbError(Exception):
    """A hard tool error (no KB, bad path), surfaced to the caller as an MCP error result."""


# --- Tokenization -----------------------------------------------------------

STOP = {
    "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "but", "with", "without",
    "into", "from", "by", "as", "at", "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "it", "its", "you", "your", "we", "our", "they",
    "their", "he", "she", "his", "her", "them", "us", "i", "me", "my", "mine", "ours",
    "yours", "will", "would", "can", "could", "should", "may", "might", "must", "do",
    "does", "did", "done", "has", "have", "had", "how", "what", "when", "where", "why",
    "who", "whom", "which", "whose", "than", "then", "so", "if", "else", "not", "no",
    "yes", "about", "over", "under", "again", "further", "more", "most", "other", "some",
    "such", "only", "own", "same", "too", "very", "just", "also", "cannot",
}

# Longest-first suffix list. Order within a given length is irrelevant:
# a word has exactly one ending of each length.
_SUFFIXES = sorted([
    "ization", "ational", "ication", "fulness", "ousness", "iveness",
    "ature", "ities", "ement", "ness", "tion", "sion", "ies", "ied", "ying",
    "ing", "ers", "er", "ed", "ly", "al", "s", "y", "e",
], key=len, reverse=True)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def stem(word):
    for suf in _SUFFIXES:
        if len(word) - len(suf) >= 3 and word.endswith(suf):
            return word[:len(word) - len(suf)]
    return word


def tokens(text):
    """Stemmed, non-stopword tokens (length > 1), in text order with duplicates."""
    if not text:
        return []
    return [stem(t) for t in _TOKEN_RE.findall(text.lower()) if len(t) > 1 and t not in STOP]


def raw_words(text):
    """Unstemmed, non-stopword tokens (length > 1) — used to locate readable snippets."""
    if not text:
        return []
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 1 and t not in STOP]


def token_set(text):
    return set(tokens(text))


def net_round(value, digits):
    """Rounds like .NET Math.Round(double, digits): scale, round half to even, unscale.

    Python's round(value, digits) rounds the exact binary value instead, which
    disagrees on midpoints such as 6.825 (6.83 here, 6.82 in .NET).
    """
    power = 10.0 ** digits
    return round(value * power) / power


# --- YAML (the subset frontmatter uses) ---------------------------------------
#
# Block mappings and sequences, flow mappings and sequences, plain, single- and
# double-quoted scalars, literal/folded block scalars, and comments. Scalars stay
# strings (no type resolution). Anchors, aliases, and tags are rejected.

class YamlError(Exception):
    def __init__(self, message, line):
        super().__init__(message)
        self.line = line


_ESCAPES = {
    "0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n", "v": "\v", "f": "\f",
    "r": "\r", "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\", "N": "\x85",
    "_": "\xa0", "L": " ", "P": " ",
}
_HEX_ESCAPES = {"x": 2, "u": 4, "U": 8}


def _indent_of(line):
    return len(line) - len(line.lstrip(" "))


def _strip_comment(text):
    """Drops a trailing ` # comment` that sits outside quotes."""
    quote = None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
            elif ch == "\\" and quote == '"':
                continue
        elif ch in "\"'" and (i == 0 or text[i - 1] in " \t[{,:"):
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i].rstrip()
    return text.rstrip()


def _read_quoted(text, pos, line):
    """Reads the quoted scalar starting at text[pos]; returns (value, end_pos)."""
    q = text[pos]
    out = []
    i = pos + 1
    while i < len(text):
        ch = text[i]
        if q == "'":
            if ch == "'":
                if i + 1 < len(text) and text[i + 1] == "'":
                    out.append("'")
                    i += 2
                    continue
                return "".join(out), i + 1
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            return "".join(out), i + 1
        if ch == "\\":
            if i + 1 >= len(text):
                break
            esc = text[i + 1]
            if esc in _ESCAPES:
                out.append(_ESCAPES[esc])
                i += 2
                continue
            if esc in _HEX_ESCAPES:
                n = _HEX_ESCAPES[esc]
                digits = text[i + 2:i + 2 + n]
                if len(digits) != n or any(c not in "0123456789abcdefABCDEF" for c in digits):
                    raise YamlError("while scanning a double-quoted scalar, found invalid escape", line)
                out.append(chr(int(digits, 16)))
                i += 2 + n
                continue
            raise YamlError(f"while scanning a double-quoted scalar, found unknown escape character '{esc}'", line)
        out.append(ch)
        i += 1
    raise YamlError("while scanning a quoted scalar, found unexpected end of stream", line)


def _split_key(content, line):
    """Splits `key: rest` (block context). Returns (key, rest) or None when not a key line."""
    if not content or content[0] in "[{":
        return None
    if content[0] in "\"'":
        key, end = _read_quoted(content, 0, line)
        rest = content[end:]
        stripped = rest.lstrip(" ")
        if stripped.startswith(":") and (len(stripped) == 1 or stripped[1] in " \t"):
            return key, stripped[1:]
        return None
    for i, ch in enumerate(content):
        if ch == "#" and i > 0 and content[i - 1] in " \t":
            return None
        if ch == ":" and (i + 1 == len(content) or content[i + 1] in " \t"):
            return content[:i].strip(), content[i + 1:]
    return None


def _plain(text, line):
    """Validates and returns a plain (unquoted) block scalar."""
    first = text[0]
    if first in "&*!":
        raise YamlError("anchors, aliases, and tags are not supported", line)
    if first in "@`%":
        raise YamlError(f"found character '{first}' that cannot start any token", line)
    if first in ",]}":
        raise YamlError(f"did not find expected node content (found '{first}')", line)
    if text == "-" or text.startswith("- "):
        raise YamlError("block sequence entries are not allowed in this context", line)
    if text.startswith(("? ", ": ")) or text in ("?", ":"):
        raise YamlError("complex keys are not supported", line)
    if ": " in text or text.endswith(":"):
        raise YamlError("mapping values are not allowed in this context", line)
    return text


def _scalar(text, line):
    """Parses a complete inline value: quoted, flow collection, or plain."""
    if text == "":
        return ""
    if text[0] in "\"'":
        value, end = _read_quoted(text, 0, line)
        if text[end:].strip():
            raise YamlError("did not find expected key after a quoted scalar", line)
        return value
    if text[0] in "[{":
        value, end = _Flow(text, line).node(0)
        if text[end:].strip():
            raise YamlError("did not find expected <document end> after a flow collection", line)
        return value
    return _plain(text, line)


class _Flow:
    """Recursive parser for flow collections: [a, b] and { k: v }."""

    def __init__(self, text, line):
        self.text = text
        self.line = line

    def _skip(self, i):
        while i < len(self.text) and self.text[i] in " \t":
            i += 1
        return i

    def node(self, i):
        i = self._skip(i)
        if i >= len(self.text):
            raise YamlError("while parsing a flow node, found unexpected end of stream", self.line)
        ch = self.text[i]
        if ch == "[":
            return self._sequence(i + 1)
        if ch == "{":
            return self._mapping(i + 1)
        if ch in "\"'":
            return _read_quoted(self.text, i, self.line)
        if ch in "&*!":
            raise YamlError("anchors, aliases, and tags are not supported", self.line)
        start = i
        while i < len(self.text):
            c = self.text[i]
            if c in ",[]{}":
                break
            if c == ":" and (i + 1 == len(self.text) or self.text[i + 1] in " \t,[]{}"):
                break
            if c == "#" and self.text[i - 1] in " \t":
                break
            i += 1
        return self.text[start:i].strip(), i

    def _sequence(self, i):
        items = []
        while True:
            i = self._skip(i)
            if i >= len(self.text):
                raise YamlError("while parsing a flow sequence, did not find expected ',' or ']'", self.line)
            if self.text[i] == "]":
                return items, i + 1
            value, i = self.node(i)
            items.append(value)
            i = self._skip(i)
            if i < len(self.text) and self.text[i] == ",":
                i += 1
            elif i >= len(self.text) or self.text[i] != "]":
                raise YamlError("while parsing a flow sequence, did not find expected ',' or ']'", self.line)

    def _mapping(self, i):
        result = {}
        while True:
            i = self._skip(i)
            if i >= len(self.text):
                raise YamlError("while parsing a flow mapping, did not find expected ',' or '}'", self.line)
            if self.text[i] == "}":
                return result, i + 1
            key, i = self.node(i)
            if not isinstance(key, str):
                raise YamlError("complex keys are not supported", self.line)
            i = self._skip(i)
            value = ""
            if i < len(self.text) and self.text[i] == ":":
                i = self._skip(i + 1)
                if i < len(self.text) and self.text[i] not in ",}":
                    value, i = self.node(i)
            if key in result:
                raise YamlError("Duplicate key", self.line)
            result[key] = value
            i = self._skip(i)
            if i < len(self.text) and self.text[i] == ",":
                i += 1
            elif i >= len(self.text) or self.text[i] != "}":
                raise YamlError("while parsing a flow mapping, did not find expected ',' or '}'", self.line)


class _Block:
    """Indentation-driven parser for block mappings, sequences, and scalars."""

    def __init__(self, text):
        self.lines = [l.rstrip("\r") for l in text.split("\n")]
        self.i = 0
        for n, l in enumerate(self.lines):
            lead = l[:len(l) - len(l.lstrip(" \t"))]
            if "\t" in lead and l.strip():
                raise YamlError("found a tab character where indentation is expected", n + 1)

    def _skip(self):
        while self.i < len(self.lines):
            s = self.lines[self.i].strip()
            if s and not s.startswith("#"):
                return
            self.i += 1

    def _at_end(self):
        self._skip()
        return self.i >= len(self.lines)

    @staticmethod
    def _is_entry(content):
        return content == "-" or content.startswith("- ")

    def document(self):
        if self._at_end():
            return None
        value = self.block(_indent_of(self.lines[self.i]))
        if not self._at_end():
            raise YamlError("did not find expected <document end>", self.i + 1)
        return value

    def block(self, indent):
        content = self.lines[self.i][indent:]
        if self._is_entry(content):
            return self.sequence(indent)
        if _split_key(content, self.i + 1) is not None:
            return self.mapping(indent)
        start = self.i + 1
        parts = []
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if not line.strip() or _indent_of(line) < indent:
                break
            parts.append(_strip_comment(line.strip()))
            self.i += 1
        return _scalar(" ".join(p for p in parts if p), start)

    def mapping(self, indent):
        result = {}
        while not self._at_end():
            line = self.lines[self.i]
            ind = _indent_of(line)
            if ind < indent:
                break
            if ind > indent:
                raise YamlError("while parsing a block mapping, did not find expected key (bad indentation)", self.i + 1)
            content = line[indent:]
            if self._is_entry(content):
                raise YamlError("while parsing a block mapping, did not find expected key", self.i + 1)
            kv = _split_key(content, self.i + 1)
            if kv is None:
                raise YamlError("while scanning a simple key, could not find expected ':'", self.i + 1)
            key, rest = kv
            lineno = self.i + 1
            if key in result:
                raise YamlError("Duplicate key", lineno)
            self.i += 1
            result[key] = self.value(rest, indent, lineno, sequence_may_align=True)
        return result

    def sequence(self, indent):
        items = []
        while not self._at_end():
            line = self.lines[self.i]
            ind = _indent_of(line)
            if ind < indent:
                break
            if ind > indent:
                raise YamlError("while parsing a block collection, did not find expected '-' indicator", self.i + 1)
            content = line[indent:]
            if not self._is_entry(content):
                break
            after = content[1:]
            body = after.lstrip(" ")
            body_indent = indent + 1 + (len(after) - len(body))
            lineno = self.i + 1
            if body and (self._is_entry(body) or _split_key(body, lineno) is not None):
                # Nested collection on the entry line: parse it at its own column.
                self.lines[self.i] = " " * body_indent + body
                items.append(self.block(body_indent))
            else:
                self.i += 1
                items.append(self.value(body, indent, lineno, sequence_may_align=False))
        return items

    def value(self, rest, indent, lineno, sequence_may_align):
        """The value after `key:` or `-`; the cursor is already on the next line."""
        text = _strip_comment(rest.strip())
        if text == "":
            if self._at_end():
                return ""
            line = self.lines[self.i]
            ind = _indent_of(line)
            if ind > indent:
                return self.block(ind)
            if ind == indent and sequence_may_align and self._is_entry(line[indent:]):
                return self.sequence(indent)
            return ""
        if text[0] in "|>":
            return self._block_scalar(text, indent, lineno)
        # Continuation lines: anything more indented than the owning key or entry.
        parts = [text]
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if not line.strip() or _indent_of(line) <= indent:
                break
            parts.append(_strip_comment(line.strip()))
            self.i += 1
        return _scalar(" ".join(p for p in parts if p), lineno)

    def _block_scalar(self, header, indent, lineno):
        m = re.fullmatch(r"([|>])([+-]?)[1-9]?|([|>])[1-9]([+-])", header)
        if not m:
            raise YamlError("while scanning a block scalar, did not find expected comment or line break", lineno)
        style = m.group(1) or m.group(3)
        chomp = m.group(2) or m.group(4) or ""
        raw = []
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.strip() and _indent_of(line) <= indent:
                break
            raw.append(line)
            self.i += 1
        while raw and not raw[-1].strip():
            raw.pop()
            if chomp == "+":
                break
        content = [l for l in raw if l.strip()]
        base = min((_indent_of(l) for l in content), default=0)
        lines = [l[base:] if l.strip() else "" for l in raw]
        if style == "|":
            text = "\n".join(lines)
        else:
            text, prev_blank = "", False
            for l in lines:
                if not l:
                    text += "\n"
                    prev_blank = True
                else:
                    text += ("" if not text or prev_blank or text.endswith("\n") else " ") + l
                    prev_blank = False
        if chomp == "-" or not text:
            return text
        return text + "\n"


def parse_yaml(text):
    """Parses one YAML document; returns None for an empty document."""
    return _Block(text).document()


# --- Frontmatter ------------------------------------------------------------

class Frontmatter:
    """Parsed frontmatter. Values are str (scalar), list (sequence), or dict (mapping)."""
    __slots__ = ("meta", "body", "ok", "err")

    def __init__(self, meta, body, ok, err):
        self.meta = meta
        self.body = body
        self.ok = ok
        self.err = err

    def has(self, key):
        return key in self.meta

    def raw(self, key):
        return self.meta.get(key)

    def get_string(self, key):
        """Scalar as-is; a sequence of scalars space-joined; anything else ""."""
        return as_string(self.meta.get(key))

    def get_list(self, key):
        """Tag normalization: missing → [], scalar → [scalar], sequence → its scalars."""
        value = self.meta.get(key)
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [v for v in value if isinstance(v, str)]
        return []


def as_string(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(v for v in value if isinstance(v, str))
    return ""


def parse_frontmatter(text):
    if text is None or not text.startswith("---"):
        return Frontmatter({}, text or "", False, "no frontmatter block")
    lines = text.split("\n")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), -1)
    if end < 0:
        return Frontmatter({}, text, False, "unterminated frontmatter block")
    body = "\n".join(lines[end + 1:]) if end + 1 <= len(lines) - 1 else ""
    try:
        doc = parse_yaml("\n".join(lines[1:end]))
    except YamlError as ex:
        return Frontmatter({}, body, False, f"invalid YAML (line {ex.line}): {ex}")
    if doc is None:
        return Frontmatter({}, body, True, "")
    if not isinstance(doc, dict):
        return Frontmatter({}, body, False, "frontmatter is not a YAML mapping")
    return Frontmatter(doc, body, True, "")


def yaml_scalar(value):
    """Quotes a scalar for frontmatter when plain YAML would misread it."""
    plain_ok = (
        len(value) > 0
        and value == value.strip()
        and ": " not in value
        and " #" not in value
        and not value.endswith(":")
        and value[0] not in "-?:,[]{}#&*!|>'\"%@`"
        and not any(unicodedata.category(c) == "Cc" for c in value)
    )
    if plain_ok:
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


# --- Paths and messages ---------------------------------------------------------

def full_path(path):
    return os.path.abspath(path)


def path_key(path):
    """Case-insensitive identity for a full path (mirrors the C# OrdinalIgnoreCase sets)."""
    return os.path.normcase(os.path.abspath(path)).lower()


def is_under(root_full, full):
    root = root_full.rstrip("/\\")
    if path_key(full) == path_key(root):
        return True
    try:
        rel = os.path.relpath(full, root)
    except ValueError:
        return False
    return rel != "." and not rel.startswith("..") and not os.path.isabs(rel)


def is_raw_artifact(kb_root_full, full):
    """True when a path is below a directory named `raw` in the KB."""
    try:
        rel = os.path.relpath(full, kb_root_full)
    except ValueError:
        return False
    return any(seg.lower() == "raw" for seg in re.split(r"[\\/]", rel) if seg)


def rel(kb_root_full, full):
    return os.path.relpath(full, kb_root_full).replace("\\", "/")


def pyrepr(s):
    """Python-style repr for quoted values in messages (same as the C# server's)."""
    quote = '"' if ("'" in s and '"' not in s) else "'"
    out = [quote]
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ch == quote:
            out.append("\\" + ch)
        else:
            out.append(ch)
    out.append(quote)
    return "".join(out)


def read_text(path):
    """Reads a file like .NET File.ReadAllText: BOM stripped, line endings kept."""
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        return f.read()


def write_text(path, text):
    """Writes UTF-8 without a BOM, line endings exactly as given."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
