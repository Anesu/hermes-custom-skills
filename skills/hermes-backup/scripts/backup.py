#!/usr/bin/env python3
"""
Hermes Full-State Backup — Disaster Recovery for the Digital Armor-Bearer.

Collect → Sync → Snapshot → Push → Prune

PRIVATE REPO: Anesu/hermes-backups
NEVER commits auth.json or .env — those stay local.
"""

import json
import os
import shutil
import sqlite3
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
BACKUP_REPO = Path.home() / "hermes-backups"
DEVICE = os.environ.get("HERMES_SYNC_MACHINE", "unknown-device")

RETENTION = {
    "per_device": 3,       # Keep last N snapshots per device
    "max_total": 10,       # Hard cap across all devices
}

# Assets we capture (relative to HERMES_HOME)
CAPTURE_ASSETS = {
    "state_db": "state.db",
    "config_yaml": "config.yaml",
    "cli_history": ".hermes_history",
    "skills_prompt_snapshot": ".skills_prompt_snapshot.json",
}

# Assets we NEVER transport (security boundary)
NEVER_TRANSPORT = [
    "auth.json",
    ".env",
    "shared/nous_auth.json",
]

# Assets we document but skip (too large / ephemeral)
SKIP_AND_NOTE = {
    "state_db_wal": ("state.db-wal", "SQLite WAL — ephemeral, not meaningful offline"),
    "state_db_shm": ("state.db-shm", "SQLite shared memory — ephemeral"),
    "logs": ("logs/", "Churn-heavy; use `tail -100` if needed"),
    "cache": ("cache/", "Recoverable; model metadata re-downloads"),
}


def sha256_file(path: Path) -> str:
    """SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_sqlite(src: Path, dst: Path) -> str:
    """Safe SQLite backup. Uses SQLite backup API on standard Linux/macOS;
    falls back to file copy on Android/Termux where the backup API is unstable."""
    # Android/Termux: sqlite3 backup API can SIGABRT on cleanup.
    if "ANDROID" in os.environ.get("PREFIX", "") or "com.termux" in str(Path.home()):
        shutil.copy2(src, dst)
        return "file copy (Android-safe)"

    # Standard Linux/macOS: use SQLite online backup API (safe during writes)
    try:
        src_conn = sqlite3.connect(str(src))
        dst_conn = sqlite3.connect(str(dst))
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        return "sqlite3 backup API"
    except Exception as e:
        print(f"  [WARN] SQLite backup API failed ({e}), falling back to file copy")
        shutil.copy2(src, dst)
        return "file copy (fallback)"


def export_cron(definitions: list, dst: Path):
    """Export cron definitions to JSON."""
    with open(dst, "w") as f:
        json.dump({"device": DEVICE, "timestamp": datetime.now(timezone.utc).isoformat(),
                    "count": len(definitions), "definitions": definitions}, f, indent=2)


def export_sessions_meta(dst: Path):
    """Export session metadata (count, recent titles) without full dumps."""
    state_db = HERMES_HOME / "state.db"
    if not state_db.exists():
        return

    try:
        conn = sqlite3.connect(str(state_db))
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT COUNT(*) as count FROM sessions")
        total = cur.fetchone()["count"]

        cur = conn.execute(
            "SELECT id, title, started_at, ended_at, message_count "
            "FROM sessions ORDER BY started_at DESC LIMIT 20"
        )
        recent = [dict(r) for r in cur.fetchall()]
        conn.close()

        with open(dst, "w") as f:
            json.dump({"total_sessions": total, "recent_sessions": recent}, f, indent=2)
    except Exception as e:
        print(f"  [WARN] Session metadata export failed: {e}")


def collect_cron_defs() -> list:
    """Collect cron job definitions via Hermes CLI if available.
    Falls back to parsing human-readable output since --json flag doesn't exist."""
    try:
        result = subprocess.run(
            ["hermes", "cron", "list"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return []
        output = result.stdout.strip()
        if not output or "No scheduled jobs" in output:
            return []
        # Parse human-readable output into structured list
        # Output format: each job on a line like "<id>  <schedule>  <status>  <name>"
        jobs = []
        for line in output.split("\n"):
            line = line.strip()
            if line and not line.startswith("No "):
                parts = line.split(None, 3)
                if len(parts) >= 2:
                    jobs.append({
                        "id": parts[0],
                        "schedule": parts[1],
                        "status": parts[2] if len(parts) > 2 else "?",
                        "name": parts[3] if len(parts) > 3 else "",
                    })
        return jobs
    except Exception:
        return []


def trigger_skill_sync() -> dict:
    """Trigger skill-sync push. Returns status.
    Tries script first; falls back to agent-driven sync (Path B in skill-sync docs).
    The script may not exist on all machines — agent-driven is always available."""
    # Try both possible script locations (categorized vs root-level)
    candidates = [
        HERMES_HOME / "skills" / "productivity" / "skill-sync" / "scripts" / "sync.py",
        HERMES_HOME / "skills" / "skill-sync" / "scripts" / "sync.py",
    ]
    sync_script = None
    for c in candidates:
        if c.exists():
            sync_script = c
            break

    if not sync_script:
        return {"status": "skipped",
                "reason": "skill-sync script not found (use agent-driven sync via skill-sync skill)"}
    try:
        result = subprocess.run(
            ["python3", str(sync_script), "push"],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "HERMES_SYNC_MACHINE": DEVICE}
        )
        return {"status": "pushed" if result.returncode == 0 else "failed",
                "exit_code": result.returncode,
                "stderr": result.stderr[-500:] if result.stderr else ""}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def trigger_identity_sync() -> dict:
    """Trigger identity-sync push. Returns status. (Requires private repo access)"""
    candidates = [
        HERMES_HOME / "skills" / "productivity" / "identity-sync" / "scripts" / "identity_sync.py",
        HERMES_HOME / "skills" / "identity-sync" / "scripts" / "identity_sync.py",
    ]
    identity_script = None
    for c in candidates:
        if c.exists():
            identity_script = c
            break

    if not identity_script:
        return {"status": "skipped",
                "reason": "identity-sync script not found (use agent-driven sync via identity-sync skill)"}
    try:
        result = subprocess.run(
            ["python3", str(identity_script), "push"],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "HERMES_SYNC_MACHINE": DEVICE}
        )
        return {"status": "pushed" if result.returncode == 0 else "failed",
                "exit_code": result.returncode}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def apply_retention(repo: Path, device: str):
    """Prune old backups: keep last N per device, max M total."""
    backups_dir = repo / "backups"
    if not backups_dir.exists():
        return

    device_dir = backups_dir / device
    if not device_dir.exists():
        return

    # Sort backups by name (timestamp) descending
    backups = sorted(
        [d for d in device_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name, reverse=True
    )

    # Keep last N per device
    keep = RETENTION["per_device"]
    to_prune = backups[keep:]
    for d in to_prune:
        print(f"  [PRUNE] {device}/{d.name} (per-device limit: {keep})")
        shutil.rmtree(d)


def apply_global_retention(repo: Path):
    """Hard cap: max RETENTION['max_total'] backups across all devices."""
    backups_dir = repo / "backups"
    if not backups_dir.exists():
        return

    all_backups = []
    for device_dir in backups_dir.iterdir():
        if device_dir.is_dir():
            for backup_dir in device_dir.iterdir():
                if backup_dir.is_dir():
                    all_backups.append((device_dir.name, backup_dir))

    if len(all_backups) <= RETENTION["max_total"]:
        return

    # Sort by name (timestamp) descending, prune oldest
    all_backups.sort(key=lambda x: x[1].name, reverse=True)
    for device, backup_dir in all_backups[RETENTION["max_total"]:]:
        print(f"  [PRUNE] {device}/{backup_dir.name} (global cap: {RETENTION['max_total']})")
        shutil.rmtree(backup_dir)


def build_manifest(assets: dict, syncs: dict) -> dict:
    """Construct the per-snapshot manifest."""
    return {
        "device": DEVICE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "backup_id": datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{DEVICE}",
        "assets": assets,
        "excluded_security": {
            "auth_json": "SECURITY — OAuth tokens never leave device",
            "dot_env": "SECURITY — API keys never leave device",
            "shared_nous_auth": "SECURITY — Shared auth never transported",
        },
        "skipped": {k: v[1] for k, v in SKIP_AND_NOTE.items()},
        "syncs_triggered": syncs,
    }


def check_gh_auth() -> bool:
    """Check if gh CLI is authenticated for Git operations."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def preflight_check() -> dict:
    """Run pre-flight checks. Returns {status: 'ok'|'warn'|'block', issues: [...]}."""
    issues = []

    # Report detected device name
    issues.append({
        "level": "info",
        "msg": f"Device name: '{DEVICE}' (set via HERMES_SYNC_MACHINE={DEVICE})",
    })

    # Check state.db
    state_db = HERMES_HOME / "state.db"
    if not state_db.exists():
        issues.append({"level": "block", "msg": "state.db not found — nothing to back up"})

    # Check gh auth
    if not check_gh_auth():
        issues.append({
            "level": "warn",
            "msg": "gh CLI not authenticated. Push to GitHub will fail.",
            "fix": "gh auth login --scopes repo",
        })

    # Check backup repo
    if not BACKUP_REPO.exists():
        issues.append({
            "level": "block",
            "msg": f"Backup repo not found at {BACKUP_REPO}",
            "fix": "gh repo clone Anesu/hermes-backups ~/hermes-backups",
        })

    return {
        "status": "block" if any(i["level"] == "block" for i in issues) else
                  "warn" if issues else "ok",
        "issues": issues,
    }


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    global DEVICE

    # ── Auto-detect DEVICE name from hostname if not set ──
    if DEVICE == "unknown-device":
        import platform
        DEVICE = platform.node().split(".")[0] or "fedora-linux"
        os.environ["HERMES_SYNC_MACHINE"] = DEVICE

    print("═" * 50)
    print("HERMES FULL-STATE BACKUP")
    print(f"  Device:  {DEVICE}")
    print(f"  Source:  {HERMES_HOME}")
    print(f"  Repo:    {BACKUP_REPO}")
    print("═" * 50)

    # ── Pre-flight checks ──
    print("\n[0/5] Pre-flight checks...")
    checks = preflight_check()

    for issue in checks["issues"]:
        prefix = {"block": "[FATAL]", "warn": "[WARN]", "info": "[INFO]"}.get(issue["level"], "[?]")
        print(f"  {prefix} {issue['msg']}")
        if "fix" in issue:
            print(f"         Fix: {issue['fix']}")

    if checks["status"] == "block":
        print("\n[CANNOT PROCEED] Fix the blocking issues above, then re-run.")
        sys.exit(1)

    if checks["status"] == "warn":
        print("  (Non-blocking warnings — backup will proceed, but push may fail)\n")

    # ── Phase 1: Create backup directory ──
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKUP_REPO / "backups" / DEVICE / ts
    backup_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[1/5] Backup directory: {backup_dir}")

    # ── Phase 2: Capture assets ──
    assets = {}
    print("\n[2/5] Capturing state...")

    for name, rel_path in CAPTURE_ASSETS.items():
        src = HERMES_HOME / rel_path
        dst = backup_dir / rel_path
        if not src.exists():
            print(f"  [SKIP] {rel_path} — not found")
            continue

        if name == "state_db":
            dst.parent.mkdir(parents=True, exist_ok=True)
            method = backup_sqlite(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            method = "copy"

        size = dst.stat().st_size
        sha = sha256_file(dst)
        assets[name] = {"path": rel_path, "size": size, "sha256": sha, "method": method}
        print(f"  [OK] {rel_path}  ({size:,} bytes)")

    # ── Cron definitions ──
    cron_defs = collect_cron_defs()
    if cron_defs:
        cron_path = backup_dir / "cron.json"
        export_cron(cron_defs, cron_path)
        size = cron_path.stat().st_size
        sha = sha256_file(cron_path)
        assets["cron_definitions"] = {"path": "cron.json", "size": size, "sha256": sha,
                                       "count": len(cron_defs)}
        print(f"  [OK] cron.json  ({len(cron_defs)} jobs, {size:,} bytes)")
    else:
        print("  [SKIP] No cron jobs found")

    # ── Session metadata ──
    sessions_path = backup_dir / "sessions_meta.json"
    export_sessions_meta(sessions_path)
    if sessions_path.exists():
        size = sessions_path.stat().st_size
        sha = sha256_file(sessions_path)
        assets["sessions_meta"] = {"path": "sessions_meta.json", "size": size, "sha256": sha}
        print(f"  [OK] sessions_meta.json  ({size:,} bytes)")

    # ── Phase 3: Trigger live syncs ──
    print("\n[3/5] Triggering live syncs...")
    syncs = {}

    print("  skill-sync push...")
    syncs["skill_sync"] = trigger_skill_sync()
    print(f"    → {syncs['skill_sync']['status']}")

    print("  identity-sync push...")
    syncs["identity_sync"] = trigger_identity_sync()
    print(f"    → {syncs['identity_sync']['status']}")

    # ── Phase 4: Write manifest ──
    print("\n[4/5] Writing manifest...")
    manifest = build_manifest(assets, syncs)
    manifest_path = backup_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  [OK] {manifest_path}")

    # Update global manifest
    global_manifest_path = BACKUP_REPO / "manifest.json"
    try:
        if global_manifest_path.exists():
            with open(global_manifest_path) as f:
                global_manifest = json.load(f)
        else:
            global_manifest = {"devices": {}, "snapshots": []}
    except (json.JSONDecodeError, FileNotFoundError):
        global_manifest = {"devices": {}, "snapshots": []}

    # Update device entry
    global_manifest["devices"][DEVICE] = {
        "last_backup": manifest["timestamp"],
        "backup_count": global_manifest["devices"].get(DEVICE, {}).get("backup_count", 0) + 1,
    }
    # Keep last 50 entries
    global_manifest["snapshots"].append({
        "backup_id": manifest["backup_id"],
        "device": DEVICE,
        "timestamp": manifest["timestamp"],
    })
    global_manifest["snapshots"] = global_manifest["snapshots"][-50:]

    with open(global_manifest_path, "w") as f:
        json.dump(global_manifest, f, indent=2)

    # ── Phase 5: Push to GitHub ──
    print("\n[5/5] Pushing to private repo...")

    # Check if we can push (repo exists, is git repo, has remote, gh authed)
    can_push = True
    if not BACKUP_REPO.exists():
        print("  [SKIP] Backup repo not cloned — backup saved locally only")
        print(f"         Clone it: gh repo clone Anesu/hermes-backups {BACKUP_REPO}")
        can_push = False
    elif not (BACKUP_REPO / ".git").exists():
        print("  [SKIP] Not a git repo — backup saved locally only")
        print(f"         Initialize: cd {BACKUP_REPO} && git init && git remote add origin git@github.com:Anesu/hermes-backups.git")
        can_push = False
    elif not check_gh_auth():
        print("  [WARN] gh CLI not authenticated. Backup saved locally, push skipped.")
        print("         To push later: gh auth login --scopes repo")
        can_push = False

    if can_push:
        os.chdir(BACKUP_REPO)

        # Verify repo is PRIVATE before pushing
        try:
            result = subprocess.run(
                ["gh", "repo", "view", "Anesu/hermes-backups", "--json", "isPrivate"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                repo_info = json.loads(result.stdout)
                if not repo_info.get("isPrivate"):
                    print("  [FATAL] Repo is NOT private! Aborting push.")
                    print("  Run: gh repo edit Anesu/hermes-backups --visibility private")
                    can_push = False
        except Exception as e:
            print(f"  [WARN] Could not verify repo privacy: {e}")

    if can_push:
        subprocess.run(["git", "add", "-A"], check=True)
        commit_msg = f"backup: {DEVICE} — {manifest['backup_id']}"
        result = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
        if result.returncode != 0 and "nothing to commit" not in (result.stderr or ""):
            print(f"  [WARN] Commit issue: {result.stderr}")

        result = subprocess.run(["git", "push"], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("  [OK] Pushed to Anesu/hermes-backups (PRIVATE)")
        else:
            print(f"  [WARN] Push failed (backup saved locally): {result.stderr[:200]}")
    else:
        print("  [INFO] Backup saved locally. Push skipped.")

    # ── Retention (local only if can't push) ──
    if BACKUP_REPO.exists():
        apply_retention(BACKUP_REPO, DEVICE)
        apply_global_retention(BACKUP_REPO)

    # ── Summary ──
    total_size = sum(a["size"] for a in assets.values())
    print("\n" + "═" * 50)
    print(f"BACKUP COMPLETE: {manifest['backup_id']}")
    print(f"  Assets:      {len(assets)} files")
    print(f"  Total size:  {total_size:,} bytes")
    print(f"  Skill sync:  {syncs['skill_sync']['status']}")
    print(f"  Identity:    {syncs['identity_sync']['status']}")
    print(f"  Security:    auth.json + .env NOT transported")
    print("═" * 50)


if __name__ == "__main__":
    main()
