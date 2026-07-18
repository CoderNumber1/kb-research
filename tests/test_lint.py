"""Tests for kb-lint (kb_lint.py): OKF conformance + wiki-hygiene rules."""
from helpers import write_md

TS = "2026-07-18T00:00:00Z"


def codes(data):
    return {f["code"] for f in data["findings"]}


def levels(data, code):
    return {f["level"] for f in data["findings"] if f["code"] == code}


def test_clean_bundle_passes(kb, run_json):
    data, proc = run_json("lint", "--kb-root", kb, "--json")
    assert proc.returncode == 0
    assert data["conformant"] is True
    assert data["findings"] == []


def test_populated_bundle_passes(kb_with_pages, run_json):
    data, proc = run_json("lint", "--kb-root", kb_with_pages, "--json")
    assert proc.returncode == 0, data["findings"]
    assert data["conformant"] is True


def test_missing_type_is_conformance_error(kb, run_json):
    write_md(kb / "billing" / "bad.md",
             {"title": "No type here", "timestamp": TS}, "# Body\nlinked from nowhere.")
    # give it an inbound link so we isolate the type error
    write_md(kb / "billing" / "hub.md",
             {"type": "Reference", "title": "Hub", "description": "Links out.",
              "timestamp": TS}, "See [bad](/billing/bad.md).")
    data, proc = run_json("lint", "--kb-root", kb, "--domain", "billing", "--json")
    assert proc.returncode == 1
    assert data["conformant"] is False
    assert "type" in codes(data)
    assert levels(data, "type") == {"ERROR"}


def test_unparseable_frontmatter_is_error(kb, run_json):
    (kb / "billing" / "raw.md").write_text("no frontmatter at all\n", encoding="utf-8")
    data, proc = run_json("lint", "--kb-root", kb, "--domain", "billing", "--json")
    assert proc.returncode == 1
    assert "frontmatter" in codes(data)


def test_broken_link_warning(kb, run_json):
    write_md(kb / "billing" / "a.md",
             {"type": "Reference", "title": "A", "description": "x", "timestamp": TS},
             "Link to [ghost](/billing/does-not-exist.md).")
    data, _ = run_json("lint", "--kb-root", kb, "--domain", "billing", "--json")
    assert "broken-link" in codes(data)


def test_orphan_warning(kb, run_json):
    write_md(kb / "billing" / "lonely.md",
             {"type": "Reference", "title": "Lonely", "description": "x", "timestamp": TS},
             "# Body\nNothing links here.")
    data, _ = run_json("lint", "--kb-root", kb, "--domain", "billing", "--json")
    assert "orphan" in codes(data)


def test_index_drift_then_fix(kb, run_script, run_json):
    write_md(kb / "billing" / "p1.md",
             {"type": "Reference", "title": "P1", "description": "one", "timestamp": TS},
             "See [p2](/billing/p2.md).")
    write_md(kb / "billing" / "p2.md",
             {"type": "Reference", "title": "P2", "description": "two", "timestamp": TS},
             "See [p1](/billing/p1.md).")
    before, _ = run_json("lint", "--kb-root", kb, "--domain", "billing", "--json")
    assert "index-drift" in codes(before)
    fix = run_script("lint", "--kb-root", kb, "--domain", "billing", "--fix-index")
    assert fix.returncode == 0
    index_text = (kb / "billing" / "index.md").read_text()
    assert "[P1](p1.md)" in index_text and "[P2](p2.md)" in index_text
    after, _ = run_json("lint", "--kb-root", kb, "--domain", "billing", "--json")
    assert "index-drift" not in codes(after)


def test_duplicate_title_warning(kb, run_json):
    for name in ("d1.md", "d2.md"):
        write_md(kb / "billing" / name,
                 {"type": "Reference", "title": "Same Title",
                  "description": "x", "timestamp": TS},
                 "[peer](/billing/d1.md) [peer2](/billing/d2.md)")
    data, _ = run_json("lint", "--kb-root", kb, "--domain", "billing", "--json")
    assert "dup-title" in codes(data)


def test_non_iso_log_date_warning(kb, run_json):
    (kb / "billing" / "log.md").write_text(
        "# Log\n\n## July 5th 2026\n* did a thing\n", encoding="utf-8")
    data, _ = run_json("lint", "--kb-root", kb, "--domain", "billing", "--json")
    assert "log-date" in codes(data)


def test_bad_timestamp_warning(kb, run_json):
    write_md(kb / "billing" / "t.md",
             {"type": "Reference", "title": "T", "description": "x",
              "timestamp": "not-a-date"},
             "[self-ish](/billing/t.md)")
    data, _ = run_json("lint", "--kb-root", kb, "--domain", "billing",
                       "--stale-days", "30", "--json")
    assert "timestamp" in codes(data)


def test_frontmatter_in_nonroot_index_is_error(kb, run_json):
    (kb / "billing" / "index.md").write_text(
        "---\ntype: NotAllowed\n---\n\n# Billing\n", encoding="utf-8")
    data, proc = run_json("lint", "--kb-root", kb, "--domain", "billing", "--json")
    assert proc.returncode == 1
    assert "index-frontmatter" in codes(data)


def test_missing_recommended_fields_is_info(kb, run_json):
    write_md(kb / "billing" / "sparse.md", {"type": "Reference"},
             "[peer](/billing/sparse.md)")
    data, _ = run_json("lint", "--kb-root", kb, "--domain", "billing", "--json")
    assert "recommended" in codes(data)
    assert levels(data, "recommended") == {"INFO"}
