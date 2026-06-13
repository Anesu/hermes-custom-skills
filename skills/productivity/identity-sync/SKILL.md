---
name: identity-sync
description: "Synchronize Hermes identity files (SOUL.md, USER.md, MEMORY.md, config.yaml) across machines via a private GitHub repo. Personality transplant in one command."
version: 1.0.0
category: productivity
metadata:
  hermes:
    tags: [github, sync, identity, soul, backup, multi-machine, private]
---

# Identity Sync — Cross-Machine Personality Replication

Synchronize the four files that make Hermes *your* Hermes — SOUL.md, USER.md, MEMORY.md, and config.yaml — between machines using a private GitHub repository. Restore your Digital Armor-Bearer persona on any new machine with a single `identity-sync pull`.

## When to Use

- **New machine setup** — restore your entire Hermes identity in one command
- **After editing SOUL.md** — push so your persona stays consistent across machines
- **After a memory update** — keep persistent memory synced
- **Before a reinstall** — push to ensure nothing is lost
- **When USER.md changes** — salary, debt, goals updated? Sync it.

## What Gets Synced

| File | Restores |
|------|----------|
| `SOUL.md` | Agent identity, communication style, hard boundaries, Sola Scriptura worldview |
| `USER.md` | Your bio, finances, Patience, career details, Unified Wealth Philosophy |
| `MEMORY.md` | Tech facts, RTX 3090 paths, Rungano TTS, Levite system, environment quirks |
| `config.yaml` | Model selection, TTS voice (Anesu/Shona), memory limits, tool configuration |

## What Does NOT Get Synced

- **`auth.json`** — API keys and tokens (never committed)
- **`~/.hermes/skills/`** — Use `skill-sync` for that (public repo)
- **`~/.hermes/cron/`** — Scheduled jobs (future)
- **Project `AGENTS.md` files** — These live in individual repos

> ⚠️ **This is a private repo.** USER.md contains your salary, debt, and relationship details. Never make the identity repo public.

## How It Works

```
┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│  Machine A   │  push   │  GitHub Repo     │  pull   │  Machine B   │
│  (desktop)   │ ──────> │  hermes-identity │ <────── │  (laptop)    │
│              │         │  (PRIVATE)       │         │              │
│  SOUL.md     │         │                  │         │  SOUL.md     │
│  USER.md     │         │  manifest.json   │         │  USER.md     │
│  MEMORY.md   │         │  + identity files│         │  MEMORY.md   │
│  config.yaml │         │                  │         │  config.yaml │
└──────────────┘         └──────────────────┘         └──────────────┘
```

### Conflict Resolution

| Scenario | Default Behavior |
|----------|-----------------|
| Local newer than remote | Push wins — local overwrites remote |
| Remote newer than local | Pull wins — remote overwrites local |
| Both modified since last sync (**diverged**) | Skipped — manual resolution required |
| File deleted locally | Removed from remote on next push |

**For diverged files**, run `identity-sync resolve <filename>` to choose:
- `[1]` Keep LOCAL
- `[2]` Keep REMOTE
- `[3]` Keep BOTH (save remote as `.remote` variant)
- `[4]` Show diff

USER.md and MEMORY.md are **never auto-overwritten** when diverged — they require explicit resolution due to their personal nature.

## Commands

### `identity-sync status`

Show what's different between local and remote identity files. Read-only.

```
✅ SOUL.md       — in sync
✅ USER.md       — in sync
🔄 MEMORY.md     — local newer
⚠️  config.yaml  — DIVERGED (modified on both sides)
```

### `identity-sync push`

Push local identity files to the private GitHub repo. Updates manifest, commits, and pushes.

### `identity-sync pull`

Restore identity files from the repo to `~/.hermes/`. Skips diverged files.

### `identity-sync resolve <filename>`

Interactive conflict resolution for a specific file (SOUL.md, USER.md, MEMORY.md, or config.yaml).

---

## Setup

### Prerequisites

- Git installed and configured
- `gh` CLI authenticated with `repo` scope
- Access to the private repo `Anesu/hermes-identity`

### First Run

```bash
cd ~/.hermes/skills/productivity/identity-sync
python scripts/identity_sync.py status
```

The repo auto-clones to `~/.hermes/identity-sync-repo/` on first run.

### Environment

```bash
export HERMES_SYNC_MACHINE="windows-desktop"
```

## New Machine Bootstrap

On a brand-new machine with Hermes installed:

```bash
# 1. Clone identity
gh repo clone Anesu/hermes-identity ~/hermes-identity

# 2. Clone skills
gh repo clone Anesu/hermes-custom-skills ~/hermes-custom-skills

# 3. Restore identity (loads the identity-sync skill, runs pull)
#    → SOUL.md, USER.md, MEMORY.md, config.yaml land in ~/.hermes/

# 4. Restore skills (loads the skill-sync skill, runs pull)
#    → All 163 skills land in ~/.hermes/skills/

# 5. Re-authenticate (auth tokens are NOT synced)
#    → Set up API keys in ~/.hermes/auth.json or via hermes setup
```

Your Hermes is now identical to your desktop — same persona, same memory, same skills.

## Pitfalls

### Private Repo Access Denied
If `gh auth status` doesn't show `repo` scope, re-authenticate:
```bash
gh auth login --scopes repo
```

### config.yaml Conflicts
config.yaml changes frequently (Hermes auto-updates settings). Diverged config files are common. Use `identity-sync resolve config.yaml` to diff and choose.

### Sensitive Data in Unexpected Places
USER.md and MEMORY.md contain personal information. Never make the identity repo public. If you accidentally do, rotate all referenced information immediately.

### Auth Tokens Not Synced
After pulling identity files to a new machine, API calls will fail until you re-authenticate. Run `hermes setup` or manually populate `auth.json`.

### Memory Lock Files
Hermes may hold a lock on MEMORY.md or USER.md during active sessions. If pull fails with a permission error, wait for the session to end or close the lock file.
