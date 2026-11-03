# Knowledge Base Doctrine

Within the plugin, this document is the sole normative doctrine for
knowledge-base behavior. The skills describe procedures, and the plugin's MCP
tools provide the deterministic operations. This doctrine remains subordinate
to system, developer, repository, and user instructions; it does not grant
authority to override them.

The Open Knowledge Format (OKF) v0.2 specification is the validation target
for this doctrine and the tools: changes to either are checked against it. The
specification is not shipped with the plugin. Everything an agent needs to
produce conformant pages is stated here, in this plugin's own terms.

## The three layers

### Raw Source Archive

Any `kb/**/raw` archive is a user-owned collection of source material. It may
contain Markdown, binary files, exports, transcripts, or other material the
user deliberately placed there. The archive is opaque: the plugin does not
assign meaning to its layout or rewrite its bytes.

Raw Artifacts are evidence that a user chose to retain. They are not Concept
Pages, are outside the Concept Page graph, and do not need frontmatter, a
manifest record, an index, or a plugin-defined eligibility decision. A file's
presence in the archive is sufficient.

### Concept Page Wiki

The wiki is the compiled layer. It contains one durable concept, entity,
playbook, reference, or metric per page, with indexes and append-only logs
providing navigation and history. Concept Pages are agent-produced knowledge:
they preserve a source's durable facts and explain what a source means rather
than reproducing the source.

### Schema layer

The schema layer is this doctrine, the procedural skills, and the MCP tool
contracts. It defines how sources are acquired, how domains route derived
knowledge, how pages link and cite, and how search, lint, and capture behave.

## Raw source ownership

The Raw Source Archive belongs to the user, not the agent.

- Normal ingest, capture, initialization, search, lint, and consolidation
  operations **MUST NOT** write to the archive.
- An agent **MAY** copy material there only after an express, direct user
  instruction authorizes that copy. The authorization applies to the named
  action; it is not standing permission for later workflows.
- Reading a local source for ingestion does not authorize or require a second
  copy. Placing a file in the archive does not trigger ingestion.
- The archive does not require a manifest, source hash, frontmatter, raw index,
  replacement registry, or freshness metadata.
- Raw Markdown may be retrieved only through an explicit opt-in
  (`include_raw`). Non-Markdown archive files are not searchable documents.

The agent's own analysis, summaries, and conversation findings belong in
Concept Pages. They must not be presented as original source material merely
because the agent could write them to a source directory.

## Domains

A domain is a directory under the KB root holding `domain.md`, `index.md`, and
`log.md`. Domains may nest as sub-domains (`billing/eu`); a sub-domain is
registered in its parent's `index.md`, not the root catalog.

- `domain.md` has `type: Domain` and a one-sentence, keyword-rich
  `description`. That description is the routing input: ingest and capture
  match knowledge against it, preferring the most specific matching domain.
- A domain with `status: deprecated` is listed but never routed to.
- A domain with no Concept Pages yet is valid.
- Concept Pages never sit at the KB root; they belong to a domain.

## The three operations

### Ingest

Ingest acquires source material, routes its subject to the best domain, and
compiles durable knowledge into Concept Pages.

1. Read a local file at its existing path, fetch a remote resource, or use the
   material supplied in the conversation.
2. Record the canonical origin as a `sources` entry (see
   [Citations and provenance](#citations-and-provenance)).
3. Route to a domain. When the best fit is low-confidence, consider whether a
   new domain would fit better, and ask the user before creating one.
4. Search the target domain before writing so existing pages are extended
   rather than duplicated. A search already run in the same turn that covers
   the concept answers this; do not repeat it.
5. Create or update Concept Pages, cross-links, the domain index, and the
   domain log.
6. Run scoped lint and surface failures.

Ingest never writes to the Raw Source Archive as a side effect. A
user-directed archive copy is a separate operation and is not a prerequisite
for compilation. Remote sources are represented by their canonical
references, not by an agent-owned mirror.

### Query

Query searches compiled Concept Pages first, follows indexes and cross-links,
and synthesizes an answer grounded in citations. Raw retrieval is excluded by
default.

Absence of evidence is not a negative answer. A legitimate "no" requires a
page that records the negative (something unsupported or decided against).
When the knowledge base does not answer, fall back to the codebase, external
sources, and reasoning, and say plainly when the answer is unknown.

If query work produces a genuinely new and durable conclusion, capture records
it as Concept Page content.

### Lint

Lint checks Concept Page conformance and wiki hygiene:

- **Errors (non-conformant):** a non-reserved `.md` file without parseable
  YAML frontmatter; frontmatter without a non-empty `type`; an `index.md` with
  frontmatter other than `okf_version` in the bundle-root `index.md`.
- **Warnings:** malformed provenance, trust, or lifecycle fields; datetimes
  without a UTC offset; footnotes with no matching source; broken links or
  source paths; body links into the Raw Source Archive; orphaned pages;
  duplicate titles or resources; index drift; non-ISO log headings.
- **Information:** missing recommended fields, stale pages, and legacy v0.1
  shapes awaiting migration.

Staleness comes from `stale_after` (a page is stale when now is on or after
that instant). An age threshold over `generated.at` may be requested as an
additional signal.

An orphan is resolved only by an inbound link (or a `sources` lineage edge)
from another Concept Page. Links from `domain.md`, `index.md`, `log.md`, or
the Raw Source Archive never resolve an orphan; if no related Concept Page
links in, the orphan finding is accurate and stays.

The Raw Source Archive is opaque to lint: raw files are never checked for
frontmatter, links, orphans, duplicates, or index drift. Broken links inside
append-only logs are historical records, not findings.

## Capture

The wiki compounds only when durable understanding is written down. The
`kb-capture` sweep scans the work just completed, keeps reusable facts and
decisions, routes them to the appropriate domain, and uses the ingest workflow
to create or update Concept Pages.

A repository chooses its capture mode when it is initialized with `kb-init`:

- **Automatic.** The `<knowledge-base>` directive in the repository's
  instructions file tells every agent to search the knowledge base first and
  to run `kb-capture` at the end of every turn in which new information
  entered its context.
- **Explicit (agent).** The directive only tells agents to search the
  knowledge base first. Capture happens when the user works through the
  `knowledge-curator` agent, which runs `kb-capture` at the end of its work.

Capture records agent-produced understanding in the wiki. It never places
summaries, excerpts, or other generated material in the Raw Source Archive.

## Good Concept Pages

A good Concept Page:

- covers one concept and has a stable, descriptive path;
- uses structured headings, lists, and tables where they improve retrieval;
- states durable meaning instead of copying a source;
- links to related Concept Pages in both directions when useful;
- records its provenance in `sources`, attributing specific claims with
  footnotes;
- records uncertainty instead of inventing unsupported detail; and
- is listed by its domain index.

## Page format (OKF v0.2)

A Concept Page is a UTF-8 Markdown file: a YAML frontmatter block delimited by
`---` lines, then a Markdown body. Frontmatter must be valid YAML; quote a
value that contains `: ` or ` #`.

```yaml
---
type: Reference                         # required, never empty
title: Retry policy                     # recommended
description: How webhook deliveries are retried.   # recommended, one sentence
resource: https://api.example.com/webhooks         # only for a concrete asset
tags: [billing, webhooks]
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-27T03:00:00Z }
verified: { by: human:alice, at: 2026-10-28T09:00:00Z }
status: stable                          # draft | stable | deprecated
stale_after: 2027-04-27T00:00:00Z
sources:
  - id: vendor-docs
    resource: https://docs.example.com/webhooks/retries
    title: Vendor webhook retry docs
---

Deliveries retry with exponential backoff for 24 hours.[^vendor-docs]

[^vendor-docs]: Vendor webhook retry docs
```

- **`type`** is the only required key. Values are free text (`Reference`,
  `Playbook`, `Entity`, `Metric`, `Domain`, …); consumers tolerate unknown types.
- **`resource`** identifies the underlying asset the page describes (a table,
  an endpoint, a repository). Omit it for abstract concepts. It is never a
  provenance field.
- **`generated`** records the last meaningful content change: `by` (an actor,
  required) and `at`. Update it whenever you change a page's substance.
- **`verified`** records confirmation events, each `{ by, at }`; a single event
  may be a bare mapping. Trust is derived: no `verified` is unverified, only
  non-human actors is machine-confirmed, any `human:` actor is human-reviewed.
  Never add `verified` on someone else's behalf.
- **`status`** defaults to `stable` when absent. Use `draft` for incomplete
  pages and `deprecated` for pages kept only for links and history.
- **`stale_after`** is an absolute instant at which the page needs review.
- **`sources`** lists what the page derives from. Each entry requires
  `resource` and may carry `id`, `title`, `author`, `usage_count`, and
  `last_modified`; a sibling `usage_window: { from, to }` frames usage counts.
  Attribute a claim with a footnote whose label is a source `id` (`[^id]`).
  Labels are keyed, never positional, so they survive reordering.
- **Actors** are `<producer>/<version>` for agents and tools (for example
  `claude-code/claude-opus-5-5`), `human:<id>` for people, and
  `process:<id>` for automated processes. Hand-authored or human-confirmed
  content must use `human:`.
- **Datetimes** are ISO 8601 with an explicit UTC offset
  (`2026-10-27T03:00:00Z`).
- **Path-valued fields** (`resource`, `sources[].resource`) accept an absolute
  URL, a bundle-relative path beginning with `/`, or a relative path. A
  `sources[].resource` may instead be a scope descriptor that is not a path.
- **Unknown keys** are allowed and preserved, but never reuse a key OKF defines
  with a different meaning or value set.
- **Attested Computation** concepts (`type: Attested Computation`, the
  `# Computation` heading, executor and attester fields) are tolerated but out
  of scope: the plugin neither produces nor validates them.

### Links, indexes, and logs

- Link Concept Pages with Markdown links, preferably bundle-relative
  (`[retry policy](/billing/retry-policy.md)`). A link asserts a relationship;
  the prose says what kind. Broken links are tolerated but are hygiene
  findings.
- `index.md` and `log.md` are reserved. An `index.md` carries no frontmatter,
  except that the bundle-root `index.md` may hold exactly
  `okf_version: "0.2"`. A domain `index.md` lists its Concept Pages under
  `# Concepts` and sub-domains under `# Sub-domains`.
- A `log.md` is append-only history with `## YYYY-MM-DD` headings, newest
  first.

### Legacy v0.1 pages

Pages written before v0.2 may carry `timestamp` instead of `generated.at`, and
a body `# Citations` list instead of `sources`. Tools read both as fallbacks
and lint reports them as information. When you substantively edit such a page,
migrate it: move `timestamp` to `generated.at` (with an actor), and move each
citation to a `sources` entry attributed by footnote.

## Citations and provenance

Every source-backed claim identifies its canonical origin through a `sources`
entry.

- A URL or local file path is the `resource` of a sources entry.
- A conversation is a scope descriptor, for example
  `resource: conversation on 2026-10-27`. It is valid provenance in `sources`,
  never a page's top-level `resource`.
- A user-placed Raw Artifact is cited by pointing a sources entry at it
  (`resource: /billing/raw/vendor-export.csv`). Never link into the Raw
  Source Archive from a page body, and never create an archive copy merely to
  make a citation possible.
- A provenance URL found in a page's top-level `resource` moves to a
  `sources` entry; it is never deleted. `resource` stays only if the page
  really describes that asset.

Provenance describes where knowledge came from. It does not imply that an
agent-created copy is an independent source record. A failed read, unavailable
origin, or unverifiable directed copy must be reported explicitly rather than
replaced with a success-shaped fallback.

The Raw Source Archive is a plugin-local opaque boundary outside the Concept
Page graph. OKF v0.2 defines no subtree exclusion, so a strict OKF consumer
may still expect frontmatter on raw Markdown; this boundary is not a portable
conformance claim.
