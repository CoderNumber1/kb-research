"""Tests for the PowerShell plugin variant (okf-knowledge-base-powershell).

Structural checks always run. The parity tests — asserting the pwsh scripts
produce byte-identical JSON to the Python scripts — run only where `pwsh` is
installed, and skip cleanly otherwise (e.g. CI without PowerShell).
"""
import json
import re
import shutil
import subprocess
import sys

import pytest

from helpers import (DOMAINS, POWERSHELL_ROOT, PLUGIN_ROOT, SKILL_NAMES,
                     extract_frontmatter, run, write_md)

SKILLS = POWERSHELL_ROOT / "skills"
SCRIPTS = POWERSHELL_ROOT / "scripts"
PWSH = shutil.which("pwsh")
needs_pwsh = pytest.mark.skipif(PWSH is None, reason="pwsh not installed")

PS_SCRIPTS = ["KbCommon.psm1", "init_domain.ps1", "detect_domain.ps1",
              "kb_search.ps1", "kb_lint.ps1", "kb_detect.ps1"]


# --- structural -----------------------------------------------------------

def test_manifest_valid():
    data = json.loads((POWERSHELL_ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert data["name"] == "okf-knowledge-base-powershell"
    assert data.get("description")


def test_ships_powershell_scripts_and_no_python():
    for s in PS_SCRIPTS:
        assert (SCRIPTS / s).exists(), f"missing {s}"
    assert list(POWERSHELL_ROOT.rglob("*.py")) == []


def test_has_the_same_skill_set():
    found = {p.parent.name for p in SKILLS.glob("*/SKILL.md")}
    assert set(SKILL_NAMES) <= found


@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_skill_frontmatter_valid(skill):
    fm = extract_frontmatter((SKILLS / skill / "SKILL.md").read_text())
    assert fm.get("name") == skill
    assert len(fm.get("description", "")) > 40


@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_skill_calls_pwsh_not_python(skill):
    text = (SKILLS / skill / "SKILL.md").read_text()
    assert "python3" not in text and not re.search(r"\.py\b", text)
    for script in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/scripts/(\S+?\.ps1)", text):
        assert (SCRIPTS / script).exists(), f"{skill} references missing {script}"


def test_hook_runs_pwsh_detector():
    hooks = json.loads((POWERSHELL_ROOT / "hooks" / "hooks.json").read_text())
    cmd = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "kb_detect.ps1" in cmd and "pwsh" in cmd and "CLAUDE_PLUGIN_ROOT" in cmd


def test_reference_docs_present():
    for name in ("okf-spec.md", "llm-wiki.md"):
        assert (POWERSHELL_ROOT / "references" / name).stat().st_size > 200


# --- behavioural parity (requires pwsh) -----------------------------------

def _ps(script, *args, cwd=None):
    return subprocess.run(
        [PWSH, "-NoProfile", "-File", str(SCRIPTS / script), *map(str, args)],
        capture_output=True, text=True, cwd=cwd)


def _norm(txt):
    d = json.loads(txt)
    if isinstance(d, dict):
        d.pop("kb_root", None)
    return d


@pytest.fixture
def kb_with_pages_pwsh(kb_with_pages):
    return kb_with_pages


@needs_pwsh
def test_detect_parity(kb):
    for q in ["customer refund on monthly invoice dunning",
              "rolling kubernetes deployment ci pipeline", "oauth token login session"]:
        py = run("detect", "--kb-root", kb, "--query", q, "--json")
        ps = _ps("detect_domain.ps1", "--kb-root", kb, "--query", q, "--json")
        assert py.returncode == ps.returncode
        assert _norm(py.stdout) == _norm(ps.stdout), q


@needs_pwsh
def test_search_parity(kb_with_pages):
    for q in ["refund processing", "dunning overdue invoices", "kubernetes deploy"]:
        py = run("search", q, "--kb-root", kb_with_pages, "--json")
        ps = _ps("kb_search.ps1", q, "--kb-root", kb_with_pages, "--json")
        assert _norm(py.stdout) == _norm(ps.stdout), q


@needs_pwsh
def test_lint_parity(kb_with_pages):
    py = run("lint", "--kb-root", kb_with_pages, "--json")
    ps = _ps("kb_lint.ps1", "--kb-root", kb_with_pages, "--json")
    assert py.returncode == ps.returncode
    assert json.loads(py.stdout) == json.loads(ps.stdout)


@needs_pwsh
def test_lint_parity_with_faults(kb):
    write_md(kb / "billing" / "bad.md", {"title": "No type"}, "[x](/billing/ghost.md)")
    write_md(kb / "billing" / "lonely.md",
             {"type": "Reference", "title": "Lonely", "description": "x",
              "timestamp": "2026-07-18T00:00:00Z"}, "no inbound links")
    py = run("lint", "--kb-root", kb, "--json")
    ps = _ps("kb_lint.ps1", "--kb-root", kb, "--json")
    assert py.returncode == ps.returncode == 1
    assert json.loads(py.stdout) == json.loads(ps.stdout)


@needs_pwsh
def test_init_domain_creates_clean_bundle(tmp_path):
    root = tmp_path / "kb"
    p = _ps("init_domain.ps1", "--kb-root", root, "--slug", "billing",
            "--title", "Billing", "--description", "Invoices and payments.")
    assert p.returncode == 0, p.stderr
    assert (root / "billing" / "domain.md").exists()
    # Both linters agree the pwsh-created bundle is clean.
    assert run("lint", "--kb-root", root).returncode == 0
    assert _ps("kb_lint.ps1", "--kb-root", root).returncode == 0
