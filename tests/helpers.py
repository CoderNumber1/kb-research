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
PLUGIN_ROOT = REPO_ROOT / "plugins" / "okf-knowledge-base"            # python scripts variant
SCRIPTLESS_ROOT = REPO_ROOT / "plugins" / "okf-knowledge-base-scriptless"
POWERSHELL_ROOT = REPO_ROOT / "plugins" / "okf-knowledge-base-powershell"
SKILLS = PLUGIN_ROOT / "skills"
AGENTS = PLUGIN_ROOT / "agents"
REFERENCES = PLUGIN_ROOT / "references"
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"

SCRIPTS = {
    "init": SCRIPTS_DIR / "init_domain.py",
    "detect": SCRIPTS_DIR / "detect_domain.py",
    "search": SCRIPTS_DIR / "kb_search.py",
    "lint": SCRIPTS_DIR / "kb_lint.py",
    "analyze": SCRIPTS_DIR / "kb_analyze.py",
    "kb_detect": SCRIPTS_DIR / "kb_detect.py",
}

SKILL_NAMES = ["kb-init-domain", "kb-ingest", "kb-search", "kb-lint", "kb-consolidate"]

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


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # so intra-package imports (kb_common) resolve
    spec.loader.exec_module(mod)
    return mod


def load_script_module(script_key: str):
    """Import a script file as a module to unit-test its pure functions."""
    return _load(SCRIPTS[script_key], f"kb_{script_key}")


def load_common():
    """Import the shared kb_common module for unit tests."""
    return _load(SCRIPTS_DIR / "kb_common.py", "kb_common")
