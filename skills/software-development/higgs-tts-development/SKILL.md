---
name: higgs-tts-development
description: Develop, debug, and extend the Rungano (Higgs-TTS) Electron + Flask desktop app. Use when modifying renderer, server, electron main, styles, or project structure.
---

# Higgs-TTS Development

Rungano is an Electron desktop shell for Higgs Audio v3 TTS on RTX 3090.
Stack: Electron → Flask :7861 → SGLang-Omni :8000 (WSL2) → Higgs Audio v3 4B.

## Project layout

```
Higgs-TTS/
├── voices/                    ← input assets (parallel to output/)
│   └── <language>/<name>/    ← auto-detected from directory
│       ├── reference.wav
│       └── meta.json
├── output/<YYYY-MM-DD>/      ← date-organized synthesis output
├── server/
│   ├── server.py             ← Flask routes (thin wiring)
│   ├── higgs/
│   │   ├── core.py           ← HiggsTTS adapter over SGLang
│   │   ├── audio.py          ← WAV post-processing
│   │   ├── voices.py         ← VoiceCatalog (filesystem scan)
│   │   ├── history.py        ← HistoryStore (date-based I/O)
│   │   ├── text.py           ← TextChunker (spaCy + regex)
│   │   ├── system.py         ← GPU info + WSL paths
│   │   └── config.py         ← Frozen HiggsConfig
│   └── .venv/                ← Python venv (flask, spacy, sglang)
├── electron/
│   ├── main.js               ← Electron main process
│   └── preload.js            ← IPC bridge
└── renderer/
    ├── index.html            ← UI shell
    ├── app.js                ← Orchestrator (~150 lines, imports + wires modules)
    ├── state.js              ← Shared state, DOM refs (els), LABELS, $() helper
    ├── api.js                ← HTTP fetch wrapper (all server calls through here)
    ├── toast.js              ← Transient notification helper
    ├── chips.js              ← Control-token chip UI (emotion/style/prosody/sfx)
    ├── health.js             ← IPC-driven traffic-light status + tooltip detail
    ├── voices.js             ← Voice dropdown, clone modal, upload flow
    ├── playlist.js           ← Sentence DOM rendering, download, click-to-play
    ├── synthesis.js          ← SSE streaming engine, progress, cancel
    ├── sessions.js           ← Recent-session cards, export, clear history
    ├── settings.js           ← Model settings modal (temperature, top-K, etc.)
    ├── theme.js              ← Light/dark toggle with localStorage persistence
    ├── dragdrop.js           ← .txt file drag-and-drop
    └── styles.css            ← Dark + light themes
```

## Development workflow

### Starting the app

```bash
# 1. Start Flask (must kill any existing on port 7861 first)
PID=$(netstat -ano | grep ':7861' | grep LISTENING | awk '{print $NF}' | head -1)
[ -n "$PID" ] && taskkill //PID $PID //F
rm -rf server/__pycache__ server/higgs/__pycache__
server/.venv/Scripts/python server/server.py --port 7861 &

# 2. Launch Electron
npx electron .
```

### The stale bytecode trap

Python compiles `.pyc` files into `__pycache__/`. When you change source files but the running Flask process loaded the old `.pyc`, the server keeps serving old code even after restart. **Every time you change server Python files, clear caches before restarting.**

```bash
find server -name '__pycache__' -exec rm -rf {} +
find server -name '*.pyc' -delete
rm -f output/.migrated-v2  # if re-running migration
```

### The null element crash pattern

When an `$('some-id')` call returns null because the ID doesn't exist in the HTML, and that reference is used in `init()` to attach event listeners, ALL listeners after that point silently fail. Symptoms: "buttons aren't clickable", "nothing works."

**After ANY HTML restructure, run `scripts/verify-ids.py` to check all IDs match.**

```python
import re
app_js = open('renderer/app.js').read()
html = open('renderer/index.html').read()
js_ids = set(re.findall(r"\$\(&#x27;([^&#x27;]+)&#x27;\)", app_js))
html_ids = set(re.findall(r'id="([^"]+)"', html))
missing = js_ids - html_ids
if missing: print(f"MISSING: {missing}")
else: print(f"All {len(js_ids)} IDs match")
```

### Renderer ES module verification

After changes to any renderer module, run these two checks:

**1. Syntax check (all 13 modules):**
```bash
cd renderer
for f in *.js; do node --check "$f" && echo "$f: OK"; done
```

**2. Import/export cross-reference:**
```bash
python scripts/verify-renderer-imports.py
```
This script parses every `import {X} from './Y.js'` statement and verifies `X` exists as an `export` in `Y.js`. Catches: importing a name that was renamed/deleted, importing from a nonexistent file, or typos in exported function names. No circular dependency detection needed — ES modules in this project form a DAG (orchestrator imports everything, feature modules import downward).

### Testing endpoints without the full stack

```bash
cd server && .venv/Scripts/python -c "
import sys; sys.path.insert(0, '.')
from server import app
with app.test_client() as c:
    r = c.get('/api/voices')
    print(r.status_code, len(r.json['voices']))
"
```

### Port conflict resolution

Multiple stale Flask processes accumulate because Electron spawns its own. **Always check for ALL processes on the port:** a single `taskkill` may leave stale listeners.

```bash
for PID in $(netstat -ano | grep ':7861' | grep LISTENING | awk '{print $NF}' | sort -u); do
  taskkill //PID $PID //F
done
```

### Electron tray.getMenu() deprecation

In Electron v33+, `tray.getMenu()` is removed. Store the Menu reference at creation time and reference it directly:

```javascript
let trayMenu = null;
// At creation:
trayMenu = Menu.buildFromTemplate([...]);
tray.setContextMenu(trayMenu);
// In update functions:
const f = trayMenu.getMenuItemById('status-flask');  // NOT tray.getMenu()
```

## Server endpoints (after refactor)

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Flask + SGLang readiness, GPU info |
| `GET /api/controls` | Control token catalogue (emotion/style/prosody/sfx) |
| `GET /api/voices` | All voices (presets + custom from `voices/<lang>/<name>/`) |
| `POST /api/voices/custom` | Upload voice clone (fields: name, language, audio, transcript) |
| `POST /api/tts` | Single-utterance synthesis |
| `POST /api/tts/batch` | Sentence-by-sentence synthesis (returns all at once) |
| `POST /api/tts/batch/stream` | Streaming SSE — sentences delivered progressively |
| `POST /api/export/wav` | Concatenate multiple entries into one WAV download (300ms gap) |
| `GET /api/history` | All synthesis entries across date directories |
| `GET /api/history/<id>` | Delete a specific entry |

## User UI preferences

- Traffic-light status (🔴→🟡→🟢) instead of "Flask: ready" / "Model: bosonai/..."
- Voice dropdown: name only, no "• custom" suffix. Language badge next to it.
- Word count, not character count ("187 words" not "1253 chars")
- Tech details (model name, VRAM, GPU) in ℹ tooltip, not status bar
- 3-column layout: Text input (left, flexible) | Playlist + Recent (center, flexible) | Effects chips (right, 320px fixed). Voice selector stays in text input footer, near Synthesise button. Settings summary at bottom of effects column.
- Actions toolbar with clear labels: "Export WAV" not "⬇ WAV"
- Synthesise button: just "Synthesise" not "Synthesise All"
- ⚙ Settings, ☀ Theme, and ⟳ Restart MUST stay visible in the status bar (user reversed a decision to hide them in the tooltip)
- Language badge (e.g. "SHONA") appears next to "Text to synthesise" label, updated when voice changes

## Voice directory structure

```
voices/<language>/<voice-name>/
├── reference.wav    ← ALWAYS this filename (not Zuva rangu.wav or audio/foo.wav)
└── meta.json        ← {"id", "name", "language", "transcript", "audio_filename": "reference.wav", "created_at"}
```

- Language is **inferred from the directory name** — dropping a voice into `voices/shona/` makes it Shona
- `VoiceCatalog.custom_voices()` walks `voices/<lang>/*/meta.json` and returns `{id, name, kind, language, audio_path, transcript}`
- The `voices/` directory is at `SERVER_DIR.parent / "voices"` — parallel to `output/`, NOT inside it
- On voice clone, use `_sanitize_name()` to strip special chars for the directory name

## Output directory structure

```
output/<YYYY-MM-DD>/<HHMMSS>-<entry_id>.{json,wav}
```

- `HistoryStore` walks date directories newest-first to list entries
- `HistoryStore.make_output_path(entry_id)` is the canonical source of truth for the path scheme
- `_make_output_path(entry_id)` in server.py delegates to `get_history().make_output_path(entry_id)` — no duplicated `time.strftime` patterns
- Audio file URLs in responses must use `out_path.relative_to(OUTPUT_DIR).as_posix()` — e.g. `/audio/2026-06-10/234449-abc.wav`
- **Never hardcode `/audio/history/`** — that path is dead since the date-based refactor

## The closest() null trap

When using `els.textInput.closest('.panel-input')` in `initDragDrop()`, if the DOM structure changes (or the element isn't ready), `closest()` returns null and crashes `init()`. **Always add null guards:**

```javascript
function initDragDrop() {
  if (!els.textInput) return;
  const panel = els.textInput.closest('.panel-input');
  if (!panel) return;
  // ... rest of handler
}
```

## After date-based storage: check file paths everywhere

When switching from flat `history/` to `output/<YYYY-MM-DD>/`:
- Server response `file` URLs → must use date-based paths
- `saveM3u()` → extract the relative path from `/audio/YYYY-MM-DD/...` instead of constructing `history/{id}`
- `exportAllWav()` → search all date dirs for `*-{id}.wav` instead of looking in a flat directory
- Migration → use `shutil.copy2` then `unlink` (not `shutil.move`) on Windows to avoid file-lock failures

## Design system — Minimal Depth

See `references/design-tokens.md` for the full color palette, shadow scale, animation keyframes, and component class reference.

CSS design language applied across the app:

- **Palette:** Darker base (`--bg-0: #0a0e14`), progressive layering (bg-1/2/3)
- **Radius:** `--radius-sm: 6px`, `--radius: 10px`, `--radius-lg: 14px`
- **Shadows:** `--shadow-sm/md/lg` with larger spreads in dark mode
- **Transitions:** All interactive elements use `--transition: 200ms ease`
- **Buttons:** Pill-shaped (`border-radius: 999px`), icon-first in action contexts
- **Hover:** Translates `-1px` to `-2px` with deeper shadow — tactile feel

### Animations (defined in keyframes)

| Animation | Trigger | Duration | Effect |
|---|---|---|---|
| `pulse-glow` | Ready status dot | 2s loop | Green box-shadow pulses |
| `slide-in` | New sentence appears | 300ms | Translates from +12px right, fades in |
| `fade-up` | Modals, toasts, session cards | 150-300ms | Translates from +6px below, fades in |
| `spin` | Progress spinner | 800ms loop | Rotate 360° |

### Floating action bubble

Pill-shaped icon-only toolbar that appears only when sentences exist:

```html
<div class="action-bubble" id="action-bubble" hidden>
  <button title="Open in VLC">▶</button>
  <button title="Export WAV">⬇</button>
  <button title="Save .m3u">📋</button>
  <button title="Open folder">📁</button>
</div>
```

CSS: `display: flex; gap: 2px; padding: 4px 6px; border-radius: 999px; box-shadow`. Hover lifts with deeper shadow. Toggle visibility in `renderSentenceList()` via `els.actionBubble.hidden`.

### Session cards (Recent section)

Each card represents one synthesis session (not individual sentences). Built from `GET /api/history/sessions`:

```javascript
async function loadRecentSessions() {
  const { sessions } = await api('/api/history/sessions');
  for (const s of sessions.slice(0, 8)) {
    // card.className = 'session-card'
    // text: s.first_text.slice(0, 80)
    // meta: date · sentence_count · duration
    // Hover-reveal actions: ▶ ⬇ 📁
    // Click card: exportSessionWav(s) → downloads rungano-{date}.wav
  }
}
```

Session cards have `animation: fade-up 0.3s ease` on first render, hover lift 2px, and `.session-actions` that go from `opacity: 0` to `opacity: 1` on hover.

### Server: Sessions endpoint

`GET /api/history/sessions` returns entries grouped by synthesis session (date folder + 4-char time prefix from `HHMMSS` filename). Each entry in one `Synthesise` click shares the same `HHMM` prefix.

```python
# HistoryStore.list_sessions() groups by key = f"{date_str}/{prefix}"
# Returns [{date, prefix, first_text, sentence_count, total_elapsed_sec, created_at, ids: [...]}]
```

## VLC / system player playback (no embedded audio)

The embedded HTML5 `<audio>` player was removed entirely — it caused flickering play/pause cycles and broken `.m3u` paths. All playback is now external through the system's default player.

- **Click a sentence** → `openInVlc(s)` resolves the absolute file path from the output directory and calls `window.higgs.openFile(path)`
- **"Play All in VLC"** → `playAllInVlc()` calls `saveM3u(true)` which generates the `.m3u` and opens it via `shell.openPath()`
- **IPC: `higgs:open-file`** — added to `main.js` as `shell.openPath(filePath)` and exposed in `preload.js` as `openFile(path)`
- **`saveM3u(openAfter)`** — accepts boolean; when `true`, opens the .m3u after saving; when `false`, just downloads and toasts

When removing audio player:
- Remove `audioPlayer`, `audioWrap`, `audioPlaceholder` from HTML
- Remove those refs from `els` object in app.js
- Remove `ended` / `error` event listeners from `init()`
- Remove `_enterSynthesisingState` audio hide/show logic
- Remove auto-play-first-sentence block from streaming handler
- Strip Space/Arrow key keyboard shortcuts (keep only Esc for cancel)
- Update shortcuts hint in HTML

## GitHub push via `gh` CLI

If `gh` is not installed on Windows:
```bash
curl -sL https://github.com/cli/cli/releases/download/v2.65.0/gh_2.65.0_windows_amd64.zip -o /tmp/gh.zip
unzip -o /tmp/gh.zip -d /tmp/gh
/tmp/gh/bin/gh.exe auth login --hostname github.com --web
# User opens URL and enters device code
/tmp/gh/bin/gh.exe repo create <name> --public --source=. --remote=origin --push
```

## Cache must be cleared while server is DEAD

**Critical:** `__pycache__` regenerates instantly when the server process is running. If you clear cache while Flask is alive, the next request re-creates the `.pyc` from the already-loaded (stale) bytecode. The only reliable sequence:

1. Kill ALL Flask processes on the port
2. Clear cache
3. Start fresh Flask

Never clear cache with the server running — it's a no-op.
