---
name: skill-sync
description: "Synchronize ~/.hermes/skills/ across machines via GitHub. Push, pull, status, resolve conflicts."
version: 1.1.0
category: productivity
metadata:
  hermes:
    tags: [github, sync, skills, backup, multi-machine]
---

# Skill Sync

Sync `~/.hermes/skills/` across machines via a GitHub repo (`Anesu/hermes-custom-skills`). Detects changes via SHA256, resolves conflicts with latest-wins default.

**Model:** local skills ↔ GitHub repo ↔ remote machines. `manifest.json` tracks SHA256 hashes per skill + per-machine sync state.

## Quick Reference

```bash
export HERMES_SYNC_MACHINE="termux-android"  # set once, persist in ~/.bashrc

python3 ~/.hermes/skills/skill-sync/scripts/sync.py status
python3 ~/.hermes/skills/skill-sync/scripts/sync.py push
python3 ~/.hermes/skills/skill-sync/scripts/sync.py pull
python3 ~/.hermes/skills/skill-sync/scripts/sync.py resolve <skill-name>
```

## Commands

| Command | What it does |
|---|---|
| `status` | Show diff: unchanged, new local, new remote, changed, diverged. No changes. |
| `push` | Local → GitHub. New/updated skills pushed. Deleted skills removed from repo. Diverged skipped. |
| `pull` | GitHub → local. New/updated remote skills installed. Diverged skipped. |
| `resolve <name>` | Interactive: keep local, keep remote, keep both, or show diff. |

## Sync Logic

| Local | Remote | Action |
|---|---|---|
| No | Yes | Install |
| Yes | No | Add to repo |
| Same SHA | Same SHA | Skip |
| Newer SHA | Older SHA | Push |
| Older SHA | Newer SHA | Pull |
| Diverged SHA | Diverged SHA | ⚠️ Conflict — resolve |

**Diverged =** local SHA ≠ remote, both differ from this machine's last-synced SHA (edited on two machines independently).

## Setup

```bash
# Repo auto-clones on first status/push. If it fails:
gh repo clone Anesu/hermes-custom-skills ~/.hermes/skill-sync-repo

# Set machine identity:
export HERMES_SYNC_MACHINE="termux-android"
echo 'export HERMES_SYNC_MACHINE="termux-android"' >> ~/.bashrc
```

## Pitfalls

| Problem | Fix |
|---|---|
| Repo not cloned / auth fails | `gh repo clone Anesu/hermes-custom-skills ~/.hermes/skill-sync-repo` |
| Git merge conflicts in repo clone | `cd ~/.hermes/skill-sync-repo && git stash && git pull` |
| Permission denied (403) on push | `gh auth login --scopes repo` |
| First pull on new machine shows all DIVERGED | Expected — files match but manifest has no records for this machine. See `references/manifest-fixup.md`. |
| Windows path length (260-char limit) | Enable long paths or shorten skill directory names |
| Manifest SHA drift after pull from another machine | Top-level SHA may be stale. Recompute from actual repo files and update. |
