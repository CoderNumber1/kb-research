---
name: kb-init-domain
description: >-
  Initialize a new domain (a self-contained subject area) inside the Open
  Knowledge Format knowledge base under kb/. Use this whenever the user wants to
  start tracking a NEW topic, subject, product area, project, or body of
  knowledge that does not yet have a home in the KB — e.g. "set up a domain for
  our billing system", "create a knowledge area for the payments API", "start a
  wiki section on onboarding", or when kb-ingest determines an incoming source
  belongs to a subject the KB does not cover yet. Scaffolds the domain's
  domain.md (scope + description used for auto-routing), index.md, log.md, and
  raw/, and registers it in the root catalog. Trigger this before ingesting
  sources for a brand-new topic.
---

# Initialize a Knowledge Base Domain

A **domain** is one OKF bundle subtree under `kb/<slug>/` — a self-contained area
of knowledge with its own sources, concept pages, index, and log. Domains are the
unit `kb-ingest` routes sources into and `kb-search`/`kb-lint` scope to. Read
`references/okf-spec.md` and `references/llm-wiki.md` (repo root) if you need the
underlying model.

## When to use this

Create a domain when knowledge needs a home that doesn't exist yet: a new product
area, project, subject, or topic. Do **not** create a domain for a source that
fits an existing one — check first with:

```bash
python3 .claude/skills/kb-ingest/scripts/detect_domain.py --list
```

If an existing domain's description covers the topic, ingest into it instead.
Prefer a few broad, well-scoped domains over many thin ones; overlapping domains
make routing ambiguous and fragment related knowledge.

## Inputs to settle first

- **Title** — human-readable name (e.g. "Billing & Invoicing").
- **Slug** — short, directory-safe id (e.g. `billing`). Derived from the title if
  not given.
- **Description** — ONE clear sentence describing the domain's scope. This is the
  single most important input: `kb-ingest` matches incoming sources against it to
  auto-route them, so make it specific and keyword-rich (name the systems,
  entities, and activities the domain covers), not vague.
- **Tags** — a few cross-cutting keywords (optional but improves routing).

If the description would be vague, ask the user what belongs in the domain and
what explicitly does not before scaffolding.

## Steps

1. **Check for overlap** with `detect_domain.py --list` (above). If a suitable
   domain exists, stop and ingest there instead.
2. **Scaffold and register** in one deterministic step:

   ```bash
   python3 .claude/skills/kb-init-domain/scripts/init_domain.py \
     --slug billing \
     --title "Billing & Invoicing" \
     --description "How invoices are generated, paid, and dunned across products." \
     --tags billing,payments,invoicing
   ```

   This creates `kb/billing/{domain.md, index.md, log.md, raw/index.md}`, adds the
   domain to `kb/index.md`, and logs it in `kb/log.md`. It refuses to clobber an
   existing directory unless you pass `--force`.
3. **Fill in `domain.md`** — the scaffold leaves placeholders under
   `# Scope`, `# Concept types`, and `# Entry points`. Replace them with real
   content: what is in scope, what is out of scope (and where that lives instead),
   and the kinds of concept pages you expect (Reference, Playbook, Entity, Metric,
   …). Good scope notes keep the domain coherent as it grows.
4. **Confirm** by showing the user the created tree and the registered catalog
   entry. If the domain was created to receive a specific source, hand off to
   `kb-ingest` next.

## Conventions

- The KB root is `kb/`. Every domain is a direct child directory.
- `domain.md` has `type: Domain` and carries the routing `description` — keep it
  current if the domain's scope shifts.
- Never put concept pages at the KB root; they belong inside a domain.
- After creating a domain, a `kb-lint` run should still pass (empty domains are
  valid). Populate it via `kb-ingest`.
