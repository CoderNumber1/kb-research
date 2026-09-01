# Second Brain + Delegation System — Plan of Attack

*A three-phase build plan for turning a git-backed markdown knowledge base (okf/karpathy-style) into a working "second brain" that keeps your days organized, tracks your task load, and lets you delegate to both humans and AI without the context-switching becoming overwhelming.*

**Your context this is tuned to:** team lead over three developers, sole final code-review approver, knowledge base is a git repo of markdown files.

**The one rule that governs the whole plan:** don't install everything at once. Get the compounding foundation working first, live on it, then let the next most painful gap tell you what to add. The knowledge base is the memory everything else reads from — it comes first.

---

## Phase 1 — Leverage out of the box (this week)

Goal: get value from tools that need no custom work, and stand up the memory spine over the repo you already have.

### 1a. Point retrieval at your knowledge base
- **librarian** becomes your primary memory/retrieval layer. It walks a knowledge graph or codebase and returns the relevant pieces and how they connect — exactly what you want over an okf base. Because your base is a git repo of markdown, this is *more* native to Claude Code than any vault integration would be; no adapter needed on day one.
- Action: point Claude Code at the knowledge-base repo, confirm librarian-style retrieval returns useful, connected results. If retrieval is weak, that's a signal your file/folder conventions need tightening (see Phase 2), not that the approach is wrong.

### 1b. Kill the context-switch tax
- **pickup** — session resume. As the sole review approver you switch between three developers' branches constantly; pickup reconstructs "where you were, what's in flight, what's blocked" from the repo and git history, turning each switch into a warm start instead of a ~20-minute rebuild. This is your single highest-leverage skill — prioritize it.

### 1c. Turn on the store-agnostic layer (all no-setup)
- **adhd-task-triage** — you give it your current energy state; it hands back the one task you can actually start, instead of an intimidating priority-sorted list. Directly addresses the "mountain of tasks."
- **schedule** — time-blindness guardrail. Recurring checkpoints so you don't lose three hours inside one PR.
- **mirror** — reads commits and closed tasks and reports what you actually shipped. **Higher value in a lead role than an IC one:** on days you unblock three people and approve reviews, you produce little under your own name and your brain reads that as "did nothing." mirror counters that with receipts.
- **ravila4 nudge + time hooks** — shell/Python hooks on prompt submission so "wrap up in 30 minutes" actually fires. No vault dependency.
- **i-have-adhd** (optional, easy to toggle) — action-first, numbered, low-preamble replies when you're moving fast.

### Phase 1 priority order
1. librarian pointed at the repo (the foundation everything reads from)
2. pickup (your most expensive recurring tax)
3. Live on those two for about a week before adding more.
4. Then layer in triage → schedule → mirror → hooks as each gap makes itself felt.

### What you are NOT doing in Phase 1
- No Obsidian (not an option, and not needed — git is your cross-session persistence).
- No custom skills yet.
- No delegation protocol yet — you need the memory spine working first.

---

## Phase 2 — Design and build for your environment

Goal: replace the two Obsidian-specific pieces you're skipping with git-native equivalents that live *inside* your knowledge base, and build the delegation layer that no off-the-shelf ADHD skill actually solves.

### 2a. Custom daily-capture skill (replaces packaged daily-journal)
- A `SKILL.md` in `.claude/skills/<name>/` that appends a dated entry to a file in your knowledge-base repo (e.g. `daily-log/YYYY-MM-DD.md`). Conversational capture at end of day, committed to git. Trivial to build because your store is already plain markdown.
- Payoff: the record builds itself instead of depending on you remembering to log, and it lives in the same repo everything else reads.

### 2b. Tighten knowledge-base structure so retrieval carries
- Without a vault's linking/semantic-search affordances, retrieval quality depends on how the okf base is organized. Establish and enforce: clear file/folder conventions, consistent naming, and lightweight frontmatter. If the base is well-organized, librarian carries it fine; if it sprawls, retrieval degrades.
- Later optimization (only if the base gets large and sprawling): add a semantic-search layer over the repo. Not a day-one need, and not Obsidian-dependent.

### 2c. The delegation protocol — the part that's actually yours to design
This is the weak point in *any* ADHD-skill stack and the piece most tied to your specific job. No skill solves it; you design it. The two directions need different handling:

- **Delegating to AI:** before you hand a task to an agent, the context it needs already lives in the repo as a node — not in your head or a chat scrollback. This is the real payoff of building the second brain first. Delegating becomes "point the agent at a path."
- **Delegating to humans:** your three developers need briefs they can act on. That's a writing/structuring task, not an executive-function patch. The stack gives you the raw material (librarian pulls context, pickup gives current thread state); turning it into a clear brief is its own step.

**Design artifacts to build in this phase:**
- A **CLAUDE.md section** encoding the protocol, e.g.: *AI tasks get a vault/repo node; human tasks get a written brief; batch each type rather than interleaving them.*
- A **vault-node template** tuned to your okf structure (for AI-delegable tasks): what the task is, where the relevant context lives (paths), acceptance criteria, current state.
- A **human-brief template** (for developer delegation): goal, context/links into the repo, scope boundaries, what "done" looks like, review expectations.

Because both AI nodes and human briefs are just files in the one repo your developers already have access to, there's no second system to sync — a real advantage of the git-backed approach over a vault.

### Guard against the seductive failure mode
Don't spend all your executive-function budget perfecting the AI-delegation pipeline while your human developers wait on ambiguous instructions. The human-brief path is lower-tech and higher-impact on your actual team throughput. Build both templates; resist over-engineering the AI side.

---

## Phase 3 — Integrate the two surfaces over time

Goal: make the memory spine (knowledge base + retrieval) and the executive-function layer (triage/resume/schedule/mirror) reinforce each other, so each session makes the next one smarter and delegation load keeps dropping.

### 3a. Close the write-back loop
- The engineering skills are meant to chain around a shared, growing knowledge store — not run as isolated tools. Wire it so:
  - **pickup** reads recent nodes/commits to reconstruct context.
  - **adhd-task-triage** and **mirror** write back what was decided and done.
  - **daily-capture** commits the day's record.
  - **librarian** walks the accumulated graph so nothing starts from scratch.
- The compounding effect: the base accumulates your decisions instead of forgetting them at session end. That's the whole point of a second brain versus a pile of notes.

### 3b. Batch by delegation type, not by project
- Use the CLAUDE.md protocol to structure your day around *type of switch* rather than firefighting: a block for AI-delegable node-writing, a block for human briefs, a block for your own review approvals. Reducing the *kinds* of context switches is what actually lowers the overwhelm — more than any single skill does.
- **schedule** enforces the block boundaries; **nudge/time hooks** keep them honest.

### 3c. Let the base become the single source of truth for delegation
- Over time, the target state: any task you're tracking, delegating to AI, or handing to a developer resolves to a file in the repo. Your developers read the same context an agent would. "What's the state of X?" is answered by the base, not by reconstructing it in your head.
- **mirror** against this base gives you an honest weekly picture of lead-role output (unblocked, approved, migrated) that a commit count alone would hide.

### 3d. Review and prune quarterly
- A knowledge base grows traps: stale nodes, dead links, conventions that drifted. Schedule a recurring prune (this is itself a good AI-delegable task). Retrieval quality is a maintained property, not a one-time setup.

---

## Summary — the shape of the whole thing

| Layer | Phase 1 (out of the box) | Phase 2 (build for you) | Phase 3 (integrate) |
|---|---|---|---|
| **Memory / knowledge base** | librarian over the git repo | custom daily-capture skill; tighten structure | write-back loop; base = single source of truth |
| **Executive function** | pickup, adhd-task-triage, schedule, mirror, nudge/time hooks | — | chain the skills; mirror for lead-role visibility |
| **Delegation** | — | CLAUDE.md protocol; AI-node + human-brief templates | batch by delegation type; developers read the same base |
| **Output style** | i-have-adhd (optional) | — | — |

**Start here:** librarian + pickup, this week, on the repo you already have. Everything else waits until those two are load-bearing.

**The honest caveat:** the delegation-to-humans piece is the weakest point in any ADHD-skill stack and the one most tied to your job. Its fix is as much a personal protocol as an installable skill. Build the two templates in Phase 2 and treat them as first-class, not an afterthought to the AI pipeline.

---

## Final handoff notes — direction and implementation detail

*Written as a last pass of input before this plan may be handed to a model or another person to execute. Read this before starting Phase 2. It captures the judgment behind the plan, not just the steps.*

### On the three deliverables (confirming they're in scope)
Phase 2, section 2c already names three artifacts as required: (1) a **CLAUDE.md section** encoding the delegation protocol, (2) a **repo-node template** for AI-delegable tasks, and (3) a **human-brief template** for developer delegation. They are deliverables, not suggestions. Whoever executes this should produce all three as actual files. The notes below are the implementation detail that section deliberately left open.

### Direction — what matters most, in priority order
1. **The knowledge base is load-bearing infrastructure, not a side project.** Every other layer reads from it. If forced to choose where to spend limited effort, spend it on retrieval quality and structure conventions (2b) before anything downstream. A messy base makes every skill above it worse.
2. **Reducing the *kinds* of context switches beats optimizing any single switch.** The overwhelm comes from interleaving three modes — your own review work, AI delegation, human delegation. The batching discipline (3b) is the highest-impact behavioral change in this whole plan. No skill substitutes for it.
3. **The human-brief path is higher-impact on team throughput than the AI-delegation path**, and it's the one most likely to be neglected because the AI side is more fun to build. Weight effort accordingly. If a week goes by where the AI pipeline got polished and no developer brief improved, that's a red flag.
4. **Don't let the tooling become the work.** The failure mode for this kind of system, especially with ADHD, is that building the second brain *becomes* the productive-feeling task that displaces the actual work. Ship briefs and approvals; the system exists to serve throughput, not the reverse.

### Implementation detail — CLAUDE.md section
- Keep it short and imperative. It's read by an agent every session; verbosity dilutes it.
- Encode the core protocol as explicit rules, e.g.: *AI-delegable tasks get a repo node using the node template. Human-delegable tasks get a brief using the brief template. Batch each type into its own block; do not interleave. Context lives in the repo, never only in chat.*
- Include a "where things live" map: the paths for daily logs, task nodes, and briefs, so any agent resolves references without asking.
- State the retrieval convention so the agent knows how the base is organized (folder meanings, naming, frontmatter fields).
- Add a pointer for the model's own behavior: prefer asking over assuming when a task's context isn't in the repo yet — that gap is the signal to write the node first.

### Implementation detail — AI-delegable repo-node template
Fields to include at minimum:
- **Task** — one-line statement of what's being delegated.
- **Context paths** — explicit repo paths where the relevant code/knowledge lives (this is the field that makes delegation "point the agent at a path").
- **Acceptance criteria** — what "done" looks like, concretely.
- **Current state** — what's already been tried/decided, so the agent doesn't redo it.
- **Constraints** — what not to touch, scope boundaries.
- Keep it plain markdown with frontmatter, committed to git, so it's diffable and both agents and humans can read it.

### Implementation detail — human-brief template
Fields to include at minimum:
- **Goal** — what outcome you need and why (the "why" is what lets a developer make good local decisions).
- **Context / links** — pointers into the repo, not re-explained prose.
- **Scope boundaries** — explicitly what's in and out, since ambiguity here is what generates the interruptions you're trying to reduce.
- **Definition of done** — acceptance criteria a developer can self-check against before it reaches your review queue.
- **Review expectations** — what you'll be checking for as the sole approver, so they can pre-empt it. This directly shrinks your review load.
- Consider a lightweight version for small asks so the template doesn't become friction that pushes you back to verbal delegation.

### Implementation detail — sequencing and validation
- Build the node template first (it's simpler and unblocks AI delegation), then the human brief, then the CLAUDE.md that references both. The CLAUDE.md is the keystone — write it last so it points at real files.
- Validate each template by running one real task through it end to end before standardizing. A template that survives one real delegation is worth ten designed in the abstract.
- Treat the templates as living: after two weeks of use, prune fields nobody fills and add fields you keep improvising. Convention drift is normal; unmaintained drift is the failure.

### The things most likely to get missed
- **Write-back is easy to skip and quietly fatal.** If triage/mirror/daily-capture read from the base but nothing writes decisions back (3a), the base stops compounding and degrades into a stale snapshot. Verify the loop actually closes.
- **Retrieval quality is a maintained property.** Schedule the quarterly prune (3d) as a real recurring task, ideally AI-delegated, or the base rots.
- **The delegation protocol is yours, not the stack's.** No installed skill will produce it. If Phase 2's 2c gets deprioritized because it's the only part without a ready-made tool, the whole delegation goal fails — that section is the point of the plan, not an add-on.

---

*All skills referenced are community-built; none are official Anthropic products, and effectiveness claims are largely self-reported. Validate each against your own workflow before making it load-bearing.*
