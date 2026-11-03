---
name: kb-init
description: >-
  Bootstrap a brand-new Open Knowledge Format knowledge base in the current
  repository: choose how knowledge capture works (automatic every turn, or
  explicit through the knowledge-curator agent), create the kb/ root, write the
  knowledge-base directive into the repository's instructions file, and hand
  off to kb-init-domain for the first domain. Use when the user wants to set
  up, start, or add a knowledge base or wiki to a repository that has no kb/
  root yet — or to switch an existing knowledge base's capture mode.
---

# Bootstrap a Knowledge Base in this Repository

This is the repository-level setup that turns a plain repository into a host
for a knowledge base. It is distinct from `kb-init-domain`, which opens a new
subject area inside an existing knowledge base. Read
`${CLAUDE_PLUGIN_ROOT}/references/knowledge-base.md` if the operating model is
not already clear.

## What bootstrapping establishes

1. **The KB root** — `kb/index.md` (declaring `okf_version: "0.2"`) and
   `kb/log.md`, the catalog every domain registers into.
2. **The `<knowledge-base>` directive** — a block in the repository's
   instructions file (default `CLAUDE.md` beside `kb/`). Instruction files are
   loaded into every session, so the directive is how future agents learn the
   knowledge base exists and must be searched first.
3. **The capture mode**, which decides what the directive says about capture.

The **kb_init** tool does all three deterministically. Do not hand-write the
directive or the root files.

## Steps

1. **Check the state.** If `kb/index.md` already exists, this is a mode switch
   or a directive refresh, not a new knowledge base — say so, and skip step 5.
2. **Ask the user which capture mode to use.** Present both and wait for an
   answer; do not pick for them.
   - **Automatic** — the directive tells every agent to search the knowledge
     base first *and* to run the `kb-capture` sweep at the end of every turn
     in which new information entered its context. Knowledge compounds with no
     extra effort; every turn pays a small capture cost.
   - **Explicit (agent)** — the directive only tells agents to search the
     knowledge base first. Capture happens only when the user works through
     the `knowledge-curator` agent, which runs `kb-capture` when it finishes.
     Nothing is written to the wiki unless the user opts in.
3. **Confirm the instructions file.** Default is `CLAUDE.md` in the
   repository root. If the repository keeps agent instructions elsewhere,
   confirm the path with the user.
4. **Call kb_init** with `kb_root` (absolute path of `<repo>/kb`),
   `capture_mode` (`automatic` or `agent`), and `instructions_file` only if it
   is not the default. The call is idempotent: it creates missing root files,
   leaves existing ones untouched, and inserts or replaces the single
   `<knowledge-base>` block. Report its output.
5. **Create the first domain.** A new knowledge base needs a home for its
   first knowledge: hand off to **kb-init-domain**.
6. **Confirm** the root, the instructions file, the capture mode, and how to
   switch it later (run kb-init again).

## Notes

- Only repositories where a knowledge base was created carry the directive,
  so the knowledge base stays out of the way everywhere else.
- Creating a knowledge base does not grant permission to write to the
  user-owned Raw Source Archive.
