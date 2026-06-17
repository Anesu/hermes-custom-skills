---
name: hermes-backup
description: "Full-state Hermes disaster recovery backup. Captures state.db, config, cron, history, sessions metadata. Wraps skill-sync + identity-sync. Pushes to PRIVATE GitHub repo."
version: 1.1.0
category: productivity
metadata:
  hermes:
    tags: [backup, disaster-recovery, state, private, github, multi-machine]
---

# Hermes Full-State Backup

Disaster recovery for your Digital Armor-Bearer. Captures the complete modifiable state of a Hermes instance — everything needed to restore your persona, skills, session history, and configuration on a new machine.

**PRIVATE REPO**: `Anesu/hermes-backups` — contains `state.db` snapshots (session data). Never make this public.

## What It Covers

| Layer | Asset | Mechanism |
|-------|-------|-----------|
| **Identity** | SOUL.md, USER.md, MEMORY.md, config.yaml | Triggers `identity-sync push` |
| **Skills** | All installed skill directories | Triggers `skill-sync push` |
| **Brain** | `state.db` (SQLite session store) | SQLite backup API (safe during writes) |
| **Config** | `config.yaml` | Direct capture |
| **Automation** | Cron job definitions | Exported via `hermes cron list` |
| **Memory** | CLI history (`.hermes_history`) | Direct capture |
| **Context** | Session metadata (titles, recency) | SQLite query — not full dumps |

## What It NEVER Transports

| Asset | Reason |
|-------|--------|
| `auth.json` | OAuth tokens — security boundary |
| `.env` | API keys — security boundary |
| `state.db-wal` / `state.db-shm` | SQLite WAL — ephemeral, not meaningful offline |
| `logs/` | Churn-heavy, large |
| `cache/` | Recoverable from network |

## Retention Policy

| Rule | Value |
|------|-------|
| Per-device snapshots | Keep last **3** |
| Global cap | Max **10** total across all devices |
| Auto-prune | Runs on every backup |

Backups older than the retention window are deleted from the repo. Git history preserves them in `git reflog` for 90 days.

## Quick Start

```bash
# One-time setup — pick your device name
export HERMES_SYNC_MACHINE="bazzite"          # Fedora desktop (auto-detected from hostname if unset)
# export HERMES_SYNC_MACHINE="termux-android"  # Android phone
# export HERMES_SYNC_MACHINE="windows-desktop" # Windows machine
echo 'export HERMES_SYNC_MACHINE="bazzite"' >> ~/.bashrc

# Clone the backup repo (one-time)
gh repo clone Anesu/hermes-backups ~/hermes-backups

# Run backup (script auto-detects device name from hostname if HERMES_SYNC_MACHINE unset)
python3 ~/.hermes/skills/hermes-backup/scripts/backup.py

# If gh is not authenticated, backup still saves locally — push when ready
```

## Restore from Backup

```bash
# 1. Clone the backup repo
gh repo clone Anesu/hermes-backups ~/hermes-backups-restore

# 2. Restore state.db snapshot
cp ~/hermes-backups-restore/backups/<device>/<timestamp>/state.db ~/.hermes/state.db

# 3. Restore config (REVIEW before using — paths may differ between machines)
cp ~/hermes-backups-restore/backups/<device>/<timestamp>/config.yaml ~/.hermes/config.yaml
# IMPORTANT: Review ~/.hermes/config.yaml — home directory paths, terminal.backend,
# and provider configs may need adjustment for this machine.

# 4. Restore skills (via skill-sync)
# Load the skill-sync skill and run: skill-sync pull

# 5. Restore identity (via identity-sync)
# Load the identity-sync skill and run: identity-sync pull

# 6. Re-authenticate
# auth.json and .env are NOT in the backup — re-run `hermes setup`
```

## Manifest Format

Each backup produces a `manifest.json`:

```json
{
  "device": "termux-android",
  "timestamp": "2026-06-16T10:30:00Z",
  "backup_id": "20260616-103000-termux-android",
  "assets": {
    "state_db": {"path": "state.db", "size": 9990144, "sha256": "abc123..."},
    "config_yaml": {"path": "config.yaml", "size": 14830, "sha256": "def456..."},
    "cron_definitions": {"path": "cron.json", "size": 1234, "count": 3},
    "cli_history": {"path": ".hermes_history", "size": 4567, "sha256": "..."},
    "sessions_meta": {"path": "sessions_meta.json", "size": 891, "sha256": "..."}
  },
  "excluded_security": {
    "auth_json": "SECURITY — OAuth tokens never leave device",
    "dot_env": "SECURITY — API keys never leave device"
  },
  "syncs_triggered": {
    "skill_sync": {"status": "pushed"},
    "identity_sync": {"status": "pushed"}
  }
}
```

## Cron Automation

Schedule automatic daily backups:

```bash
hermes cron create "daily 3am" \
  --prompt "Run the hermes-backup script: python3 ~/.hermes/skills/hermes-backup/scripts/backup.py" \
  --name "hermes-daily-backup"
```

Or via the `cronjob` tool during a session.

## Repo Structure

```
Anesu/hermes-backups/         (PRIVATE)
├── README.md
├── .gitignore                 # Blocks auth.json, .env, WAL files
├── manifest.json              # Global index of all snapshots
└── backups/
    ├── termux-android/
    │   ├── 20260616-103000/
    │   │   ├── manifest.json
    │   │   ├── state.db
    │   │   ├── config.yaml
    │   │   ├── cron.json
    │   │   ├── .hermes_history
    │   │   └── sessions_meta.json
    │   ├── 20260615-103000/
    │   └── 20260614-103000/
    └── windows-desktop/
        └── ...
```

## Pitfalls

| Problem | Fix |
|---------|-----|
| `HERMES_SYNC_MACHINE` not set | Script auto-detects from hostname. Set permanently: `export HERMES_SYNC_MACHINE="my-device" >> ~/.bashrc` |
| Repo not cloned (`~/hermes-backups/` missing) | `gh repo clone Anesu/hermes-backups ~/hermes-backups`. Backup saves locally without repo. |
| `gh` CLI not authenticated | `gh auth login --scopes repo`. Backup still saves locally; push skips. |
| `state.db` locked during backup | SQLite backup API handles concurrent writes safely on Linux/macOS. Falls back to file copy on Android or if API fails. |
| identity-sync / skill-sync scripts not found | Scripts may not exist on all machines. Backup skips syncs gracefully. Use agent-driven sync: load the `skill-sync` or `identity-sync` skill and ask Hermes to sync. |
| Git push fails (auth) | `gh auth status` — ensure `repo` scope. Token may need refresh. |
| Repo accidentally made public | Script verifies privacy before push. If public, abort and warn. |
| Restored `config.yaml` has wrong paths | Home directory, terminal.backend, and provider configs are machine-specific. Review after restore. |
| `hermes cron list` output format changes | Script parses human-readable output; if a future Hermes version changes the format, cron capture will return empty. |
| `python3` not found (Windows) | Use `python` instead, or update the `PATH`. Script is tested on Linux/macOS; Windows may need adjustments. |

## Design Principle

This skill is the **third leg** of Hermes state preservation:

1. `skill-sync` → Skills (public, live)
2. `identity-sync` → Persona (private, live)
3. `hermes-backup` → Brain + config + automation (private, periodic)

Together they provide complete cross-machine recovery. None of them transport secrets (auth.json, .env) — those must be reconfigured manually on each device.
