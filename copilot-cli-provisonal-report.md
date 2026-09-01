# Provisional Report — Porting the Second-Brain / Delegation Plan to GitHub Copilot CLI

*How the recommendations in the main plan of attack change if the executing agent is **GitHub Copilot CLI** instead of Claude Code.*

**Status: provisional.** Copilot CLI went GA in February 2026 and ships changes constantly — commands, flags, file locations, and customization behavior move often. Everything below reflects the state of the tooling as of this writing (September 2026) and should be re-verified against the official GitHub Copilot CLI docs before you act on it. Treat this as a directional port, not a final build spec.

---

## Headline finding

**This is far less disruptive than a platform switch usually implies.** The core building block your entire plan rests on — the `SKILL.md` file — is an **open standard that both tools share**. A skill written for Claude Code works in Copilot CLI unchanged, because both read the same format: a folder containing a `SKILL.md` with `name` and `description` frontmatter plus optional supporting scripts. Copilot reads the same frontmatter fields and honors the same description-based activation model. Some agent-specific frontmatter fields are ignored by Copilot, but the core instructions work without modification.

So the plan doesn't get rewritten. It gets **re-pathed and re-sourced**. Your git-backed markdown knowledge base — the foundation of the whole system — is completely unaffected, because it was never tied to either agent. What changes is where skills live on disk, how you install community ones, and a few capability details around hooks, custom agents, and MCP.

---

## What stays exactly the same

- **Your okf/karpathy knowledge base.** It's a git repo of markdown; both agents read and write files and run git natively. Zero change.
- **The three-phase structure** of the main plan. Foundation-first, build-your-own second, integrate third — all still holds.
- **The delegation protocol and its artifacts.** The CLAUDE.md-equivalent instructions file, the AI-node template, and the human-brief template are all just markdown you author. None of them depend on the agent. (Note the filename change below.)
- **The `SKILL.md` files themselves** for your custom daily-capture skill and any of the engineering-five patterns you build. Author them once; they run on either agent.
- **The core discipline** — batch by delegation type, close the write-back loop, maintain retrieval quality. Agent-agnostic.

The portability cuts both ways and is worth knowing: if you build this on Copilot CLI and later move to Claude Code (or Codex, or Cursor), the skills travel with you. You are not locking into a vendor by choosing either one.

---

## What changes — by area

### 1. Where skills live (the main practical difference)

Claude Code reads skills from `.claude/skills/`. Copilot CLI is more permissive — it reads project skills from any of `.github/skills/`, `.claude/skills/`, or `.agents/skills/` inside the repo, and personal skills from `~/.copilot/skills/`, `~/.claude/skills/`, or `~/.agents/skills/` in your home directory.

**Important gotcha:** despite Copilot CLI *accepting* `.claude/skills/`, it only loads skills located **inside your repository** for project scope — a global `~/.claude/skills` folder that worked for Claude Code will **not** be picked up by Copilot CLI the same way. Community reports flag this as a common "my skills aren't detected" failure.

**Recommendation:** since you're building a portable system and may not want to commit to one agent, store your canonical skills in **`.agents/skills/`** — the vendor-neutral location that Copilot CLI reads natively (and Codex too). If you also want Claude Code to see them, add a thin stub in `.claude/skills/`. This keeps one canonical copy and avoids duplication drift. Requirements that trip people up: skill folder names should use dashes (e.g. `daily-capture`), and each needs valid `SKILL.md` frontmatter — a bare file in the right folder isn't enough.

### 2. How you install community skills (Phase 1 changes most here)

This is where your Phase 1 sourcing changes. The chudi.dev engineering-five and the ravila4 toolkit were written for Claude Code, but because the format is shared, the skills themselves are portable — what changes is the install path and marketplace.

- **The `.claude/skills` clone-and-copy approach** from the main plan (ravila4) still works if you copy into a repo-level `.agents/skills/` or `.github/skills/` instead of a global `~/.claude/skills`.
- **Copilot CLI has its own plugin ecosystem.** Community and custom plugins install directly from GitHub repos with `copilot plugin install owner/repo`. Plugins can bundle MCP servers, agents, skills, and hooks.
- **The Awesome Copilot marketplace** is pre-registered in recent Copilot CLI versions: `copilot plugin install <plugin-name>@awesome-copilot`. If your version reports an unknown marketplace, register once with `copilot plugin marketplace add github/awesome-copilot`.
- **Cross-agent skill installers exist.** The `gh skill` command in GitHub CLI searches, installs, updates, and publishes agent skills, and writes provenance metadata into the skill's frontmatter so `gh skill update` can track upstream changes. A `--agent copilot` flag wires a skill into the correct Copilot directory.

**Net effect on Phase 1:** the engineering-five are still "build/adapt from source" rather than one-command installs, exactly as in the main plan — but you now also have Copilot's native plugin/marketplace path and `gh skill` as installation routes for anything published to them. Check whether equivalents of pickup/librarian/triage already exist on Awesome Copilot or the broader skills directories before hand-building.

### 3. The instructions file: `AGENTS.md`, not `CLAUDE.md`

Copilot CLI's convention for persistent custom instructions is **`AGENTS.md`** (the emerging cross-tool standard), used together with Agent Skills to define behavior and tool access consistently across models and sessions. Your planned "CLAUDE.md section encoding the delegation protocol" becomes an **`AGENTS.md` section** with identical content. `AGENTS.md` is also read by Codex and other tools, so it's the more portable home for your protocol anyway.

**Recommendation:** author the delegation protocol in `AGENTS.md`. If you keep a `CLAUDE.md` for Claude Code, have it reference `AGENTS.md` rather than duplicating the rules.

### 4. Custom agents — a capability Copilot adds

Copilot CLI has a first-class **custom agents** concept: specialized agent "profiles" defined via `.agent.md` files (or an interactive wizard), each able to specify its own tools, MCP servers, and instructions, selectable with `/agent`. This is genuinely useful for your delegation goal and doesn't have a direct Claude Code equivalent in the main plan.

**Recommendation:** consider a dedicated **"reviewer" custom agent** and a **"delegator" custom agent** as an optional Phase 2/3 enhancement. A reviewer profile tuned to what you check as sole approver could pre-screen developer PRs against your standards before they hit your queue — directly attacking your most expensive recurring task. Note that recent VS Code/Copilot CLI versions can also read Claude-format agents from `.claude/agents/`, so these are somewhat portable too.

### 5. Hooks — supported, but re-verify the config

The ravila4 nudge + time hooks from your Phase 1/2 pacing layer have a home: Copilot CLI supports **hooks** that run custom shell commands automatically at key points in a session. The *concept* ports directly. What changes is the wiring — ravila4's hooks were written against Claude Code's `settings.json` hook schema, so you'll need to adapt them to Copilot CLI's hook configuration rather than copy them verbatim.

**Recommendation:** treat the hooks as "adapt," not "drop in." Re-verify the current hook config format in the Copilot CLI docs, since this is one of the fast-moving areas.

### 6. MCP and code review — a notable bonus for your role

Two Copilot-native capabilities are worth folding into your plan because they hit your specific job as sole review approver:

- **Built-in GitHub MCP server.** Copilot CLI ships with GitHub's MCP server pre-configured, so it can search issues, analyze labels/activity, summarize scope, and even merge PRs from the terminal. For a review-heavy lead, this means task-tracking and PR triage can run against live GitHub state, not just your local knowledge base. Custom MCP servers are added via `mcp-config.json` in `~/.copilot`.
- **Copilot code review now supports agent skills + MCP** (GA as of July 2026). You can add a `SKILL.md` under `.github/skills` that injects your team's coding standards and internal tools into **every** Copilot code review, and pull context from third-party systems via MCP.

**Recommendation:** this is a real argument in Copilot's favor *for your specific situation*. If your developers' PRs get an automated first-pass review against your encoded standards before reaching you, your bottleneck as sole approver shrinks. Encode your review checklist as a skill in `.github/skills` and let it run at review time. This is arguably the single biggest role-specific win in the whole port.

### 7. Model flexibility

Copilot CLI supports models from multiple providers (Anthropic, Google, OpenAI) and lets you switch per task or use `/model` to compare approaches, with plan/autopilot modes toggled via Shift+Tab. Not central to your plan, but relevant if you want a cheaper model for capture/journaling and a stronger one for review or complex delegation.

---

## Revised phase notes (deltas only)

**Phase 1 — out of the box**
- Same skills, but store canonical copies in `.agents/skills/` (repo-level), not global `~/.claude/skills`.
- Check Awesome Copilot marketplace and `gh skill` for existing pickup/librarian/triage equivalents before hand-building.
- Turn on Copilot's built-in GitHub MCP server immediately — it covers issue/PR triage that would otherwise need custom work.

**Phase 2 — build for your environment**
- `AGENTS.md` replaces the `CLAUDE.md` section for the delegation protocol.
- Daily-capture `SKILL.md` is authored identically; just place it in `.agents/skills/`.
- **New option:** build a "reviewer" custom agent (`.agent.md`) encoding your approval standards.
- Adapt (don't copy) the ravila4 hooks to Copilot's hook config.

**Phase 3 — integrate**
- **New leverage:** wire your review-standards skill into Copilot code review (`.github/skills`) so developer PRs are pre-screened before your queue — the biggest role-specific gain.
- Write-back loop, batching, and quarterly prune are unchanged.
- Use MCP to let the system read live GitHub state (issues, PR status) alongside the local knowledge base as the single source of truth.

---

## Bottom line

Switching to Copilot CLI **does not invalidate the plan** — the knowledge base, the phase structure, the delegation artifacts, and the `SKILL.md` skills all carry over because they sit on an open standard. The real deltas are: skills live in `.agents/skills/` (repo-scoped), instructions live in `AGENTS.md`, community install runs through Copilot's plugin marketplace / `gh skill`, and hooks need re-wiring. In exchange, Copilot CLI *adds* three things that matter for a sole review approver: custom agents, a built-in GitHub MCP server, and agent-skill-powered code review — the last of which could cut your review bottleneck more directly than anything in the Claude Code version of the plan.

If you're genuinely weighing the two, the deciding factor for *your* role probably isn't the second-brain layer (near-identical on both) but the review layer: Copilot's native code-review-skill integration is a meaningful edge if your bottleneck is being the single approver over three developers.

---

## Sources consulted (verify before acting — this space moves fast)

- GitHub Copilot CLI GA announcement (skills, plugins, custom agents, MCP): https://github.blog/changelog/2026-02-25-github-copilot-cli-is-now-generally-available/
- Copilot code review — agent skills + MCP GA: https://github.blog/changelog/2026-07-29-copilot-code-review-agent-skills-and-mcp-now-generally-available/
- Using GitHub Copilot CLI (hooks, MCP, config paths): https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/overview
- Adding agent skills for Copilot CLI (SKILL.md, skill dirs, allowed-tools): https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills
- Cross-compatibility of SKILL.md / AGENTS.md across Claude Code, Copilot, Codex: https://raffertyuy.com/raztype/claude-copilot-codex-cross-compatibility/
- One skill for both Claude Code and Copilot CLI (watched paths, distribution models): https://www.allaboutken.com/posts/20260408-mini-guide-claude-copilot-skills/
- Copilot CLI features overview (models, subagents, plan/autopilot): https://github.com/features/copilot/cli
- Awesome Copilot marketplace (plugin install): https://github.com/github/awesome-copilot
- Community discussion on skill detection gotchas: https://github.com/orgs/community/discussions/183396

*Provisional as of September 2026. Copilot CLI changes frequently; treat every command, path, and capability above as subject to change and confirm against current official docs before building.*
