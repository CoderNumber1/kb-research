"""Tests for domain auto-detection (detect_domain.py) — the routing that
kb-ingest relies on to file a source into the right domain."""
import pytest

from helpers import load_script_module


def test_list_reports_all_domains(kb, run_json):
    data, proc = run_json("detect", "--kb-root", kb, "--list", "--json")
    assert proc.returncode == 0
    slugs = {d["slug"] for d in data["domains"]}
    assert slugs == {"billing", "infra", "auth"}


@pytest.mark.parametrize("query,expected", [
    ("customer requested a refund on their monthly invoice, dunning email failed",
     "billing"),
    ("rolling deployment to the production kubernetes cluster failed on the CI pipeline",
     "infra"),
    ("oauth token refresh returns 401 during login session", "auth"),
])
def test_routes_source_to_correct_domain(kb, run_json, query, expected):
    data, proc = run_json("detect", "--kb-root", kb, "--query", query, "--json")
    assert proc.returncode == 0
    assert data["confidence"] in ("high", "medium")
    assert data["recommendation"] == expected
    assert data["ranking"][0]["slug"] == expected


def test_unrelated_source_yields_low_confidence_no_match(kb, run_json):
    data, _ = run_json("detect", "--kb-root", kb, "--json",
                       "--query", "quarterly marketing campaign analytics dashboard")
    assert data["confidence"] == "low"
    assert data["recommendation"] is None


def test_empty_kb_exits_nonzero(empty_kb, run_script):
    proc = run_script("detect", "--kb-root", empty_kb, "--query", "anything")
    assert proc.returncode == 3
    assert "No domains found" in proc.stdout


def test_stemmer_unifies_word_families():
    mod = load_script_module("detect")
    # Different surface forms must collapse to a shared root, or routing misses.
    assert mod.stem("webhooks") == mod.stem("webhook")
    assert mod.stem("verification") == mod.stem("verified") == mod.stem("verify")
    assert mod.stem("retries") == mod.stem("retried") == mod.stem("retry")
    assert mod.stem("deliveries") == mod.stem("delivered") == mod.stem("delivery")


def test_tokenize_drops_stopwords_and_short_tokens():
    mod = load_script_module("detect")
    toks = mod.tokenize("The a of an invoice to be paid")
    assert "the" not in toks and "of" not in toks and "an" not in toks
    assert mod.stem("invoice") in toks
