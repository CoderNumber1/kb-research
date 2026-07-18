---
name: kb-init-domain
description: >-
  Initialize a new domain (a self-contained subject area) inside the Open
  Knowledge Format knowledge base under kb/, by creating the files directly with
  your file tools — no scripts. Use whenever the user wants to start tracking a
  NEW topic, subject, product area, or project that has no home in the KB yet —
  e.g. "set up a domain for our billing system", "create a knowledge area for the
  payments API", "start a wiki section on onboarding" — or when kb-ingest finds a
  source belongs to a subject the KB doesn't cover. Scaffolds domain.md (scope +
  description used for auto-routing), index.md, log.md, and raw/, and registers
  the domain in the root catalog (or a parent, for nested sub-domains).
---

# Initialize a Knowledge Base Domain (scriptless)

A **domain** is one OKF bundle subtree under `kb/<slug>/` with its own sources,
concept pages, index, and log. You create it by **writing the files yourself**
with Write/Edit — there are no helper scripts. Read
`${CLAUDE_PLUGIN_ROOT}/references/okf-spec.md` and
`${CLAUDE_PLUGIN_ROOT}/references/llm-wiki.md` if the model isn't clear to you.

## Before creating

- **Find the KB root.** It's the `kb/` bundle in the working directory (a
  directory with an `index.md` whose frontmatter has `okf_version`, or that
  contains domain subdirectories). If there is no `kb/` yet, you'll create it.
- **Check for overlap.** List existing domains by reading `kb/index.md` and each
  `kb/*/domain.md` description (Glob `kb/**/domain.md`). If one already covers the
  topic, stop and ingest into it instead — don't fragment related knowledge.
- **Settle the inputs:** a **title**, a directory-safe **slug** (lowercase,
  hyphens; a path like `billing/eu` makes a nested sub-domain), a one-sentence
  **description** (this is what `kb-ingest` matches sources against — make it
  specific and keyword-rich), and a few **tags**.

## Create the files

Ensure `kb/index.md` and `kb/log.md` exist (create the root if this is the first
domain — root `index.md` carries only `okf_version: "0.1"`). Then write these
four files under `kb/<slug>/`:

**`domain.md`** (a first-class OKF concept — the routing anchor):

```markdown
---
type: Domain
title: <Title>
description: <One sentence describing the scope — used for auto-routing.>
slug: <slug>            # full bundle-relative path, e.g. billing/eu
tags: [<tag>, <tag>]
status: active
timestamp: <ISO 8601 now>
---

# Scope

<description>

**In scope:** _what belongs here._

**Out of scope:** _what does not, and where it lives instead._

# Concept types

_The kinds of pages this domain will hold (Reference, Playbook, Entity, Metric)._

# Entry points

_Link the most important pages here once they exist._

# Sources

Raw source material is snapshotted under [`raw/`](raw/index.md).
```

**`index.md`** (progressive disclosure — no frontmatter):

```markdown
# <Title>

<description>

See [domain.md](domain.md) for scope and conventions.

# Concepts

<!-- Concept pages are listed here as they are ingested. None yet. -->

# Sources

* [Raw sources](raw/) - immutable snapshots of ingested material.
```

**`log.md`** (newest first, ISO dates):

```markdown
# <Title> — Update Log

## <YYYY-MM-DD>
* **Initialization**: Created the <Title> domain.
```

**`raw/index.md`**:

```markdown
# Raw Sources

Immutable snapshots of material ingested here. Concept pages cite back to these.
Do not edit source snapshots after they are written.
```

## Register the domain

- **Top-level domain** → add a bullet under `# Domains` in `kb/index.md`:
  `* [<Title>](<slug>/index.md) - <description>`, and prepend a dated
  `* **Creation**: …` entry to `kb/log.md` (newest first).
- **Nested sub-domain** (slug has a parent, e.g. `billing/eu`) → the parent must
  already exist. Register under the **parent's** `index.md` in a `# Sub-domains`
  section (`* [<Title>](eu/index.md) - <description>`) and add a `* **Creation**`
  line to the parent's `log.md` — not the root catalog.

## Finish

Show the created tree and the catalog entry. Fill in the `domain.md` scope
placeholders with real in/out-of-scope notes. If the domain was created for a
specific source, hand off to `kb-ingest`. Don't over-nest — add a sub-domain only
when its scope is genuinely distinct.
