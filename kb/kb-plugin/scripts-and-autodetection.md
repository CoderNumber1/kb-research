---
type: Reference
title: Scripts, KB autodetection, and nested sub-domains
description: The shared helper library, how the KB root is found, the SessionStart detector, and nested sub-domain support.
tags: [plugin, scripts, autodetection, sub-domains, hooks]
timestamp: 2026-07-18T00:00:00Z
---

# Scripts

The script variants share a small library (`kb_common.py` / `KbCommon.psm1`):
frontmatter parser, stemmer/tokenizer, and `find_kb_root`. The operation scripts
(`init_domain`, `detect_domain`, `kb_search`, `kb_lint`, `kb_analyze`,
`kb_detect`) share one CLI (`--kb-root`, `--query`, `--json`, `--domain`,
`--fix-index`, …) so all variants are drop-in comparable.

# KB autodetection

`find_kb_root` resolves the knowledge base in order: an explicit `--kb-root`,
then the `$KB_ROOT` env var, then a search from the working directory upward for
a bundle (a `kb/` child, or a directory whose `index.md` declares `okf_version`,
or one containing domain subdirectories). So the tools need no configuration
inside a project, and error cleanly when no KB is present.

# SessionStart detector hook

A `SessionStart` [hook](/claude-code/hooks-and-scopes.md) runs a detector
(`kb_detect.py` / `.ps1`, or an inline shell one-liner in the scriptless variant)
that emits `additionalContext` announcing a `kb/` bundle — and its domains — when
one is found in the working directory, and stays silent otherwise. This is what
makes the plugin "light up" only where a KB exists.

# Nested sub-domains

Domains nest to any depth (e.g. `billing/eu/vat`). A sub-domain is registered
under its parent's `index.md` (`# Sub-domains`) and `log.md`, not the root
catalog; `detect_domain` discovers domains recursively and ingest routes a source
to the **most specific** matching (sub-)domain. Back to [overview](overview.md).
