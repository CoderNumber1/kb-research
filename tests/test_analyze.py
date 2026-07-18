"""Tests for kb_analyze.py — the consolidation-candidate finder behind
kb-consolidate."""
from helpers import write_md

TS = "2026-07-18T00:00:00Z"
BODY = ("A refund returns money to the customer. Refunds are issued for failed "
        "charges, disputed charges, and chargebacks. Finance approves refunds "
        "over one thousand dollars. Refunds settle in five business days.")


def seed_dupes(kb):
    """Two near-identical refund pages in `billing`, plus a third copy in
    `auth` — a within-domain twin and a cross-domain duplicate."""
    write_md(kb / "billing" / "refunds.md",
             {"type": "Reference", "title": "Refund processing",
              "description": "How refunds are issued to customers after a failed "
              "or disputed charge.", "tags": ["refunds", "payments"], "timestamp": TS},
             "# Overview\n" + BODY)
    write_md(kb / "billing" / "issuing-refunds.md",
             {"type": "Reference", "title": "Issuing refunds",
              "description": "The process for issuing a refund to a customer after "
              "a failed or disputed charge.", "tags": ["refunds", "payments"], "timestamp": TS},
             "# Steps\n" + BODY)
    write_md(kb / "auth" / "refund-requests.md",
             {"type": "Playbook", "title": "Handling refund requests",
              "description": "How support issues a refund to a customer after a "
              "failed or disputed charge.", "tags": ["refunds"], "timestamp": TS},
             "# Steps\n" + BODY)


def test_finds_within_domain_twins(kb, run_json):
    seed_dupes(kb)
    data, _ = run_json("analyze", "--kb-root", kb, "--json")
    groups = [set(g["members"]) for g in data["within_domain"]]
    assert {"billing/issuing-refunds.md", "billing/refunds.md"} in groups


def test_finds_cross_domain_duplicate(kb, run_json):
    seed_dupes(kb)
    data, _ = run_json("analyze", "--kb-root", kb, "--json")
    assert data["cross_domain"], "expected a cross-domain group"
    g = data["cross_domain"][0]
    assert "auth/refund-requests.md" in g["members"]
    assert len(g["domains"]) > 1 and g["scope"] == "cross-domain"
    assert g["est_saving_bytes"] > 0


def test_domain_scope_limits_to_within(kb, run_json):
    seed_dupes(kb)
    data, _ = run_json("analyze", "--kb-root", kb, "--domain", "billing", "--json")
    assert data["cross_domain"] == []
    assert any(len(g["members"]) >= 2 for g in data["within_domain"])


def test_high_threshold_filters_everything(kb, run_json):
    seed_dupes(kb)
    data, _ = run_json("analyze", "--kb-root", kb, "--min-similarity", "0.99", "--json")
    assert data["within_domain"] == [] and data["cross_domain"] == []


def test_no_candidates_on_clean_kb(kb, run_json):
    # Domains only, no concept pages -> nothing to consolidate.
    data, proc = run_json("analyze", "--kb-root", kb, "--json")
    assert proc.returncode == 0
    assert data["pages_analyzed"] == 0
    assert data["within_domain"] == [] and data["cross_domain"] == []


def test_no_kb_errors(tmp_path, run_script):
    proc = run_script("analyze", cwd=tmp_path)
    assert proc.returncode == 2
    assert "no knowledge base" in (proc.stderr + proc.stdout).lower()
