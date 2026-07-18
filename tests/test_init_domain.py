"""Tests for the kb-init-domain scaffolder (init_domain.py)."""


def test_scaffolds_expected_files(empty_kb, run_script):
    proc = run_script("init", "--kb-root", empty_kb, "--slug", "billing",
                      "--title", "Billing", "--description", "Invoices and payments.")
    assert proc.returncode == 0, proc.stderr
    d = empty_kb / "billing"
    for name in ("domain.md", "index.md", "log.md", "raw/index.md"):
        assert (d / name).exists(), f"missing {name}"


def test_domain_md_carries_routing_metadata(empty_kb, run_script):
    run_script("init", "--kb-root", empty_kb, "--slug", "billing",
               "--title", "Billing", "--description", "Invoices and payments.",
               "--tags", "billing,payments")
    text = (empty_kb / "billing" / "domain.md").read_text()
    assert "type: Domain" in text
    assert "description: Invoices and payments." in text
    assert "slug: billing" in text
    assert "billing" in text and "payments" in text  # tags


def test_registers_in_root_catalog_and_log(empty_kb, run_script):
    run_script("init", "--kb-root", empty_kb, "--slug", "billing",
               "--title", "Billing", "--description", "Invoices and payments.")
    root_index = (empty_kb / "index.md").read_text()
    assert 'okf_version: "0.1"' in root_index
    assert "[Billing](billing/index.md)" in root_index
    root_log = (empty_kb / "log.md").read_text()
    assert "Billing" in root_log and "Established" in root_log


def test_slugifies_messy_names(empty_kb, run_script):
    run_script("init", "--kb-root", empty_kb, "--slug", "My Cool Domain!",
               "--title", "My Cool Domain", "--description", "Scope.")
    assert (empty_kb / "my-cool-domain" / "domain.md").exists()


def test_refuses_existing_domain_without_force(empty_kb, run_script):
    args = ("--kb-root", empty_kb, "--slug", "billing",
            "--title", "Billing", "--description", "Scope.")
    assert run_script("init", *args).returncode == 0
    clash = run_script("init", *args)
    assert clash.returncode == 2
    assert "already exists" in clash.stderr
    assert run_script("init", *args, "--force").returncode == 0


def test_multiple_domains_share_one_dated_log_block(empty_kb, run_script):
    run_script("init", "--kb-root", empty_kb, "--slug", "a",
               "--title", "A", "--description", "First.")
    run_script("init", "--kb-root", empty_kb, "--slug", "b",
               "--title", "B", "--description", "Second.")
    log = (empty_kb / "log.md").read_text()
    # Both creations recorded, under a single date heading (one "## " block).
    assert log.count("## ") == 1
    assert "[A](a/index.md)" in log and "[B](b/index.md)" in log


def test_created_domain_lints_clean(kb, run_script):
    # The `kb` fixture builds three domains; the bundle must be conformant.
    proc = run_script("lint", "--kb-root", kb)
    assert proc.returncode == 0, proc.stdout


# --- nested sub-domains ---------------------------------------------------

def test_nested_subdomain_registered_under_parent(empty_kb, run_script):
    run_script("init", "--kb-root", empty_kb, "--slug", "billing",
               "--title", "Billing", "--description", "Invoices and payments.")
    proc = run_script("init", "--kb-root", empty_kb, "--slug", "billing/eu",
                      "--title", "EU Billing", "--description", "EU VAT and SEPA.")
    assert proc.returncode == 0, proc.stderr
    assert (empty_kb / "billing" / "eu" / "domain.md").exists()
    assert "slug: billing/eu" in (empty_kb / "billing" / "eu" / "domain.md").read_text()
    parent_index = (empty_kb / "billing" / "index.md").read_text()
    assert "# Sub-domains" in parent_index
    assert "[EU Billing](eu/index.md)" in parent_index
    parent_log = (empty_kb / "billing" / "log.md").read_text()
    assert "sub-domain" in parent_log and "EU Billing" in parent_log
    # A sub-domain is reached through its parent, not the root catalog.
    assert "billing/eu" not in (empty_kb / "index.md").read_text()


def test_nested_requires_existing_parent(empty_kb, run_script):
    proc = run_script("init", "--kb-root", empty_kb, "--slug", "shipping/intl",
                      "--title", "Intl", "--description", "x")
    assert proc.returncode == 2
    assert "parent domain" in proc.stderr


def test_parent_flag_matches_path_slug(empty_kb, run_script):
    run_script("init", "--kb-root", empty_kb, "--slug", "billing",
               "--title", "Billing", "--description", "Invoices.")
    proc = run_script("init", "--kb-root", empty_kb, "--parent", "billing",
                      "--slug", "eu", "--title", "EU", "--description", "EU rules.")
    assert proc.returncode == 0, proc.stderr
    assert (empty_kb / "billing" / "eu" / "domain.md").exists()


def test_deeply_nested_bundle_lints_clean(empty_kb, run_script):
    run_script("init", "--kb-root", empty_kb, "--slug", "billing",
               "--title", "Billing", "--description", "Invoices.")
    run_script("init", "--kb-root", empty_kb, "--slug", "billing/eu",
               "--title", "EU", "--description", "EU rules.")
    run_script("init", "--kb-root", empty_kb, "--slug", "billing/eu/vat",
               "--title", "EU VAT", "--description", "VAT rate tables.")
    assert (empty_kb / "billing" / "eu" / "vat" / "domain.md").exists()
    assert run_script("lint", "--kb-root", empty_kb).returncode == 0
