---
name: local-ai-desktop-app
description: Build, debug, and maintain local-first AI desktop applications (Electron + Python + local model server). Use when the user asks to build a desktop app around a local AI model, or when debugging silent/hanging/corrupted output from a local model server. Covers the Koko / Koko-Omni / Higgs-TTS pattern.
---

# Local AI Desktop Application Pattern

## Architecture (Koko family pattern)

```
Electron shell (main.js + preload.js + renderer/)
  ├─ IPC → window mgmt, tray, subprocess orchestration
  └─ fetch → Python Flask proxy :7861 → local model server :8000
```

The Flask proxy is the single seam — renderer never talks to the model server directly. This gives you a place to add features (history, voice management, audio post-processing) without touching the renderer.

## Subprocess orchestration (Windows-specific)

- **`.bat` spawn requires `shell: true`** — otherwise `EINVAL` on Windows.
- **Never `detached: true`** — creates orphan processes that survive Electron exit.
- **Kill WSL-side processes manually** in `before-quit`: `wsl -d Ubuntu -- bash -c "pkill -f <process-name>"`.
- **Restart must kill old process before spawning new one** — `if (process) { try { process.kill(); } catch {} process = null; }`.

## Stale process accumulation (the #1 debugging trap)

Multiple Flask/SGLang instances accumulate on ports, serving old code. Symptoms:
- Code changes don't take effect
- 500 errors on endpoints that work standalone
- Multiple PIDs on the same port

**Fix:** `netstat -ano | grep :<port> | grep LISTENING` → kill ALL PIDs before restarting.

## Stale `.pyc` bytecode (the #3 debugging trap)

Even after killing stale processes, new Flask instances may serve old code if `.pyc` files persist. Symptoms:
- New endpoints return 404 despite being in the source file
- Flask test client (`app.test_client()`) works but HTTP requests fail
- Route listing (`app.url_map`) shows the route, but live server doesn't

**Fix:** Clear ALL `__pycache__` directories and `.pyc` files before restarting:
```bash
find server/ -name '__pycache__' -type d -exec rm -rf {} +
find server/ -name '*.pyc' -delete
```

## VRAM exhaustion (the #2 debugging trap)

Local model servers (SGLang-Omni, vLLM) accumulate VRAM across synthesis runs. Symptoms:
- Tiny output files (KB instead of MB)
- Near-empty WAVs from TTS models
- Server still reports "healthy" but returns garbage

**Fix:** Restart the model server between long sessions. Monitor with: `nvidia-smi --query-gpu=memory.free --format=csv,noheader`.

## Diagnostic heuristics for TTS failures

| Symptom | Likely cause | Action |
|---|---|---|
| Tiny output (KB, not MB) | VRAM exhaustion | Restart model server |
| 500 on new endpoints, standalone test works | Stale Flask processes | Kill all, restart one |
| First 20s of speech then silence | Token budget too low / no EOS token | Chunk text; use max token budget |
| Silent chunks in concatenated output | trim_silence eating quiet voice-cloned audio | Disable trimming for long-form; use gaps instead |
| "Connecting…" stuck in UI | IPC preload not available (browser dev mode) | Fall back to direct HTTP fetch polling |
| Model not ready after restart | start script uses wrong path (Windows vs WSL) | Use `~/.venv-path` inside WSL, not `%USERPROFILE%\.venv-path` |

## Renderer health monitoring

**Primary channel: Electron IPC push events.** The main process polls Flask + SGLang every 10s and pushes results via `webContents.send('higgs:health', { flask, sglang, flaskBody })`. The renderer subscribes via the preload bridge (`window.higgs.onHealth(callback)`) and is a pure consumer — no duplicate HTTP polling.

```javascript
// main.js — single health source
setInterval(() => pollHealth(), 10_000);

// preload.js — bridge
onHealth: (callback) => {
  ipcRenderer.on('higgs:health', (_e, payload) => callback(payload));
}

// renderer — pure consumer
window.higgs.onHealth(({ flask, sglang, flaskBody }) => {
  updateHealthUI(flask, sglang, flaskBody);
});
```

**Fallback for dev/browser mode (no preload):** use direct HTTP `fetch()` polling. In Electron with a preload, IPC is the canonical path.

**Never run BOTH** IPC listeners and HTTP polling simultaneously — the renderer will process duplicate health events and double-fire side effects (e.g. re-initializing the chip catalogue twice).

## UI gotchas

- **CSS `display: flex` overrides browser's native `[hidden] { display: none }`.** Add explicit `[hidden] { display: none !important }` rule for modals.
- **PowerShell `.ps1` scripts**: avoid em-dashes and non-ASCII characters — they corrupt on Windows codepage.
- **Shortcut creation**: point at `.vbs` wrapper (runs `.bat` silently), not `process.execPath` (which is node.exe in dev).
- **Electron `tray.getMenu()` removed in v33+**: store the context menu reference at creation time (`trayMenu = Menu.buildFromTemplate(...)`) and use it directly instead of calling `tray.getMenu()`. Calling the removed method throws `TypeError: tray.getMenu is not a function` with no stack trace.
- **CSP blocks audio from Flask**: Electron `loadFile()` loads the renderer from `file:///`. The Content-Security-Policy must include `http://127.0.0.1:<port>` in BOTH `media-src` (for `<audio>` playback) and `connect-src` (for `fetch()`). Without `media-src`, audio loads silently fail.
- **Relative audio URLs resolve against `file:///`**: always prepend the Flask base URL. `audio.src = state.flaskUrl + '/audio/history/abc.wav'` — NOT `audio.src = '/audio/history/abc.wav'`.
- **Non-English text triggers spellcheck noise**: for TTS apps supporting Shona or other non-English languages, set `spellcheck="false"` on the `<textarea>`. Red underlines under every word make the UI look broken.
- **Human label mapping for chip controls**: internal token names like `speed_very_slow`, `pitch_high`, `expressive_high` look like debug output in the UI. Map them to human-readable labels with a lookup object: `{ speed_very_slow: 'Very slow', pitch_high: 'High pitch', expressive_high: 'Dramatic' }`. Apply the mapping in `buildChipRow()` when normalizing items — never mutate the source data, just override the `label` field on the normalized copy. The mapping lives in the renderer, not the server, because it is a presentation concern.

## Theme toggle (light/dark mode)

See `references/theme-toggle.md` for the full CSS and JS implementation.

**Summary:** Define both themes as CSS custom properties on `[data-theme="dark"]` and `[data-theme="light"]` selectors. Toggle by setting `document.documentElement.dataset.theme`. Persist to `localStorage`. Detect system preference via `window.matchMedia('(prefers-color-scheme: dark)')` on first launch. The toggle button shows a sun (☀) in light mode and a moon (🌙) in dark mode. Every CSS rule uses variables — the toggle is just swapping which variables are active.

## Voice directory organization (language auto-detection)

Voices live at `voices/<language>/<voice-name>/` — parallel to `output/`, NOT inside it. The folder name IS the language: `voices/shona/anesu/` → language = "shona". No configuration needed. Each voice directory contains `reference.wav` (consistent filename) and `meta.json`. See `references/voice-directory-structure.md` for the full VoiceCatalog implementation and migration from the old `output/voices/custom/<uuid>/` structure.

## Output directory organization (date-based)

Synthesis output is organized by date: `output/<YYYY-MM-DD>/<HHMMSS>-<id>.{json,wav}`. The HistoryStore walks date directories for list/delete operations. A `_make_output_path(entry_id)` helper in the server mirrors the naming convention. Migration from flat `history/` uses `shutil.copy2` + `f.unlink()` (not `shutil.move` on Windows — file locks cause silent failures). See `references/output-date-structure.md` for full implementation including export endpoint, audio serving, and output folder button behavior.

## Renderer polish patterns

**Word count, not character count**: For TTS, word count is the meaningful metric. `text.split(/\s+/).filter(Boolean).length`. Label it "words" not "chars". Apply to both the live counter and drag-drop toast messages.

**Export WAV**: `POST /api/export/wav` takes `{ids: [...]}`, searches all date directories, concatenates via `concat_wavs(crossfade_ms=0, gap_ms=300)`, returns single WAV. Client downloads as `rungano-YYYY-MM-DD.wav`.

**Save .m3u playlist**: Client-side generator. Uses absolute file paths from IPC `outputDir` so VLC can play directly. `#EXTINF` metadata with sentence text and duration. Downloads as `rungano-playlist.m3u`.

**Drag-and-drop .txt files**: Add `dragover`/`dragleave`/`drop` listeners on the textarea's parent panel. Show visual highlight with a CSS class. Only accept `.txt` files. Read with `file.text()`, populate textarea, update word count.

**Info tooltip panel**: Hide keyboard shortcuts and tips behind an ℹ icon in the status bar. Fixed-position panel, dismissed by clicking outside. Use `e.stopPropagation()` on the button click to prevent immediate dismissal.

**Export/save buttons**: Show ⬇ WAV and 📋 .m3u buttons in the playlist toolbar only when there are done sentences. Toggle visibility in `renderSentenceList()` alongside the Play All button.

**Info tooltip panel (ℹ)**: Replace visible keyboard-shortcut footer text with a compact ℹ icon in the status bar. The tooltip is a fixed-position `<div>` that appears below the status bar on click and dismisses when clicking anywhere outside it. Use `e.stopPropagation()` on the button click to prevent the document-level dismissal handler from immediately closing it. The tooltip shows keyboard shortcuts in `<kbd>` tags and contextual tips. This keeps the UI clean while still surfacing discoverability for power users.

**Default voice in settings**: Add a "Default Voice" dropdown to the model settings modal. Populate it dynamically from `state.voices` when the modal opens. On save, persist the selected voice ID to `localStorage` (`rungano-default-voice`). In `loadVoices()`, after populating the dropdown, check for a saved preference and override `state.selectedVoice` if the saved voice still exists in the list. "Last used" (empty value) means no override — the last manually selected voice persists for the session.

**History absolute dates**: Show "10 Jun 14:30" not "27m ago". Absolute dates are permanent; relative times change every refresh.

## VRAM gauge in status bar

Replace verbose "Model: bosonai/higgs-audio-v3-tts-4b (0.5GB free)" with a compact model name + color-coded bar.

**Implementation:** Extract model name with `.split('/').pop()`. Parse `gpu.vram_free_mb` and `gpu.vram_total_mb` from the health endpoint. Compute percentage: `(free / total) * 100`. Color the bar: green when >2GB free, yellow when 1-2GB, red when <1GB. Update from IPC health events every 10s. The bar is a `<div>` with `width: <pct>%` inside a container `<div>`. Transition the width and color with CSS `transition` for smooth animation. Show the free GB as a text label next to the bar. Hide the gauge when SGLang is not ready.

## Model settings modal

For TTS/LLM apps, expose model parameters as adjustable sliders behind a settings (⚙) button in the status bar.

**Defaults:** temperature=0.8, top_k=50, top_p=0.9, max_tokens=2048. Use `<input type="range">` with `min`/`max`/`step` attributes appropriate to each parameter. Display the current value with `input.addEventListener('input', ...)`. "Reset defaults" button restores all sliders. On save, write to `state.temperature` etc. The synthesis function reads from state and includes them in the API request body: `{ text, voice_id, temperature: state.temperature, top_k: state.topK, top_p: state.topP, max_new_tokens: state.maxTokens }`. The server endpoint must accept and pass through all four parameters to the model.

**Pitfall:** if you add `top_p` as a new parameter, you must update the server route handler, the TTS adapter (`HiggsTTS.synthesize()`), and the streaming batch endpoint — all three need the new field. Missing one produces silent defaults.

## WSL2 path translation

Model servers inside WSL2 cannot read native Windows paths. Convert:
```python
def _wsl_path(windows_path: str) -> str:
    p = windows_path.replace('\\', '/')
    m = re.match(r'^([A-Za-z]):/', p)
    if m:
        p = f'/mnt/{m.group(1).lower()}/{p[3:]}'
    return p
```

## Higgs TTS specific

See `references/higgs-tts-config.md` for the model's hard 4,096-token buffer limit, chunking strategy, silence handling, and SGLang-Omni install notes.

See `references/sse-streaming-tts.md` for the Server-Sent Events progressive synthesis pattern (replaces synchronous batch with per-sentence streaming).

## UI layout patterns

**Default: 2-column layout.** `grid-template-columns: 1fr 380px` — Input | Voice + Effects + Playlist. The voice card sits at the top of the right column as the most prominent element. Effects are collapsible `<details>` groups. The Synthesise button lives in the input panel footer (not a separate bottom bar). This gives the text area maximum room and keeps the control surface in one scrollable column.

**Three-column variant (wide windows only):** `grid-template-columns: 1fr 300px 360px` — Input | Controls | Output. Only activate at >1280px via `@media`. The Controls column hosts voice card, always-visible chip sections, and a settings summary. The 3-column layout fights for space at typical window sizes and the controls column becomes a wall of chips — prefer 2-column as the default.

**Voice card as hero:** The voice selector should be a prominent card (not just a dropdown) showing: voice name, kind badge (preset/custom), language badge (Shona/English), and a transcript preview. This is the most important setting — make it visually dominant. Use `border-color: var(--accent)` to draw attention.

**VRAM gauge:** Replace verbose "Model: bosonai/higgs-audio-v3-tts-4b (0.5GB free)" with a compact model name + color-coded bar. Green (>2GB free), yellow (1–2GB), red (<1GB). Update from IPC health events.
