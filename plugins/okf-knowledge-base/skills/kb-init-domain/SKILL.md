---
name: kb-init-domain
description: >-
  Initialize a new domain (a self-contained subject area) or nested sub-domain
  inside the Open Knowledge Format knowledge base under kb/. Use whenever the
  user wants to start tracking a NEW topic, subject, product area, project, or
  body of knowledge that has no home in the KB yet — e.g. "set up a domain for
  our billing system", "create a knowledge area for the payments API" — or when
  kb-ingest determines incoming knowledge belongs to a subject the KB does not
  cover. Scaffolds domain.md (scope + routing description), index.md, and
  log.md, and registers the domain in its parent catalog.
---

# Initialize a Knowledge Base Domain

A **domain** is one subtree under `kb/<slug>/` with `domain.md`, `index.md`,
and `log.md`: a self-contained area for compiled knowledge. Domains are the
unit `kb-ingest` routes knowledge into and `kb-search`/`kb-lint` scope to.
Read `${CLAUDE_PLUGIN_ROOT}/references/knowledge-base.md` if the operating
model is not already clear.

The knowledge base must already exist. If there is no `kb/index.md`, run
**kb-init** first.

## When to use this

Create a domain when knowledge needs a home that does not exist. Do not create
one for a topic an existing domain covers: check first by calling
**kb_detect_domain** with `kb_root` and `list: true`. Prefer a few broad,
well-scoped domains over many thin ones; overlapping domains make routing
ambiguous and fragment related knowledge.

## Inputs to settle first

- **Title** — human-readable name (e.g. "Billing & Invoicing").
- **Slug** — short, directory-safe id (e.g. `billing`).
- **Description** — one clear sentence describing the domain's scope. This is
  the routing input, so make it specific and keyword-rich: name the systems,
  entities, and activities it covers.
- **Tags** — a few cross-cutting keywords (optional, improves routing).

If the description would be vague, ask the user what belongs in the domain and
what explicitly does not before scaffolding.

## Steps

1. **Check for overlap** with **kb_detect_domain** (`list: true`). If a
   suitable domain exists, stop and ingest there instead.
2. **Scaffold and register** in one deterministic step: call
   **kb_init_domain** with `kb_root` (absolute path of the workspace `kb/`)
   and:
   - `slug: "billing"`
   - `title: "Billing & Invoicing"`
   - `description: "How invoices are generated, paid, and dunned across products."`
   - `tags: "billing,payments,invoicing"`

   This creates `kb/billing/{domain.md, index.md, log.md}` (with `generated`
   frontmatter), adds the domain to `kb/index.md`, and logs it in
   `kb/log.md`. It refuses to clobber an existing directory unless
   `force: true` is supplied.
3. **Fill in `domain.md`** — replace the placeholders under `# Scope`,
   `# Concept types`, and `# Entry points` with real content: what is in
   scope, what is not and where it lives instead, and the kinds of Concept
   Pages expected. Update `generated` to your actor and the current time.
4. **Confirm** the created tree and catalog entry. If the domain was created
   to receive knowledge, hand off to **kb-ingest**.

## Nested sub-domains

A domain can hold sub-domains when a slice has a genuinely distinct scope;
`kb-ingest` routes to the most specific match. Give `slug` a path
(`billing/eu`) or set `parent: "billing"` with `slug: "eu"`. This creates
`kb/billing/eu/{domain.md, index.md, log.md}` and registers it under the
parent's `index.md` (`# Sub-domains`) and `log.md`, not the root catalog. The
parent must exist; create top-down. Don't over-nest when an ordinary Concept
Page is enough.

## Conventions

- `domain.md` has `type: Domain`; its `slug` is the full path (`billing/eu`).
  Keep the description current if the scope shifts.
- To retire a domain without breaking links, set `status: deprecated` in its
  `domain.md`; it stays listed but is never routed to.
- An empty domain is valid; populate it through `kb-ingest`.
