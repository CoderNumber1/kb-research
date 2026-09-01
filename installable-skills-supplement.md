# Supplemental Report — What's Actually Installable, and Where From

*A correction and sourcing addendum to the ADHD AI skills report and the second-brain plan of attack.*

## The correction you're owed

You were right, and I need to state this plainly rather than bury it. **The five engineering skills from chudi.dev (adhd-task-triage, pickup, mirror, schedule, librarian) are not published as installable artifacts.** They live only as prose descriptions in blog posts. The author confirms this himself: several of them are custom skills he built for his own setup and did not release, and he frames the transferable thing as *the pattern*, not a downloadable package. His own companion piece is even titled to the effect of "there's no plugin — here's my workflow."

That means my earlier reports overstated their availability. The chudi.dev links are legitimate as **design references** — they tell you what each skill should do and how to build it — but they are **not install sources**, and presenting them alongside real install commands blurred that line. This report fixes it by separating the two cleanly: what you can install today, and what you'd have to build (or substitute) from a described pattern.

**Scope note — Obsidian excluded.** Per your constraint, this report excludes any tool that requires Obsidian to function. That exclusion removes the `llm-wiki` plugin I previously led with (its second-brain pattern is built around an Obsidian vault) and ravila4's journaling/vault skills. Where a repo is only *partly* Obsidian-dependent, I keep the Obsidian-free components and say so explicitly. The practical cost of this exclusion: the strongest off-the-shelf substitute for `librarian` was llm-wiki's `wiki-librarian`, so removing it leaves `librarian` as a build-your-own — noted in Category B.

---

## Category A — Actually installable today (verified)

### ravila4/claude-adhd-skills — pacing hooks + CLAUDE.md starter (Obsidian-free parts only)
This repo is real and installable. **Its journaling and vault skills require Obsidian and are excluded here.** What remains — and what I'm recommending — are the **time hooks, the nudge system, and the starter CLAUDE.md**, all of which are Obsidian-independent and work against a plain git setup.
- **Install (hooks only, skipping the Obsidian skills):**
  ```bash
  git clone https://github.com/ravila4/claude-adhd-skills.git
  cd claude-adhd-skills
  cp hooks/* ~/.claude/hooks/
  # copy only the non-Obsidian skills you want from skills/ — skip daily-journal / obsidian-vault
  ```
  Then copy the hook configuration into your Claude Code settings.
- **Source:** https://github.com/ravila4/claude-adhd-skills
- **What you get:** current-date/time injection into every prompt, due-nudge checks on prompt submission (`+30m`, `23:00`, etc.), and a CLAUDE.md starting point. The `test-driven-development` skill is also Obsidian-free. **Do not** copy `daily-journal` or `obsidian-vault`.

### RobotDisco/adhd-skills — GTD + knowledge-review ritual (proper marketplace)
A newly relevant find, and arguably a better fit for you than the chudi.dev patterns because it's actually installable as a marketplace plugin and is built around GTD task-management and knowledge review — close to what you're assembling.
- **Install:** register the repo as a Claude Code marketplace once per machine, then install the domain plugins you want (gtd/ for task management, brain/ for knowledge management). Skills activate immediately, no restart.
- **Source:** https://github.com/RobotDisco/adhd-skills
- **Why it matters for you:** it's organized as installable per-domain plugins (task triage, weekly review, focus check-ins) and cites its executive-function design sources — the closest real, installable analog to the chudi.dev "five" you were originally pointed at.

### alirezarezvani/claude-skills — large collection; **tc-tracker (handoff/resume) recommended, llm-wiki excluded**
This 380-skill collection is installable and cross-tool compatible. One caveat drives how it appears here: its headline second-brain plugin, **`llm-wiki` (Karpathy's LLM Wiki pattern), is built around an Obsidian vault, so it is excluded from this report** despite being the closest off-the-shelf match to your okf/Karpathy base. If you ever reconsider Obsidian, revisit it — but under your current constraint it's out, and with it goes the `wiki-librarian` sub-agent I'd previously offered as the `librarian` substitute.
- **What remains useful and Obsidian-free:** **`tc-tracker`** — a task context tracker with a defined lifecycle and handoff format, shipping five Python tools (tc_init, tc_create, tc_update, tc_status, tc_validator) and a `/tc` slash command. This maps directly onto the **pickup / session-resume / delegation-handoff** need in your plan, and it operates on its own task files rather than an Obsidian vault.
- **Install:** `npx skills add alirezarezvani/claude-skills` (or clone and copy per the repo's INSTALLATION.md; Windows users see the symlink note). Install/enable **tc-tracker** specifically; do not enable the llm-wiki plugin.
- **Source:** https://github.com/alirezarezvani/claude-skills — plugin detail in its CLAUDE.md: https://github.com/alirezarezvani/claude-skills/blob/main/CLAUDE.md
- **Verify before relying on it:** confirm tc-tracker has no transitive Obsidian dependency in its own SKILL.md before making it load-bearing — the repo as a whole mentions Obsidian for other plugins, so check this one in isolation.

### i-have-adhd (output formatting) — installable via marketplace
The ADHD-friendly output-formatting skill is a real Claude Code plugin.
- **Install:** `claude plugin marketplace add ayghri/i-have-adhd` then `claude plugin install i-have-adhd@i-have-adhd` (verify the exact owner/name against the repo, since several similarly named formatting plugins now exist).
- Also findable via the GitHub `adhd` topic (see Category C).

---

## Category B — Described patterns you must build or substitute

These are the chudi.dev "five." Treat each as a spec, and either build a SKILL.md yourself or use the installable substitute I've matched to it.

| Skill (as described) | Real install source? | What to do |
|---|---|---|
| **librarian** (codebase/graph retrieval) | Not published by author | **Build your own.** The best off-the-shelf substitute (wiki-librarian) is Obsidian-dependent and excluded. Write a SKILL.md that greps/indexes your git repo and returns relevant files + what touches them. |
| **pickup** (session resume / handoff) | Not published by author | **Substitute:** `tc-tracker` (task context tracker w/ handoff) in alirezarezvani/claude-skills — Obsidian-free; verify per note above. Or RobotDisco startup ritual. |
| **adhd-task-triage** (energy-based init) | Not published by author | **Substitute:** gtd-triage in RobotDisco/adhd-skills (installable). Otherwise build from the blog spec. |
| **schedule** (time-blindness checkpoints) | Not published by author | **Substitute:** ravila4 time hooks + nudges (installable, Obsidian-free). |
| **mirror** (progress receipts) | Not published by author | **Build:** small SKILL.md reading git log + closed tasks. No clean installable equivalent found. |

Reference specs (design only, **not install sources**):
- The five skills described: https://chudi.dev/blog/claude-code-skills-adhd-developers
- Same, on DEV with the worked daily flow: https://dev.to/chudi_nnorukam/5-claude-code-skills-every-adhd-developer-needs-5e74
- "No plugin, here's my workflow" (the author's own admission they're not packaged): https://chudi.dev/blog/claude-code-adhd-workflows
- CLAUDE.md-as-working-memory config: https://chudi.dev/blog/adhd-developers-guide-claude-md

---

## Category C — Where to browse for more installable options

Because the space moves fast and new installable skills appear weekly, these are the live directories worth searching before you hand-build anything:

- **GitHub `adhd` topic** — actively maintained cluster of ADHD Claude Code plugins/skills, several installable as marketplaces: https://github.com/topics/adhd
- **github/awesome-copilot** — if you go the Copilot CLI route, its marketplace is pre-registered: `copilot plugin install <name>@awesome-copilot` — https://github.com/github/awesome-copilot
- **Skills CLI (vercel-labs/skills)** — the cross-agent installer (`npx skills add owner/repo`) that works across Claude Code, Copilot, Codex, Cursor, and others: https://github.com/vercel-labs/skills
- **Agent Skills spec** — the open standard, useful when writing your own so it's portable: https://agentskills.io

---

## Revised recommendation for your build

Given what's actually installable **and Obsidian-free**, here's how I'd adjust the plan:

1. **Install the real, Obsidian-free skills first.** `tc-tracker` from alirezarezvani/claude-skills for handoff/session-resume (verify no Obsidian dependency in its own SKILL.md). `RobotDisco/adhd-skills` for GTD triage and review rituals. `ravila4` **hooks only** (time injection + nudges) for pacing, skipping its Obsidian journaling/vault skills.
2. **Build the two that have no Obsidian-free installable equivalent:** `librarian` (a SKILL.md that indexes your git repo) and `mirror` (a short SKILL.md over `git log` + closed tasks). Both are small; use the chudi.dev posts as design specs.
3. **On the second-brain layer specifically:** with llm-wiki excluded, there is no off-the-shelf okf/Karpathy skill that runs without Obsidian — so your knowledge-base layer stays a build-your-own over your git repo, exactly as your main plan of attack already scopes it. Nothing installable shortcuts it under your constraint.
4. **Use the chudi.dev posts strictly as design references** when writing your own SKILL.md files — they're good specs, just not packages.

The net effect: a meaningful chunk of what you want is installable (tc-tracker, RobotDisco GTD, ravila4 hooks) — just not at the chudi.dev links I originally gave you. But the Obsidian exclusion removes the one skill that would have handed you the second brain ready-made, so the knowledge-base and librarian pieces remain things you build against your git repo.

---

## Sources

- ravila4/claude-adhd-skills (installable; use hooks + CLAUDE.md only — journaling/vault skills require Obsidian, excluded): https://github.com/ravila4/claude-adhd-skills
- RobotDisco/adhd-skills (installable GTD/brain marketplace): https://github.com/RobotDisco/adhd-skills
- alirezarezvani/claude-skills (installable; use tc-tracker — its llm-wiki second-brain plugin requires Obsidian and is excluded): https://github.com/alirezarezvani/claude-skills
- alirezarezvani/claude-skills CLAUDE.md (llm-wiki plugin detail): https://github.com/alirezarezvani/claude-skills/blob/main/CLAUDE.md
- GitHub adhd topic (browse installable skills): https://github.com/topics/adhd
- vercel-labs skills CLI (cross-agent installer): https://github.com/vercel-labs/skills
- chudi.dev five skills (design reference only, NOT installable): https://chudi.dev/blog/claude-code-skills-adhd-developers
- chudi.dev "no plugin, here's my workflow" (author confirms not packaged): https://chudi.dev/blog/claude-code-adhd-workflows

*Verify owner/repo names and install commands against each repo's current README before running — this ecosystem changes weekly, and similarly named skills are common.*
