"""Pytest fixtures for the knowledge-base test suite."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import DOMAINS, run, write_md  # noqa: E402


@pytest.fixture
def run_script():
    """Return the subprocess runner (script key + args -> CompletedProcess)."""
    return run


@pytest.fixture
def run_json():
    """Run a script and parse its stdout as JSON; returns (data, proc)."""
    def _rj(script, *args):
        proc = run(script, *args)
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"{script} did not emit JSON (exit {proc.returncode}).\n"
                f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            ) from exc
        return data, proc
    return _rj


@pytest.fixture
def empty_kb(tmp_path):
    """A knowledge-base root directory that exists but has no domains."""
    root = tmp_path / "kb"
    root.mkdir()
    return root


@pytest.fixture
def kb(tmp_path):
    """A knowledge base with three domains and no concept pages (lints clean)."""
    root = tmp_path / "kb"
    for slug, title, desc, tags in DOMAINS:
        proc = run("init", "--kb-root", root, "--slug", slug,
                   "--title", title, "--description", desc, "--tags", tags)
        assert proc.returncode == 0, proc.stderr
    return root


@pytest.fixture
def kb_with_pages(kb):
    """The three-domain KB populated with reciprocally-linked concept pages.

    Each page has an inbound link (no orphans) and indexes are regenerated, so
    the resulting bundle lints clean — a realistic baseline for search/lint tests.
    """
    ts = "2026-07-18T00:00:00Z"
    write_md(kb / "billing" / "refunds.md",
             {"type": "Reference", "title": "Refund processing",
              "description": "How refunds are issued back to customers.",
              "tags": ["billing", "refunds"], "timestamp": ts},
             "# Overview\nA refund returns funds to the customer. Failed refunds "
             "roll into [dunning](/billing/dunning.md).")
    write_md(kb / "billing" / "dunning.md",
             {"type": "Playbook", "title": "Dunning policy",
              "description": "How overdue invoices are chased before write-off.",
              "tags": ["billing", "dunning"], "timestamp": ts},
             "# Steps\nRetry the charge, then email. See "
             "[refund processing](/billing/refunds.md) for reversals.")
    write_md(kb / "infra" / "deploy.md",
             {"type": "Reference", "title": "Deployment process",
              "description": "How services roll out to the cluster.",
              "tags": ["infra", "deploy"], "timestamp": ts},
             "# Overview\nRolling deploys to Kubernetes. Gated by the "
             "[CI pipeline](/infra/pipeline.md).")
    write_md(kb / "infra" / "pipeline.md",
             {"type": "Reference", "title": "CI pipeline",
              "description": "Build and test pipeline gating deploys.",
              "tags": ["infra", "ci"], "timestamp": ts},
             "# Overview\nRuns tests before a [deployment](/infra/deploy.md).")
    write_md(kb / "auth" / "oauth.md",
             {"type": "Reference", "title": "OAuth flow",
              "description": "How third-party OAuth login works.",
              "tags": ["auth", "oauth"], "timestamp": ts},
             "# Overview\nOAuth issues tokens for a [session](/auth/sessions.md).")
    write_md(kb / "auth" / "sessions.md",
             {"type": "Reference", "title": "Session management",
              "description": "How login sessions and tokens are tracked.",
              "tags": ["auth", "sessions"], "timestamp": ts},
             "# Overview\nSessions are created after [OAuth](/auth/oauth.md).")
    for slug in ("billing", "infra", "auth"):
        run("lint", "--kb-root", kb, "--domain", slug, "--fix-index")
    return kb
