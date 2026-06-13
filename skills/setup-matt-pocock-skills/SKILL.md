---
name: setup-matt-pocock-skills
description: Sets up an `## Agent skills` block in AGENTS.md/CLAUDE.md and `docs/agents/` so the engineering skills know this repo's issue tracker (GitHub or local markdown), triage label vocabulary, and domain doc layout. Run before first use of `to-issues`, `to-prd`, `triage`, `diagnose`, `tdd`, `improve-codebase-architecture`, or `zoom-out` — or if those skills appear to be missing context about the issue tracker, triage labels, or domain docs.
disable-model-invocation: true
---

# Setup Matt Pocock's Skills

Scaffold the per-repo configuration that the engineering skills assume:

- **Issue tracker** — where issues live (GitHub by default; local markdown is also supported out of the box)
- **Triage labels** — the strings used for the five canonical triage roles
- **Domain docs** — where `CONTEXT.md` and ADRs live, and the consumer rules for reading them

This is a prompt-driven skill, not a deterministic script. Explore, present what you found, confirm with the user, then write.

## When to use the `npx skills add` form (installing into a local skills library)

If the user invokes the `npx skills add <source>` form — i.e. they want to *pull the mattpocock/skills repo into a Hermes skills library* rather than scaffold `AGENTS.md` in some project — read this section first. It is a different operation from steps 1-5 below.

**Step 0 — Inventory before install.** Before running `npx skills add`, list what is already installed locally (e.g. `ls ~/.hermes/skills/` or use whatever the host uses for skill discovery) and diff against the upstream repo's available skills. The CLI defaults to "all selected" in its interactive picker; running it blindly will either clobber locally customised copies of the same skill or install duplicates. Always pre-flight with `npx skills@latest add <source> --help` to confirm exact flags for the installed version.

**Step 0a — Pick the install scope.** Decide per-skill whether to:
- **install-new-only** — pass `--skill <name>` for each upstream skill NOT already present locally, with `-y` to skip prompts. Safe, additive, recommended.
- **full-replace** — overwrite local copies with upstream versions. Only when the user explicitly wants upstream as source of truth and has no local customisations worth keeping.
- **dry-run-first** — show the user the exact list of installs/skips and let them confirm before writing.

Default to **install-new-only** unless the user says otherwise. Surface the choice with a one-line callout before executing.

**Step 0b — Run from the right cwd.** The CLI installs into `<cwd>/.agents/skills/` by default (universal multi-agent layout). To target a specific skills library:
- For `~/.hermes/skills/`: `cd ~/.hermes/skills && npx -y skills@latest add <source> -y --skill <name1> --skill <name2> ...`
- The CLI's `--agent` flag selects consumer agents, not install path. Don't conflate them.

**Step 0c — Verify after install.** Confirm no clobber of pre-existing skills and that the new directories exist (the install lands in `.agents/skills/<name>/` and registers symlinks for the supported consumers). Cross-check with `ls <skills-root>/.agents/skills/` and compare against the pre-install inventory.

**Worked example (the mattpocock/skills install against an existing local library):**

```bash
# 1. List upstream skills (CLI prints them on first run with no --skill flag).
npx -y skills@latest add mattpocock/skills --help

# 2. Diff against local: which upstream skills are already in ~/.hermes/skills/ ?
ls ~/.hermes/skills/ | sort -u > /tmp/local-skills.txt
# (manually cross-reference against the CLI's printed skill list)

# 3. Install only the genuinely new ones, non-interactively, from the right cwd.
cd ~/.hermes/skills && npx -y skills@latest add mattpocock/skills -y \
  --skill improve-codebase-architecture \
  --skill teach \
  --skill design-an-interface \
  --skill review \
  # ... one --skill flag per new skill

# 4. Verify: no pre-existing skills were overwritten, all new dirs present.
ls -la ~/.hermes/skills/.agents/skills/
```

**Pitfalls:**
- The CLI's interactive picker shows "all selected" by default. If you forget `-y` or `--skill` flags, an unattended run will install the entire repo.
- The CLI prints a security risk table per skill (Gen / Socket / Snyk columns). Surface any High/Medium Risk flags to the user verbatim — do not silently absorb them.
- After install, the skills are "universal" and register as symlinks for multiple consumers (Claude Code, Hermes Agent, etc.). You do not need to manually wire them up.

## Process (project-level AGENTS.md / CLAUDE.md scaffolding)

### 1. Explore

Look at the current repo to understand its starting state. Read whatever exists; don't assume:

- `git remote -v` and `.git/config` — is this a GitHub repo? Which one?
- `AGENTS.md` and `CLAUDE.md` at the repo root — does either exist? Is there already an `## Agent skills` section in either?
- `CONTEXT.md` and `CONTEXT-MAP.md` at the repo root
- `docs/adr/` and any `src/*/docs/adr/` directories
- `docs/agents/` — does this skill's prior output already exist?
- `.scratch/` — sign that a local-markdown issue tracker convention is already in use

### 2. Present findings and ask

Summarise what's present and what's missing. Then walk the user through the three decisions **one at a time** — present a section, get the user's answer, then move to the next. Don't dump all three at once.

Assume the user does not know what these terms mean. Each section starts with a short explainer (what it is, why these skills need it, what changes if they pick differently). Then show the choices and the default.

**Section A — Issue tracker.**

> Explainer: The "issue tracker" is where issues live for this repo. Skills like `to-issues`, `triage`, `to-prd`, and `qa` read from and write to it — they need to know whether to call `gh issue create`, write a markdown file under `.scratch/`, or follow some other workflow you describe. Pick the place you actually track work for this repo.

Default posture: these skills were designed for GitHub. If a `git remote` points at GitHub, propose that. If a `git remote` points at GitLab (`gitlab.com` or a self-hosted host), propose GitLab. Otherwise (or if the user prefers), offer:

- **GitHub** — issues live in the repo's GitHub Issues (uses the `gh` CLI)
- **GitLab** — issues live in the repo's GitLab Issues (uses the [`glab`](https://gitlab.com/gitlab-org/cli) CLI)
- **Local markdown** — issues live as files under `.scratch/<feature>/` in this repo (good for solo projects or repos without a remote)
- **Other** (Jira, Linear, etc.) — ask the user to describe the workflow in one paragraph; the skill will record it as freeform prose

**Section B — Triage label vocabulary.**

> Explainer: When the `triage` skill processes an incoming issue, it moves it through a state machine — needs evaluation, waiting on reporter, ready for an AFK agent to pick up, ready for a human, or won't fix. To do that, it needs to apply labels (or the equivalent in your issue tracker) that match strings *you've actually configured*. If your repo already uses different label names (e.g. `bug:triage` instead of `needs-triage`), map them here so the skill applies the right ones instead of creating duplicates.

The five canonical roles:

- `needs-triage` — maintainer needs to evaluate
- `needs-info` — waiting on reporter
- `ready-for-agent` — fully specified, AFK-ready (an agent can pick it up with no human context)
- `ready-for-human` — needs human implementation
- `wontfix` — will not be actioned

Default: each role's string equals its name. Ask the user if they want to override any. If their issue tracker has no existing labels, the defaults are fine.

**Section C — Domain docs.**

> Explainer: Some skills (`improve-codebase-architecture`, `diagnose`, `tdd`) read a `CONTEXT.md` file to learn the project's domain language, and `docs/adr/` for past architectural decisions. They need to know whether the repo has one global context or multiple (e.g. a monorepo with separate frontend/backend contexts) so they look in the right place.

Confirm the layout:

- **Single-context** — one `CONTEXT.md` + `docs/adr/` at the repo root. Most repos are this.
- **Multi-context** — `CONTEXT-MAP.md` at the root pointing to per-context `CONTEXT.md` files (typically a monorepo).

### 3. Confirm and edit

Show the user a draft of:

- The `## Agent skills` block to add to whichever of `CLAUDE.md` / `AGENTS.md` is being edited (see step 4 for selection rules)
- The contents of `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, `docs/agents/domain.md`

Let them edit before writing.

### 4. Write

**Pick the file to edit:**

- If `CLAUDE.md` exists, edit it.
- Else if `AGENTS.md` exists, edit it.
- If neither exists, ask the user which one to create — don't pick for them.

Never create `AGENTS.md` when `CLAUDE.md` already exists (or vice versa) — always edit the one that's already there.

If an `## Agent skills` block already exists in the chosen file, update its contents in-place rather than appending a duplicate. Don't overwrite user edits to the surrounding sections.

The block:

```markdown
## Agent skills

### Issue tracker

[one-line summary of where issues are tracked]. See `docs/agents/issue-tracker.md`.

### Triage labels

[one-line summary of the label vocabulary]. See `docs/agents/triage-labels.md`.

### Domain docs

[one-line summary of layout — "single-context" or "multi-context"]. See `docs/agents/domain.md`.
```

Then write the three docs files using the seed templates in this skill folder as a starting point:

- [issue-tracker-github.md](./issue-tracker-github.md) — GitHub issue tracker
- [issue-tracker-gitlab.md](./issue-tracker-gitlab.md) — GitLab issue tracker
- [issue-tracker-local.md](./issue-tracker-local.md) — local-markdown issue tracker
- [triage-labels.md](./triage-labels.md) — label mapping
- [domain.md](./domain.md) — domain doc consumer rules + layout

For "other" issue trackers, write `docs/agents/issue-tracker.md` from scratch using the user's description.

### 5. Done

Tell the user the setup is complete and which engineering skills will now read from these files. Mention they can edit `docs/agents/*.md` directly later — re-running this skill is only necessary if they want to switch issue trackers or restart from scratch.
