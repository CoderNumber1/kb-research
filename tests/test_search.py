"""Tests for kb-search retrieval (kb_search.py)."""
from helpers import write_md


def test_finds_relevant_page_scoped_to_domain(kb_with_pages, run_json):
    data, proc = run_json("search", "refund processing", "--kb-root",
                          kb_with_pages, "--domain", "billing", "--json")
    assert proc.returncode == 0
    paths = [h["path"] for h in data["hits"]]
    assert "billing/refunds.md" in paths
    assert data["hits"][0]["path"] == "billing/refunds.md"


def test_title_match_outranks_body_only_match(kb, run_json):
    # Two pages: one with the term in the title, one only deep in the body.
    write_md(kb / "billing" / "widget.md",
             {"type": "Reference", "title": "Chargeback handling",
              "description": "Dealing with chargebacks.", "timestamp": "2026-07-18T00:00:00Z"},
             "# Overview\nChargeback disputes are resolved here.")
    write_md(kb / "billing" / "other.md",
             {"type": "Reference", "title": "Refund basics",
              "description": "Refund overview.", "timestamp": "2026-07-18T00:00:00Z"},
             "# Notes\nOccasionally a chargeback is mentioned in passing.")
    data, _ = run_json("search", "chargeback", "--kb-root", kb,
                       "--domain", "billing", "--json")
    assert data["hits"][0]["path"] == "billing/widget.md"


def test_type_filter_restricts_results(kb_with_pages, run_json):
    data, _ = run_json("search", "dunning", "--kb-root", kb_with_pages,
                       "--type", "Playbook", "--json")
    assert data["hits"], "expected at least one Playbook hit"
    assert all(h["type"] == "Playbook" for h in data["hits"])


def test_no_matches_is_graceful(kb_with_pages, run_json):
    data, proc = run_json("search", "zzzznotachance", "--kb-root",
                          kb_with_pages, "--json")
    assert proc.returncode == 0
    assert data["hits"] == []


def test_stemming_recall_across_forms(kb, run_json):
    write_md(kb / "billing" / "retry.md",
             {"type": "Reference", "title": "Charge retry logic",
              "description": "How charges are retried.", "timestamp": "2026-07-18T00:00:00Z"},
             "# Policy\nFailed charges are retried three times with backoff.")
    # Query uses a different inflection than the page body ("retried").
    data, _ = run_json("search", "retrying", "--kb-root", kb,
                       "--domain", "billing", "--json")
    assert any(h["path"] == "billing/retry.md" for h in data["hits"])


def test_raw_sources_excluded_unless_requested(kb, run_json):
    write_md(kb / "billing" / "raw" / "vendor-doc.md",
             {"type": "Source", "title": "Vendor doc",
              "description": "Snapshot.", "resource": "https://example.com",
              "timestamp": "2026-07-18T00:00:00Z"},
             "# Source\nThe magic keyword is quixotic and appears only here.")
    default, _ = run_json("search", "quixotic", "--kb-root", kb,
                          "--domain", "billing", "--json")
    assert default["hits"] == []
    with_raw, _ = run_json("search", "quixotic", "--kb-root", kb,
                           "--domain", "billing", "--include-raw", "--json")
    assert any("raw/vendor-doc.md" in h["path"] for h in with_raw["hits"])
