# Hermes Custom Skills

**Version-controlled skill repository for Hermes Agent — synced across machines.**

This repo tracks all user-installed Hermes agent skills from `~/.hermes/skills/`. It serves as the source of truth for synchronizing skills between multiple machines (desktop, laptop, server) and provides conflict-aware resolution when skills diverge.

## Structure

```
hermes-custom-skills/
├── README.md              # This file
├── manifest.json           # Master inventory — SHAs, versions, sync state per machine
├── .gitignore
├── skills/                 # Skill files, mirrored from ~/.hermes/skills/
│   ├── productivity/
│   │   ├── yt-transcribe/
│   │   │   └── SKILL.md
│   │   └── ...
│   ├── software-development/
│   │   └── ...
│   └── ...
└── .github/
    └── workflows/          # CI (future: auto-validate skills on push)
```

## How It Works

### Sync Flow

```
Machine A                     GitHub (hermes-custom-skills)              Machine B
─────────                     ─────────────────────────────              ─────────
1. skill-sync push ──────────> manifest.json + skills/ updated
                                                                         2. skill-sync pull
                                                                            <── fetch + merge
                                                                            skills installed locally
```

### Conflict Resolution

When the same skill has been modified on two different machines since the last sync:

- **Default**: The version with the latest timestamp wins (newest-first).
- **Diverged skills**: If both versions have local changes not present in the remote, the sync pauses and asks which version to keep.
- **Manual override**: Run `skill-sync resolve <skill-name>` to choose interactively.
- **Keep both**: Append `.machine-name` suffix to one version and sync both.

### Manifest

`manifest.json` tracks every skill with:

| Field | Purpose |
|-------|---------|
| `sha256` | Content hash — used to detect changes and conflicts |
| `skill_version` | Version from the skill's YAML frontmatter |
| `last_modified` | Filesystem timestamp from last local edit |
| `synced_machines` | Per-machine record of last sync state |

## Quick Start

### On a new machine

```bash
git clone https://github.com/Anesu/hermes-custom-skills.git ~/hermes-custom-skills
# Then run the skill-sync skill to install all skills locally
```

### Pushing local changes

```bash
skill-sync push    # Scan ~/.hermes/skills/, detect changes, commit, push
```

### Pulling remote changes

```bash
skill-sync pull    # Fetch from GitHub, detect conflicts, apply updates
```

### Checking status

```bash
skill-sync status  # Show diff: what's changed locally vs remote
```

## Skill Sources

Skills in this repo come from:

| Source | Examples |
|--------|----------|
| **User-created** | `yt-transcribe`, `skill-sync` (this workflow) |
| **Hermes marketplace** | `firecrawl-*`, `baoyu-*`, `claude-code` |
| **Plugins** | `github-*`, `creative/*` |
| **Third-party** | `guizang-ppt-skill`, `caveman` |

All are tracked — not just hand-authored skills — because marketplace and plugin skills don't auto-reinstall on a new machine.

## Contributing

This is a personal skill repository. To add a new custom skill:

1. Create the skill in `~/.hermes/skills/<category>/<skill-name>/SKILL.md`
2. Run `skill-sync push`
3. On other machines, run `skill-sync pull`

---

*Managed by the `skill-sync` Hermes agent skill.*
