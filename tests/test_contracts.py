"""Contract tests for the skills, the agent, and the committed knowledge base.

Skills and the agent are instructions for an LLM, not executable code, so their
*behavior* can't be unit-tested deterministically. What we can lock down are the
invariants that keep them wired up correctly: valid frontmatter, every script
path they cite exists and runs, referenced skills/reference files exist, and the
committed bundle stays OKF-conformant. These catch the realistic failure mode —
a doc drifting out of sync with the code it points at.
"""
import re

import pytest

from helpers import (AGENTS, REFERENCES, REPO_ROOT, SCRIPTS_DIR, SKILL_NAMES,
                     SKILLS, extract_frontmatter, run)

SCRIPT_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/scripts/(\w+\.py)")


def test_expected_skills_present():
    found = {p.parent.name for p in SKILLS.glob("*/SKILL.md")}
    assert set(SKILL_NAMES) <= found


@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_skill_frontmatter_valid(skill):
    text = (SKILLS / skill / "SKILL.md").read_text()
    fm = extract_frontmatter(text)
    assert fm.get("name") == skill, f"name must equal directory ({skill})"
    assert len(fm.get("description", "")) > 40, "description should be substantive"


@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_skill_referenced_scripts_exist(skill):
    text = (SKILLS / skill / "SKILL.md").read_text()
    refs = SCRIPT_REF.findall(text)
    assert refs, f"{skill} should reference at least one plugin script"
    for script in refs:
        assert (SCRIPTS_DIR / script).exists(), \
            f"{skill} references missing script {script}"


def test_all_scripts_run_help_cleanly():
    # Every KB script must at least parse args and print help without error.
    for key in ("init", "detect", "search", "lint"):
        proc = run(key, "--help")
        assert proc.returncode == 0, f"{key} --help failed: {proc.stderr}"
        assert "usage" in proc.stdout.lower()


def test_agent_frontmatter_and_wiring():
    text = (AGENTS / "knowledge-curator.md").read_text()
    fm = extract_frontmatter(text)
    assert fm.get("name") == "knowledge-curator"
    assert len(fm.get("description", "")) > 40
    assert fm.get("tools"), "agent should declare its tools"
    # The agent points at all four skills and the reference docs — they must exist.
    for skill in SKILL_NAMES:
        assert skill in text, f"agent does not mention {skill}"
    assert (REFERENCES / "okf-spec.md").exists()
    assert (REFERENCES / "llm-wiki.md").exists()


def test_reference_docs_present_and_nonempty():
    for name in ("okf-spec.md", "llm-wiki.md"):
        path = REFERENCES / name
        assert path.exists() and path.stat().st_size > 200, name


def test_committed_kb_is_conformant():
    # The knowledge base checked into the repo must itself lint clean.
    proc = run("lint", "--kb-root", REPO_ROOT / "kb")
    assert proc.returncode == 0, proc.stdout


def test_schema_guide_present():
    assert (REPO_ROOT / "CLAUDE.md").exists()
