"""Tests for the plugin packaging: manifests, the SessionStart detector hook,
and knowledge-base autodetection from the working directory."""
import json
import subprocess
import sys

from helpers import PLUGIN_ROOT, REPO_ROOT, SCRIPTS


def test_plugin_manifest_valid():
    data = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert data["name"] == "okf-knowledge-base"
    assert data.get("description")


def test_marketplace_points_at_plugin():
    mkt = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text())
    assert mkt.get("name")
    sources = [p["source"] for p in mkt["plugins"]]
    assert "./plugins/okf-knowledge-base" in sources
    for p in mkt["plugins"]:
        manifest = REPO_ROOT / p["source"] / ".claude-plugin" / "plugin.json"
        assert manifest.exists(), f"marketplace source missing manifest: {p['source']}"


def test_hooks_register_sessionstart_detector():
    hooks = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text())
    cmd = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "kb_detect.py" in cmd and "CLAUDE_PLUGIN_ROOT" in cmd


def test_autodetects_kb_from_working_dir(kb, run_script):
    # No --kb-root: the script must find kb/ under the working directory.
    proc = run_script("detect", "--list", "--json", cwd=kb.parent)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert {d["slug"] for d in data["domains"]} == {"billing", "infra", "auth"}


def test_scripts_error_cleanly_when_no_kb(tmp_path, run_script):
    proc = run_script("lint", cwd=tmp_path)
    assert proc.returncode == 2
    assert "no knowledge base" in (proc.stderr + proc.stdout).lower()


def test_session_hook_emits_context_when_kb_present(kb):
    proc = subprocess.run([sys.executable, str(SCRIPTS["kb_detect"])],
                          cwd=str(kb.parent), capture_output=True, text=True)
    assert proc.returncode == 0
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    assert "knowledge base" in out["additionalContext"].lower()
    assert "billing" in out["additionalContext"]


def test_session_hook_silent_without_kb(tmp_path):
    proc = subprocess.run([sys.executable, str(SCRIPTS["kb_detect"])],
                          cwd=str(tmp_path), capture_output=True, text=True)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
