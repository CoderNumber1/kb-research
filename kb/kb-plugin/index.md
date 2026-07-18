# KB Plugin Architecture

Architecture of the okf-knowledge-base Claude Code plugins in this repo — the Python, PowerShell, and scriptless variants, their five skills, scripts, KB autodetection, nested sub-domains, and consolidation engine.

See [domain.md](domain.md) for scope and conventions.

# Concepts

* [The consolidation engine](consolidation-engine.md) - How kb_analyze finds duplicate/overlapping pages and how kb-consolidate merges them, recommend-then-apply.
* [Determinism and Python/PowerShell parity](determinism-and-parity.md) - Techniques and gotchas for making the PowerShell scripts produce byte-identical JSON to the Python scripts.
* [KB plugin — overview](overview.md) - This repo is a marketplace hosting three variants of an OKF/LLM-wiki knowledge-base plugin, dogfooded against the kb/ bundle.
* [Scripts, KB autodetection, and nested sub-domains](scripts-and-autodetection.md) - The shared helper library, how the KB root is found, the SessionStart detector, and nested sub-domain support.
* [The five skills](skills.md) - kb-init-domain, kb-ingest, kb-search, kb-lint, and kb-consolidate — what each operation does.
* [The three plugin variants](variants.md) - Python, PowerShell, and scriptless variants — how they differ and when to pick each, with benchmark findings.

# Sources

* [Raw sources](raw/) - immutable snapshots of ingested material.
