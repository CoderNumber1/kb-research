"""Tests for the scriptless plugin variant (okf-knowledge-base-scriptless).

Its defining property is that it does the work with built-in tools and ships
*no* scripts, so these tests lock that in: no script files, skills that don't
call any, a valid manifest and inline-shell detector hook, and parity of the
skill/agent set with the scripts variant.
"""
import json
import re
import subprocess

import pytest

from helpers import REPO_ROOT, SCRIPTLESS_ROOT, SKILL_NAMES, extract_frontmatter

SKILLS = SCRIPTLESS_ROOT / "skills"
AGENTS = SCRIPTLESS_ROOT / "agents"


def test_manifest_valid():
    data = json.loads((SCRIPTLESS_ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert data["name"] == "okf-knowledge-base-scriptless"
    assert data.get("description")


def test_marketplace_lists_both_plugins():
    mkt = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text())
    names = {p["name"] for p in mkt["plugins"]}
    assert names == {"okf-knowledge-base", "okf-knowledge-base-scriptless"}
    for p in mkt["plugins"]:
        assert (REPO_ROOT / p["source"] / ".claude-plugin" / "plugin.json").exists()


def test_ships_no_scripts():
    # The whole point of this variant: no bundled script files anywhere in it.
    py = list(SCRIPTLESS_ROOT.rglob("*.py"))
    assert py == [], f"scriptless plugin must ship no scripts, found: {py}"
    assert not (SCRIPTLESS_ROOT / "scripts").exists()


def test_has_the_same_skill_set():
    found = {p.parent.name for p in SKILLS.glob("*/SKILL.md")}
    assert set(SKILL_NAMES) <= found


@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_skill_frontmatter_valid(skill):
    fm = extract_frontmatter((SKILLS / skill / "SKILL.md").read_text())
    assert fm.get("name") == skill
    assert len(fm.get("description", "")) > 40


@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_skill_calls_no_scripts(skill):
    text = (SKILLS / skill / "SKILL.md").read_text()
    assert "${CLAUDE_PLUGIN_ROOT}/scripts" not in text
    # No invocation of a python script (references/*.md mentions are fine).
    assert not re.search(r"python3?\s+\S+\.py", text)
    assert "/scripts/" not in text


def test_agent_valid_and_wired():
    fm = extract_frontmatter((AGENTS / "knowledge-curator.md").read_text())
    assert fm.get("name") == "knowledge-curator"
    assert fm.get("tools")
    text = (AGENTS / "knowledge-curator.md").read_text()
    for skill in SKILL_NAMES:
        assert skill in text


def test_reference_docs_present():
    for name in ("okf-spec.md", "llm-wiki.md"):
        path = SCRIPTLESS_ROOT / "references" / name
        assert path.exists() and path.stat().st_size > 200


def _hook_command():
    hooks = json.loads((SCRIPTLESS_ROOT / "hooks" / "hooks.json").read_text())
    return hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]


def test_hook_is_inline_shell_not_a_script():
    cmd = _hook_command()
    assert "SessionStart" in cmd and ".py" not in cmd


def test_hook_emits_context_when_kb_present(tmp_path):
    (tmp_path / "kb").mkdir()
    (tmp_path / "kb" / "index.md").write_text('---\nokf_version: "0.1"\n---\n# KB\n')
    proc = subprocess.run(_hook_command(), shell=True, cwd=str(tmp_path),
                          capture_output=True, text=True)
    assert proc.returncode == 0
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    assert "knowledge base" in out["additionalContext"].lower()


def test_hook_silent_without_kb(tmp_path):
    proc = subprocess.run(_hook_command(), shell=True, cwd=str(tmp_path),
                          capture_output=True, text=True)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
