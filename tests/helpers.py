"""Shared helpers for the knowledge-base test suite.

Tests drive the four KB scripts as subprocesses against hermetic temporary
knowledge bases, so they exercise the real command-line entry points (exit
codes, JSON output) rather than internals — which keeps them robust to
refactors of the scripts' guts.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / ".claude" / "skills"
AGENTS = REPO_ROOT / ".claude" / "agents"
REFERENCES = REPO_ROOT / "references"

SCRIPTS = {
    "init": SKILLS / "kb-init-domain" / "scripts" / "init_domain.py",
    "detect": SKILLS / "kb-ingest" / "scripts" / "detect_domain.py",
    "search": SKILLS / "kb-search" / "scripts" / "kb_search.py",
    "lint": SKILLS / "kb-lint" / "scripts" / "kb_lint.py",
}

SKILL_NAMES = ["kb-init-domain", "kb-ingest", "kb-search", "kb-lint"]

# (slug, title, description, tags) for the standard multi-domain test fixture.
DOMAINS = [
    ("billing", "Billing & Invoicing",
     "How invoices are generated, paid, refunded, and dunned for customer accounts.",
     "billing,payments,invoices,refunds"),
    ("infra", "Infrastructure",
     "Kubernetes clusters, deployments, networking, and CI/CD pipelines.",
     "kubernetes,deploy,networking,ci"),
    ("auth", "Authentication",
     "Login, OAuth, sessions, tokens, and password resets.",
     "auth,oauth,sessions,tokens"),
]


def run(script, *args, cwd=None):
    """Run a KB script by key, returning the CompletedProcess."""
    return subprocess.run(
        [sys.executable, str(SCRIPTS[script]), *[str(a) for a in args]],
        capture_output=True, text=True, cwd=cwd,
    )


def write_md(path: Path, meta: dict, body: str = "") -> None:
    """Write a markdown file with YAML frontmatter built from `meta`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    for key, val in meta.items():
        if isinstance(val, (list, tuple)):
            lines.append(f"{key}: [{', '.join(str(v) for v in val)}]")
        else:
            lines.append(f"{key}: {val}")
    lines += ["---", "", body, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def extract_frontmatter(text: str) -> dict:
    """Parse the frontmatter of a markdown file, folding block scalars (>-, |).

    Enough to assert on `name`/`description`/`tools` in SKILL.md and agent files.
    """
    assert text.startswith("---"), "file has no frontmatter block"
    end = text.index("\n---", 3)
    meta, key = {}, None
    for line in text[3:end].splitlines():
        if not line.strip():
            continue
        if line[:1] not in (" ", "\t") and ":" in line:
            k, _, v = line.partition(":")
            key = k.strip()
            v = v.strip()
            meta[key] = "" if v in (">", ">-", "|", "|-", "") else v
        elif key is not None and line[:1] in (" ", "\t"):
            meta[key] = (meta.get(key, "") + " " + line.strip()).strip()
    return meta


def load_script_module(script_key: str):
    """Import a script file as a module to unit-test its pure functions."""
    path = SCRIPTS[script_key]
    spec = importlib.util.spec_from_file_location(f"kb_{script_key}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
