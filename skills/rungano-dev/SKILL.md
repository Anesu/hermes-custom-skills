---
name: rungano-dev
description: Develop and debug the Rungano (Higgs-TTS) Electron desktop app. Use when working on the Higgs-TTS repo at ~/Documents/GitHub/Higgs-TTS.
---

# Rungano Development

Electron desktop app for Higgs Audio v3 TTS on RTX 3090 24GB. Shona-language voice synthesis with streaming SSE, voice cloning, and model parameter controls.

## Architecture

```
Electron (main.js) → Flask :7861 (server.py) → SGLang-Omni :8000 (WSL2) → Higgs Audio v3 4B
                                    ↑
                              renderer (app.js, index.html, styles.css)
```

### Key modules

| Module | Path | Role |
|--------|------|------|
| `server.py` | `server/server.py` | Flask routes, lazy singletons, shared helpers |
| `core.py` | `server/higgs/core.py` | HiggsTTS adapter, control tokens, build_input_text() |
| `voices.py` | `server/higgs/voices.py` | VoiceCatalog — voices/<lang>/<name>/ |
| `history.py` | `server/higgs/history.py` | HistoryStore — output/<YYYY-MM-DD>/ |
| `text.py` | `server/higgs/text.py` | TextChunker — spaCy sentence segmentation |
| `audio.py` | `server/higgs/audio.py` | apply_gain, trim_silence (abs-threshold), concat_wavs |
| `system.py` | `server/higgs/system.py` | gpu_info, wsl_path |
| `config.py` | `server/higgs/config.py` | HiggsConfig — frozen dataclass, preset_voices |
| `main.js` | `electron/main.js` | Window, tray, SGLang/Flask spawn, IPC, health polling |
| `preload.js` | `electron/preload.js` | Context bridge (window.higgs) |
| `app.js` | `renderer/app.js` | UI logic, SSE streaming consumer, state, keyboard shortcuts |
| `index.html` | `renderer/index.html` | DOM structure |
| `styles.css` | `renderer/styles.css` | Dark/light themes, 2-col grid, components |

### Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Flask + SGLang readiness, GPU info |
| GET | `/api/controls` | Control token catalogue |
| GET/POST/DELETE | `/api/voices/custom` | Voice CRUD with language field |
| POST | `/api/tts` | Single utterance synthesis |
| POST | `/api/tts/batch` | Batch synthesis (all-at-once, legacy) |
| POST | `/api/tts/batch/stream` | SSE streaming synthesis (progressive) |
| POST | `/api/export/wav` | Concatenate sentences into single WAV |
| GET/DELETE | `/api/history` | Synthesis history |

### Directory structure

```
Higgs-TTS/
├── voices/                    ← Input assets (parallel to output)
│   └── <language>/            ← Auto-detected from folder name
│       └── <voice-name>/      ← Sanitized, human-readable
│           ├── reference.wav  ← Consistent filename
│           └── meta.json
├── output/
│   └── <YYYY-MM-DD>/          ← Date-based, browseable
│       ├── <HHMMSS>-<id>.json
│       └── <HHMMSS>-<id>.wav
├── server/
├── electron/
├── renderer/
└── scripts/
```

## Critical Debugging Patterns

### Silent init() crash — ALL buttons unclickable

**Symptom:** Nothing is clickable — settings, theme, info, synthesis, audio controls all dead.

**Root cause:** A `$('...')` call in `app.js` returns `null` because the HTML element ID doesn't exist in `index.html`. This sets the corresponding `els.*` property to `null`. When `init()` reaches `els.theButton.addEventListener(...)`, it throws silently, killing ALL subsequent event listeners.

**Quick diagnosis:** Run this ID-matching script:

```python
import re
app_js = open('renderer/app.js').read()
html = open('renderer/index.html').read()
js_ids = set(re.findall(r"\$\('([^']+)'\)", app_js))
html_ids = set(re.findall(r'id="([^"]+)"', html))
missing = js_ids - html_ids
print(f"MISSING: {missing}" if missing else f"All {len(js_ids)} IDs match")
```

Every `$('id-name')` in app.js MUST have a matching `id="id-name"` in index.html. This is the #1 cause of post-refactor breakage. See `references/check-ids.py` for the verification script.

### Stale .pyc cache after server changes

After editing ANY `.py` file under `server/`, ALWAYS:

```bash
find server -name '__pycache__' -exec rm -rf {} +
find server -name '*.pyc' -delete
```

If behavior still doesn't change, nuclear-clear the venv cache too:

```bash
find server/.venv/lib -name '__pycache__' -exec rm -rf {} +
```

### Multiple stale Flask processes on port 7861

Multiple Flask instances accumulate on the same port. Kill ALL before restart:

```bash
for PID in $(netstat -ano | grep ':7861' | grep 'LISTENING' | awk '{print $NF}' | sort -u); do
  taskkill //PID $PID //F
done
```

### Tray.getMenu() crash (Electron v33+)

`tray.getMenu()` was removed in newer Electron. Store the menu at creation:

```javascript
let trayMenu = null;
// In createTray():
trayMenu = Menu.buildFromTemplate([...]);
tray.setContextMenu(trayMenu);
// In updateTrayStatus():
const f = trayMenu.getMenuItemById('status-flask');  // use trayMenu, not tray.getMenu()
```

## Launch Sequence

```bash
# 1. Kill stale processes
PID=$(netstat -ano | grep ':7861' | grep LISTENING | awk '{print $NF}' | head -1)
[ -n "$PID" ] && taskkill //PID $PID //F

# 2. Start Flask
server/.venv/Scripts/python server/server.py --port 7861 &

# 3. Verify
curl -s http://127.0.0.1:7861/api/health

# 4. Launch Electron (pre-starting Flask avoids 90s hidden-window delay)
npx electron .
```

## Architectural Conventions

- **Server owns prompt format**: renderer sends `{text, controls: {emotion, style, ...}}`, server calls `build_input_text()` per-utterance
- **SSE streaming**: `/api/tts/batch/stream` pushes per-sentence events, renderer consumes via ReadableStream
- **IPC for health/status**: main.js polls, pushes via `higgs:health` — renderer is pure consumer
- **Single trim algorithm**: `trim_silence()` uses absolute threshold (100), ratio-based version retired
- **Shared helpers**: `_apply_controls()`, `_resolve_references()`, `_make_output_path()` — deduplicated in server.py

## User Preferences

- **Aggressive clean-break refactors** — no backward compat shims, no deprecation
- **Minimal UI** — traffic-light status (red→yellow→green), technical details hidden behind ℹ tooltip
- **Voice display** — name only in dropdown, language as badge, no "custom" suffix
- **Word count** — not character count. Label says "words"
- **Human-readable labels** — prosody tokens mapped via `LABELS` object in `app.js`
- **Absolute history dates** — "12 Jun 14:30" not "27m ago"
- **Shona-first** — primary use case, default language in voice clone modal
- **VRAM safety** — >1GB free for clean synthesis, restart SGLang between long sessions

## Commit Workflow

```bash
git add -A
git commit -m "type: description"
# Prefixes: refactor:, feat:, fix:, polish:
```
