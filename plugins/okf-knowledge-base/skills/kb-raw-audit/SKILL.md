---
name: kb-raw-audit
description: >-
  Audit one explicitly named knowledge-base root for legacy Raw Source Archive
  material and, only after an explicit remediation scope, apply the user's
  named changes. This is a temporary, user-invoked workflow and is never an
  automatic cleanup path.
disable-model-invocation: true
---

# Audit a Legacy Raw Source Archive

This is a temporary migration aid for a knowledge base that inherited the old
raw-handling workflow. It is separate from normal initialization, ingest,
capture, search, lint, and consolidation. Read
`${CLAUDE_PLUGIN_ROOT}/references/knowledge-base.md` before acting if the
ownership boundary is not already clear.

The Raw Source Archive is user-owned. The audit reports evidence about existing
material; it does not decide ownership, create a replacement archive, or
perform broad cleanup.

## Invocation contract

The user must invoke this skill with **exactly one explicit KB root**. Treat
the root as the only scope:

```text
/kb-raw-audit <path-to-one-kb-root>
```

If the user does not provide the path to the kb, use the working directory's
`kb/` by default and confirm with the user that this is the path they want
audited.

The skill has two phases. Phase 1 is read-only and always ends with a report.
Do not begin Phase 2 in the same turn unless the user has already supplied a
specific remediation scope for the reported paths and actions.

## Phase 1: read-only evidence pass

1. Validate the named root without modifying it. Confirm that it is a
   knowledge-base root and resolve its canonical path.
2. Find every directory named `raw` at the root, beneath a top-level domain,
   and beneath nested domain directories. Record empty directories separately.
   Include every file type; the archive is not limited to Markdown.
3. For each artifact, collect only evidence that can be checked:

   - KB-relative and absolute path;
   - the raw directory's position in the domain tree;
   - content evidence such as a canonical URL, `resource` value, citation,
     generated-process marker, or explicit source/destination declaration;
   - relevant inbound references from non-raw Concept Pages, including the
     page path and matching link or citation;

   Do not read binary files as text. Record their existence, then mark 
   provenance as unknown unless a separate record establishes it.
4. Inspect non-raw Concept Pages for references to each artifact. Exclude raw
   content and reserved navigation or log files from the Concept Page
   reference list. A filename match alone is not an inbound reference; prefer
   an actual link, citation, or clearly identifying source declaration.
5. Classify each finding using evidence and confidence, not a filename-only
   guess. Use these categories where supported:

   - **Stable-URL copy candidate** - the artifact contains or is identified by a
     stable source URL, but do not call it an agent copy unless the evidence
     establishes that.
   - **Agent-produced or process residue** - content or a checked record shows
     that an agent, transcript, report, or workflow produced it.
   - **Clearly user-placed move candidate** - the user or an authoritative
     checked-in record explicitly identifies the retained source and its
     intended destination.
   - **Ambiguous provenance** - the available evidence cannot distinguish
     user-placed source material from generated or copied material.
   - **Legacy scaffolding** - evidence shows that the directory or file was
     emitted by the old scaffolding workflow.
   - **Raw index file** - an `index.md` file inside a raw directory. Report it
     separately from source artifacts.
   - **Empty legacy raw directory** - a raw directory with no entries. Report it
     separately from files.

   A finding may have more than one evidence note, but never promote an
   ambiguous item to a move or delete recommendation. A URL, timestamp, or
   filename can support a lead; it cannot establish ownership by itself.

6. Present a human-readable report and stop. Group results by the path to the 
   `raw/` directory each artifact is found within. Use one row per artifact and
   separate sections for raw index files and empty legacy raw directories. Sort
   rows by path, category, proposed action, and confidence. Each artifact row 
   must include:

   | Field | Required content |
   | --- | --- |
   | Path | The file name within the `raw/` location group |
   | Category | One or more categories above |
   | Confidence | High, medium, or low, with the reason |
   | Evidence | Observable content, metadata, source record, or user statement |
   | Concept Page references | Relevant page paths and links/citations, or `none found` |
   | Original Source Location | Exact path/URL, or `unknown` |
   | Proposed action | `none` until the user names an action |

   Do not write the report into the KB, update an index or log, create a
   manifest, or alter any raw bytes. Do not run a fix-enabled lint operation.
   Do not show the user more information than what is requested by the table above.
   The report is not permission to clean anything. End Phase 1 by waiting for
   the user's explicit remediation scope.

## Phase 2: apply only the named scope

Start Phase 2 only when the user identifies the exact artifact paths and
actions. A request such as "clean up the old raw files" is not a scope. Require
the user to name each path and, for a move, the exact destination. Do not
expand a directory-level instruction into every child unless the user named
that directory and explicitly authorized recursive handling. If there is any
ambiguity in the user's direction, ask them to clarify the ambiguity rather than
inferring what they meant.

Before changing anything:

1. Re-check that every requested source and destination is inside the named KB
   root or is an exact external destination the user explicitly authorized.
   Reject traversal, wildcard, or inferred destinations.
2. Re-read the report evidence and confirm that the requested action matches
   the user's instruction. Leave every unlisted artifact untouched.
3. If the action affects a Concept Page link or citation, update that page
   first using the normal editing workflow, in the OKF v0.2 form: provenance
   lives in `sources` entries attributed by `[^id]` footnotes. Preserve the
   citation when the user chose to retain the source (repoint its
   `sources[].resource` to the new location); replace it with the canonical
   origin, or remove it, only when the user's scope says to do so.
4. Run **kb_lint** against the named root and affected domains before
   destructive cleanup. Fix only issues caused by the approved documentation changes.
   Surface unrelated findings instead of silently repairing them.

For an approved move, preserve bytes exactly:

1. Do not overwrite an existing destination unless the user explicitly
   authorized replacement.
2. Copy the named artifact or directory to the exact destination.
3. Compare file counts, relative paths, byte lengths, and SHA-256 hashes for
   every file. A successful copy command is not verification.
4. Only after the comparison succeeds may the original be deleted. If any
   comparison fails, stop and leave the source in place.

For an approved deletion, delete only the named artifact after all required
Concept Page/citation changes and the pre-cleanup lint pass succeed. If a
destination was part of the user's instruction, verify it before deleting the
source. Run lint again after the deletion and repair any broken references
before reporting completion.

Empty legacy raw directories and raw index files are never removed automatically.
They may be changed only when the user names the exact path and the requested
action. Treat a user-approved removal of one of these as a
separate action, not as a consequence of deleting its contents.

## Guardrails

- When replacing a citation to a removed artifact, prefer its canonical
  origin (the URL or path it was taken from) as the `sources[].resource`. Use a
  `conversation on <date>` scope descriptor only when the knowledge genuinely
  originated in a conversation and no better origin exists.
- Removal of a `# Sources` section (or raw listing) from `domain.md` and
  `index.md` files in affected domains should be recommended when the
  remediation would delete every artifact it references.
- When cleaning up `domain.md` files while remediating artifacts, remove
  references to the `raw/` directory and raw sources. Do not replace them with
  explanatory notes such as "Raw source snapshots are not retained for this
  domain".
- This skill helps the user remediate agent-made source "snapshots". Unless
  the user says otherwise, assume a URL-sourced snapshot in a `raw/` directory
  is inappropriate when suggesting remediation.
- When recommending a course of action that would delete an artifact, include
  folding any concepts it holds into new or existing Concept Pages where
  applicable.
- This skill is stateless: do not persist an audit database, manifest, report,
  marker, or cleanup queue in the repository or KB.
- No other skill or automatic end-of-turn path invokes this audit.
- Normal ingest, capture, initialization, search, lint, and consolidation
  behavior remains unchanged by the audit's presence.
- Never write to a raw directory during Phase 1.
- Never move, delete, or rewrite an artifact merely because it is old,
  duplicated, URL-backed, named like generated output, or in an empty
  directory.
- If provenance, destination, or user intent remains unclear, report the gap
  and stop rather than inventing a conclusion.
