---
name: skill-sync
description: "Synchronize Hermes agent skills across machines via GitHub. Push, pull, status, and resolve conflicts — with smart divergence detection and interactive resolution."
version: 1.0.0
category: productivity
metadata:
  hermes:
    tags: [github, sync, skills, backup, multi-machine]
---

# Skill Sync — Cross-Machine Skill Synchronization

Synchronize `~/.hermes/skills/` between multiple machines using a GitHub repository as the source of truth. Detects changes via SHA256 comparison, handles conflicts with a "latest-wins" default, and supports interactive resolution when skills diverge on two machines.

## When to Use

- Setting up a new machine — pull all your skills in one command
- After creating or editing a skill — push it so other machines get the update
- When you've edited the same skill on two machines — resolve the divergence
- Before a reinstall — push to ensure nothing is lost

## How It Works

```
┌──────────────┐         ┌──────────────────────┐         ┌──────────────┐
│  Machine A   │  push   │  GitHub Repo         │  pull   │  Machine B   │
│  (desktop)   │ ──────> │  hermes-custom-skills│ <────── │  (laptop)    │
│              │         │                      │         │              │
│  ~/.hermes/  │         │  manifest.json       │         │  ~/.hermes/  │
│  skills/     │         │  skills/             │         │  skills/     │
└──────────────┘         └──────────────────────┘         └──────────────┘
```

### Manifest-Driven

`manifest.json` in the repo tracks every skill with:
- **SHA256 hash** — detects content changes
- **Per-machine sync state** — knows what each machine last pushed
- **Timestamps** — resolves "latest wins" conflicts

### Sync Algorithm

For each skill, comparing local vs remote:

| Local | Remote | Action |
|-------|--------|--------|
| No | Yes | **Install** — new skill from repo |
| Yes | No | **Add** — new local skill to repo |
| Yes (same SHA) | Yes (same SHA) | **Skip** — no changes |
| Yes (newer SHA) | Yes (older SHA) | **Push** — local → remote |
| Yes (older SHA) | Yes (newer SHA) | **Pull** — remote → local |
| Yes (diverged SHA) | Yes (diverged SHA) | **⚠️ Conflict** — ask user |

### Divergence Detection

A skill is **diverged** when:
1. Local SHA ≠ Remote SHA
2. Local SHA ≠ the SHA last synced from this machine (meaning local was edited)
3. Remote SHA ≠ the SHA last synced from this machine (meaning another machine edited it)

Default behavior on `push`/`pull`: **skip diverged skills** and report them. The user runs `skill-sync resolve <name>` to choose.

## Commands

All commands are run through the sync script at `scripts/sync.py`.

### `skill-sync status`

Show what's different between local and remote. No changes are made.

```
✅ Unchanged:  158
📤 New locally:  2
📥 New in repo:  1
🔄 Changed:      3
⚠️  DIVERGED:     1
```

### `skill-sync push`

Push local changes to GitHub. Copies updated skills into the repo clone, regenerates `manifest.json`, commits, and pushes.

- New local skills → added to repo
- Updated local skills → updated in repo (if not diverged)
- Deleted local skills → removed from repo
- Diverged skills → skipped (reported)

### `skill-sync pull`

Pull remote changes to `~/.hermes/skills/`. Copies skills from the repo clone into the local skills directory.

- New remote skills → installed locally
- Updated remote skills → overwrite local (if not diverged)
- Diverged skills → skipped (reported)

### `skill-sync resolve <skill-name>`

Interactive resolution for a diverged skill:

```
Resolving: yt-transcribe
Local SHA:  abc123... (modified: 2026-06-14)
Remote SHA: def456...

Options:
  [1] Keep LOCAL  — overwrite remote with your version
  [2] Keep REMOTE — overwrite local with the repo version
  [3] Keep BOTH   — save remote as '{skill}.remote' variant
  [4] Show diff
```

## Setup

### Prerequisites

- Git installed and configured
- `gh` CLI authenticated (`gh auth status`)
- The repo cloned to `~/.hermes/skill-sync-repo/` (auto-cloned on first run)

### Environment

Set `HERMES_SYNC_MACHINE` to identify this machine in the manifest. Persist it in `~/.bashrc`:

```bash
export HERMES_SYNC_MACHINE="windows-desktop"  # or "macbook", "termux-android", "linux-server", etc.
echo 'export HERMES_SYNC_MACHINE="windows-desktop"' >> ~/.bashrc
```

### First Run

The sync script lives at `scripts/sync.py` within the skill directory.

```bash
python ~/.hermes/skills/skill-sync/scripts/sync.py status
```

The script auto-clones the repo on first run. If the repo already exists (cloned during setup), it runs `git pull` to fetch latest.

### Script Location

```
~/.hermes/skills/skill-sync/scripts/sync.py
```

Run it directly:
```bash
python ~/.hermes/skills/skill-sync/scripts/sync.py <command>
```

## Pitfalls

### Repo Not Cloned
First run auto-clones. If auto-clone fails (network, auth), manually:
```bash
gh repo clone Anesu/hermes-custom-skills ~/.hermes/skill-sync-repo
```

### Git Merge Conflicts in Repo
If the repo clone has uncommitted changes or merge conflicts, the sync will fail. Fix with:
```bash
cd ~/.hermes/skill-sync-repo
git stash    # or resolve manually
git pull origin main
```

### Large Number of Skills
The first push of 160+ skills may take a moment due to git staging. Subsequent syncs are fast — only changed files are processed.

### Windows Path Length
Some deeply nested skill paths may hit Windows' 260-character path limit. If you encounter `FileNotFoundError`, enable long paths in Windows or shorten skill names.

### Permission Denied on Push
Ensure `gh auth status` shows a token with `repo` scope. If pushing fails with 403, re-authenticate:
```bash
gh auth login --scopes repo
```

### First Pull on a New Machine
After the first `pull` on a machine that was never registered, all skills will show as **⚠️ DIVERGED** because the manifest has no sync records for this machine. This is expected — the files are actually identical. To fix:

1. After pull, verify files match: compare a few SHAs between local and `repo/skills/<category>/SKILL.md`
2. If files match, register this machine by updating `synced_machines` in manifest for every skill
3. **Also update the top-level `sha256`** for each skill — it may be stale from another machine's last push
4. Commit and push the manifest fix

Both the per-machine sync record AND the top-level SHA must be updated for a clean `status`. See `references/manifest-fixup.md` for the full fixup script.

### File Copies: Use Terminal, Not execute_code
The `execute_code` sandbox may not persist file writes (`shutil.copy2`, `write_file`) to the real filesystem. **Always use `terminal` with a Python heredoc** for bulk file copies between the repo clone and `~/.hermes/skills/`. Example:

```bash
python3 << 'PYEOF'
import json, hashlib, shutil
from pathlib import Path
# ... copy and verify loop ...
PYEOF
```

Verify copies by computing SHA256 on both source and destination after copying.

### Manifest SHA Drift
The top-level `sha256` in `manifest.json` reflects the file content at the time of the LAST push — which may have been from a different machine. After pulling, if local files match the repo files but `status` shows "changed remote", the manifest's top-level SHAs are stale. Recompute them from the actual repo files and update.
