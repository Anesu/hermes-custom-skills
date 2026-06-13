---
name: desktop-app-shell-windows
description: Wrap a Python (or other local) backend in a real Windows desktop application — Electron shell, system tray, native window chrome, desktop + Start Menu shortcuts, single-instance lock, hidden console. Use when the user wants a "real desktop app" feel for a local tool (TTS, image gen, LLM, etc.) on Windows, especially with an existing Python backend that already runs in a venv. Triggers on phrases like "make this a desktop app", "give it an icon", "package as exe", "looks like a regular application", "one-click launcher", "wrap it in Electron", "stop opening a browser", "system tray".
---

# Desktop App Shell for Windows

The class of work: **you have a Python/Node/local backend that already runs in a venv or via CLI, and you want it to feel like a real Windows desktop application** — with an icon, a native window (not a browser tab), a system tray, and double-click-to-launch from the Desktop or Start Menu.

This is not "build an Electron app from scratch." This is **wrapping an existing backend** in the minimum viable Electron shell. The shape of the work is well-defined; the hard parts are the Windows-specific subprocess + shortcut + icon plumbing.

## When to use

- User has a working local backend (TTS, image gen, LLM, transcription, etc.) and wants a desktop UI.
- User says "it should look like a regular app" / "I want an icon" / "double-click to launch" / "stop opening a browser tab."
- The backend exposes an HTTP API or can be wrapped in one.
- The user is on Windows. (macOS/Linux need different launch paths; covered briefly at the end.)

## When NOT to use

- The backend is already a GUI app (tkinter, Qt, etc.) — just give it an icon.
- The user wants a SaaS / multi-user product — different problem.
- The backend is on a remote server — use a web app or Tauri instead.
- Quick prototype / one-shot use — just use `webview` or a browser tab.

## Architecture (the shape that works)

```
┌─────────────────────────────────────────────────────────────┐
│  Electron Desktop App                                        │
│  ┌──────────────────┐    IPC    ┌────────────────────────┐  │
│  │  Renderer (UI)   │◄────────►│  Main process          │  │
│  │  HTML/CSS/JS     │          │  - BrowserWindow       │  │
│  │  (no framework)  │          │  - Tray                │  │
│  │                  │          │  - Subprocess spawn    │  │
│  └────────┬─────────┘          │  - Health poll         │  │
│           │ fetch              │  - Single-instance     │  │
│           ▼                   └──────┬──────────┬──────┘  │
└──────────────────────────────────────│──────────│─────────┘
                                       │          │
                       ┌───────────────┘          └──────────────┐
                       ▼                                        ▼
            ┌──────────────────────┐                ┌──────────────────────┐
            │  Python backend      │                │  Model server (WSL2) │
            │  Flask/FastAPI proxy │  OpenAI-compat │  SGLang-Omni / vLLM  │
            │  :7861               │ ─────────────► │  :8000               │
            │  - friendly /api/*   │                │  - /v1/audio/speech  │
            │  - voice catalog     │                │  - GPU inference     │
            │  - history           │                │                      │
            └──────────────────────┘                └──────────────────────┘
```

**The 3-process model** is the right answer for any backend that has its own HTTP server:

1. **Electron main** — window, tray, IPC, orchestration
2. **Python proxy** — friendly `/api/*` surface, hides raw backend calls
3. **Backend** (model server) — does the actual work

The Python proxy earns its keep by giving you a stable API to evolve (history, voice management, validation) without touching the renderer or the backend. Skipping it and going renderer → backend directly is tempting but you pay for it later when you need to add features.

If your backend **doesn't have an HTTP server** (e.g. it's a CLI tool), wrap it in a tiny Flask/FastAPI shim first. Don't make the renderer call the CLI directly.

## The 8 components, in build order

1. **Project scaffold.** Folder layout:
   ```
   app/
   ├── electron/                # main + preload
   │   ├── main.js
   │   ├── preload.js
   │   └── assets/icon.ico     # multi-resolution
   ├── renderer/                # HTML/CSS/JS UI (no framework)
   ├── server/                  # Python backend / proxy
   │   ├── server.py
   │   ├── appname/             # deep modules
   │   ├── requirements.txt
   │   └── .venv/              # created on install
   ├── scripts/
   │   ├── launch.bat
   │   ├── launch.vbs           # silent wrapper
   │   ├── start-backend.bat    # backend launcher
   │   ├── install.bat          # Windows install
   │   ├── install-in-wsl.sh    # WSL install (if backend needs Linux)
   │   └── create-shortcut.ps1
   ├── output/                  # generated artifacts
   ├── package.json
   ├── README.md
   └── LICENSE.md
   ```

2. **Branded icon (`.ico`, multi-resolution).** Generate with Pillow (see `templates/generate-icon.py` for a working template). Must contain 16, 32, 48, 64, 128, 256 px sizes in one file. **Pitfall:** Pillow's `im.save(format="ICO", sizes=[...], append_images=[...])` silently collapses to one size — use `sizes=` alone with the largest image, OR write each size to disk and combine with a real ICO writer. Tray icon: separate 32x32 transparent PNG.

3. **Electron main + preload.** Patterns:
   - `contextIsolation: true`, `nodeIntegration: false`, expose only a whitelisted `window.appname` API via `preload.js`.
   - Spawn backend with `shell: true` (REQUIRED for `.bat` on Windows — see `windows-shell-handling` §8.1).
   - Poll backend health from main; emit to renderer via IPC; show window only when healthy.
   - Single-instance lock via `app.requestSingleInstanceLock()`.
   - Close → hide to tray (don't quit) so the app feels "always running."
   - On first launch, create Desktop + Start Menu `.lnk` shortcuts via PowerShell. **Pitfall:** `process.execPath` is `node.exe` in dev — point the shortcut at `wscript.exe + your .vbs` instead.

4. **Python proxy.** Flask or FastAPI. Endpoints follow the pattern:
   - `GET /api/health` — readiness check (the renderer polls this)
   - `GET /api/<resource>` and `POST /api/<resource>` — friendly surface
   - `POST /v1/<openai-compat-path>` — pass-through to the actual backend (lets curl users hit your app with the standard recipes)
   - `GET /audio/<path>` and similar — static file serving with **path-traversal protection** (`if not str(resolved).startswith(str(OUTPUT_DIR.resolve())): return 403`)

5. **Backend launcher (`.bat`).** Wraps the actual start command. Kills any existing instance on the port (`lsof -ti :PORT | xargs kill` in WSL, or `netstat -ano | findstr :PORT` + `taskkill /PID` in pure Windows). Logs to a file so failures are diagnosable.

6. **Silent `.vbs` wrapper.** `wscript.exe` + your `.vbs` runs the `.bat` with `WindowStyle = 0` (hidden). Use this as the shortcut target, NOT the `.bat` directly, to avoid the console flash.

7. **Install script (`install.bat` + WSL companion if needed).** One command does it all:
   - Verify Python and Node
   - `npm install` for Electron
   - Create venv, `pip install -r requirements.txt`
   - If backend needs Linux (SGLang-Omni, vLLM, anything CUDA-heavy): `wsl bash install-in-wsl.sh` — installs CUDA toolkit, the serving framework, downloads model
   - Be **explicit about the time and disk cost** in the prompt ("This will take 15-30 minutes and download ~8 GB. Continue? [y/N]")

8. **Shortcuts via PowerShell.** Real `.lnk` files with `IconLocation` set. Use `WScript.Shell.CreateShortcut()` from a `.ps1` script. **Pitfalls:** don't pass `process.execPath` as the target (see §8.2 of `windows-shell-handling`); don't use `Join-Path` on already-absolute paths; avoid em-dashes and other non-ASCII (cp1252 corruption, see §8.3).

## Verifying the build (in order)

After every component, run the next check. Don't move on until the current one passes.

### Reporting progress: never return empty after tool calls

During long-running verification steps — especially the WSL install phase — you will poll background processes repeatedly. **Every poll result must be reported to the user.** The agent's rule: if you called a tool and got output, process it and tell the user what happened. A response consisting only of whitespace or bare `(empty)` after tool calls signals to the user that you're not paying attention. This is a user-facing quality rule, not a technical constraint.

**Right pattern after polling a long-running install:**
```
SGLang core installed. Now building SGLang-Omni from source — 37% CPU, 280MB RAM. Log shows 187 packages resolved so far. Still running.
```

**Wrong pattern (the one the user called out):**
```
(empty response after tool calls)
```

This applies to ALL tool-output processing — health checks, endpoint smoke tests, icon verification, shortcut creation — not just long-running installs. If there's output, summarise it.

1. `python -c "import ast; ast.parse(open('file.py').read())"` — Python syntax
2. `node -c file.js` — JS syntax
3. `python -c "import json; json.load(open('package.json'))"` — JSON validity
4. Start the Python server, curl `/api/health`, `/api/<resource>`, error path, path-traversal block
5. Generate the icon, verify all sizes are present (`PIL.Image.open(ico).ico.sizes()`)
6. Stub Electron with a fake `electron` module, `require('./main.js')`, watch for `EINVAL` on subprocess spawn
7. Run `create-shortcut.ps1` directly, verify `.lnk` files exist on Desktop + Start Menu with the right icon and target

## Common mistakes

- **Forgetting `shell: true` for `.bat` spawn** — `EINVAL` at runtime. See `windows-shell-handling` §8.1.
- **Mutating a frozen dataclass in CLI overrides** — `FrozenInstanceError`. Pass CLI values through env vars instead.
- **PowerShell `.ps1` with em-dashes / smart quotes** — silently mangled by cp1252. See `windows-shell-handling` §8.3.
- **CSS `display: flex` on elements toggled with `hidden` attribute** — `display: flex` wins over the UA `[hidden] { display: none }`. The element stays visible. Fix: add `.modal[hidden] { display: none !important; }` and set both `hidden` + `style.display` in JS. See `references/css-hidden-vs-display.md` for the full diagnosis.
- **`tray.getMenu()` removed in Electron v33+** — calling `tray.getMenu()` throws `TypeError: tray.getMenu is not a function`. The fix: store the context menu as a module-level variable during `createTray()` (`let trayMenu = Menu.buildFromTemplate(...); tray.setContextMenu(trayMenu)`), then reference `trayMenu.getMenuItemById(...)` directly in `updateTrayStatus()` instead of going through `tray.getMenu()`.

- **Stale `__pycache__` after Python refactors** — after restructuring server modules (extracting new files, moving functions between files), the Flask server may return 500 on new endpoints even though the Flask test client passes. Cause: stale `.pyc` bytecode files imported by Electron's spawned subprocess, which picks up an older cached version. Fix: `rm -rf server/__pycache__ server/*/__pycache__` before launching. This is especially relevant when you've added new modules or changed the import graph — the test client imports fresh from disk, but the cached subprocess doesn't.

- **Using Electron IPC for health/status data** — there is a race condition: if `pollHealth()` fires before the renderer finishes loading its scripts, the first `higgs:health` IPC message is silently dropped and the status bar shows "Connecting…" until the next poll. IPC health CAN work if: (a) your backend starts slower than your renderer loads (Flask + spaCy takes ~3s, window loads in ~1s — renderer wins the race), AND (b) you poll frequently enough (≤10s) that a dropped first message doesn't leave the UI stale for long. If either condition fails, use direct HTTP `fetch()` to Flask `/api/health` as the primary channel. In either case, IPC is correct for user-initiated actions (restart, open folder) and one-shot alerts (startup-failed).
- **Path traversal in `/audio/<filename>`** — always resolve the requested path and check it's still under the output dir.
- **Multiple orphan Flask processes** — after kills/restarts, `netstat -ano | findstr :PORT` may show multiple PIDs listening on the same port. Kill all of them explicitly: `taskkill /PID <n> /F` for each, then verify the port is clean before restarting. Starting Flask on a port that already has a listener silently binds to the old process.
- **VRAM monitoring via nvidia-smi** — add a `gpu` block to `/api/health` that calls `nvidia-smi --query-gpu=name,memory.used,memory.total,memory.free` via `subprocess.check_output`. Use the absolute path `os.path.join(os.environ.get("SystemRoot", r"C:\\Windows"), "System32", "nvidia-smi.exe")` — on MSYS/git-bash hosts, `subprocess` may not find `nvidia-smi` on PATH without it. Parse the CSV output (format: `name, used_MB, total_MB, free_MB`) and emit `{\"gpu\": {\"name\": \"...\", \"vram_used_mb\": N, \"vram_total_mb\": N, \"vram_free_mb\": N}}`. Show the free VRAM in the status bar so the user can see pressure before OOM.
- **Pillow ICO with `sizes=` + `append_images=`** — collapses to one size. Use `sizes=` alone with the largest image, downsampling handled by Pillow.
- **Pinning the shortcut to `process.execPath`** — wrong binary in dev. Use `wscript.exe + .vbs` shim.
- **Skipping the Python proxy** — you'll want it later for history, validation, voice management. Bake it in from day one.
- **Opening a browser instead of using Electron's BrowserWindow** — defeats the whole purpose. If you wanted a browser, you'd not be doing this.
- **`detached: true` on Windows subprocesses** — the kill signal won't propagate through `wsl.exe` into WSL to terminate the actual model server. Remove `detached: true` entirely (the default kills children on parent exit), and add an explicit `execSync('wsl -d Ubuntu -- bash -c "pkill -f sgl-omni"')` in `before-quit` to reach WSL-side processes.
- **Restart button bails out instead of killing** — `if (sglangProcess) return` blocks the restart. The correct pattern: kill the old process (even if you have to force-kill), null the reference, THEN spawn the new one. The restart button must be a hard cycle, not a no-op when the old process is still alive.
- **WSL-internal paths in Windows `.bat`** — if your venv lives inside WSL (`~/.higgs-sglang-venv`), reference it as `~/.higgs-sglang-venv` in WSL commands, NOT as `%USERPROFILE%\.higgs-sglang-venv`. Windows paths resolve to `C:\Users\...` which doesn't exist inside WSL. The `.bat` should only contain `wsl -d Ubuntu -- bash -c "source ~/.venv/bin/activate && ..."` — no Windows path translation needed.

## Companion skills to load

- `windows-shell-handling` — required for the subprocess, encoding, and shortcut pitfalls.
- `local-ai-model-integration` — if your backend wraps an AI model (TTS, LLM, image gen), load this for the API contract locking, control token injection, and voice clone reference handling.
- `impeccable` — for the UI design (dark theme, chip controls, status pills).
- `write-a-skill` — if you're also creating a per-project skill for your app.

## Reference files in this skill

- `references/architecture-decisions.md` — when to skip the 3-process model, when to add a 4th (e.g. nginx for static), when Electron is overkill.
- `references/icon-generation-template.md` — Pillow-based icon generator, multi-resolution, with a brand color palette.
- `references/shortcut-and-tray-pitfalls.md` — the full transcript of shortcut creation bugs and how to diagnose them.
- `references/css-hidden-vs-display.md` — the CSS `display: flex` overriding `[hidden]` attribute bug: reproduction, diagnosis, two fixes.
- `references/wsl-install-pitfalls.md` — WSL2-specific install failures: stale HF locks, pipefail SIGPIPE, `sglang[all]` resolver hell, dual-download WSL crashes, recovery sequences.
- `templates/electron-main.js.template` — the orchestrator pattern (window, tray, subprocess, health poll, single-instance lock, IPC).
- `templates/python-proxy.py.template` — Flask proxy with friendly `/api/*` + OpenAI-compat passthrough + path-traversal-safe static serving.
- `templates/install.bat.template` — one-shot Windows install with venv bootstrap, npm install, optional WSL delegation.
- `templates/install-in-wsl.sh.template` — CUDA toolkit check, `uv` bootstrap, source install of the serving framework, model download.
- `scripts/verify-desktop-app.sh` — the verification checklist as a runnable script (syntax checks + endpoint smoke + shortcut creation).
