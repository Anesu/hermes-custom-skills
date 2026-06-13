---
name: local-tts-serving
description: Serve TTS models (Higgs Audio v3, Kokoro, etc.) on a local GPU via SGLang-Omni or similar inference servers. Covers chunking, VRAM management, WSL path translation, and common pitfalls.
---

# Local TTS Serving

Serve text-to-speech models on a local GPU with a Flask proxy + frontend shell.

## Trigger conditions
- User asks to self-host a TTS model (Higgs, Kokoro, etc.)
- Synthesis produces silence, truncation, or corrupted audio
- SGLang-Omni / vLLM / local inference server VRAM issues
- Long text needs chunking strategies for token-budget-limited models

## Higgs Audio v3 — Known Constraints

**Hard buffer limit:** 4,096 tokens. The model has **no EOS token** — it generates until the token budget is exhausted, then produces silence/padding.

**Token rate:** 50 audio tokens per second (24 kHz ÷ 480 downsampling factor). `max_new_tokens=4096` = max 81.92 seconds of audio.

**VRAM:** ~22 GB on an RTX 3090 24GB. After several synthesis runs VRAM leaks; restart SGLang-Omni between long sessions.

See `references/higgs-v3-constraints.md` for full technical detail including chunk-sizing formulas and error patterns.

## Chunking Strategy for Long Text

When text exceeds the model's single-pass token budget, split into sentences and synthesise each separately, then concatenate.

### Defaults (battle-tested on 1,253-char Shona story):
| Setting | Value | Rationale |
|---|---|---|
| Chunk size | 150–200 chars | ~12–16s speech, well under 4,096-token limit |
| Token budget | Smart: `min(4096, max(768, int(len(chars)/8*50*2.0)))` | ~8 chars/sec × 50 tokens/sec × 2.0 safety margin |
| Trim silence | On all chunks **except the last** | Prevents eating the story ending |
| Crossfade | 50ms | Smooths chunk boundaries |
| Gaps | 0ms (none) | Crossfade alone is sufficient |

### Pitfalls
- **Trimming the last chunk eats the ending:** Higgs' trailing audio after the last sentence is low-energy; `trim_silence` misidentifies it. Skip trimming on the final chunk.
- **Too-small token budget drops words:** The smart formula must have ≥2.0× safety margin. If words are still dropped, switch to flat 4,096 tokens per chunk and accept trailing noise (the crossfade masks it).
- **VRAM leaks across runs:** After 3–4 full-story syntheses, VRAM drops from ~2.7GB free to <500MB. SGLang-Omni returns near-empty WAVs. Fix: `pkill -f sgl-omni && sgl-omni serve --model-path ... --port 8000`.

## CSS: Modal `hidden` Attribute Override

When a CSS rule sets `display: flex` (or any non-`none` value) on an element, the browser's native `[hidden] { display: none }` user-agent stylesheet is overridden. The modal stays visible.

**Fix:** Always pair `hidden` with an explicit style toggle in JS, and add a CSS override:
```css
.modal[hidden],
.modal[style*="display: none"] { display: none !important; }
```
```javascript
function openModal()  { el.hidden = false; el.style.display = 'flex'; }
function closeModal() { el.hidden = true;  el.style.display = 'none';  }
```

## Electron: IPC Timing vs Direct HTTP

Electron's `mainWindow.webContents.send()` may fire before the renderer registers its listener (`ipcRenderer.on()`). The health status shows "Connecting…" forever.

**Fix:** Use direct HTTP polling as the primary health channel, IPC as secondary (for alerts only):
```javascript
// Primary: direct fetch — always works
async function pollHealthDirect() {
  const r = await fetch('http://127.0.0.1:7861/api/health');
  const d = await r.json();
  // update status bar from d.flask_ready / d.sglang_ready
}
setInterval(pollHealthDirect, 8000);

// Secondary: IPC for restart / startup-failed alerts only
window.higgs.onStartupFailed((payload) => toast(payload.message));
```

## Windows + WSL: Subprocess Path Translation

**SGLang-Omni runs inside WSL2** and cannot read native Windows paths (`C:\Users\...`). Reference audio files stored on the Windows filesystem must be translated to WSL `/mnt/` paths:
```python
def _wsl_path(windows_path: str) -> str:
    import re
    p = windows_path.replace('\\', '/')
    m = re.match(r'^([A-Za-z]):/', p)
    if m:
        p = f'/mnt/{m.group(1).lower()}/{p[3:]}'
    return p
```

**Batch scripts (.bat) spawned from Electron** must use WSL-side paths, not Windows paths:
```batch
:: WRONG — venv inside WSL, not on Windows
set SGLANG_VENV=%USERPROFILE%\.higgs-sglang-venv

:: RIGHT — use WSL-native path
wsl -d Ubuntu -- bash -c "source ~/.higgs-sglang-venv/bin/activate && sgl-omni serve ..."
```

## Stale Flask Process Cleanup

On Windows, `proc.kill()` doesn't always clean up. Multiple Flask instances accumulate on the same port, each serving old code.

**Fix:** Clean port before starting:
```bash
netstat -ano | grep ":7861" | grep LISTENING | awk '{system("taskkill -PID "$5" -F")}'
```

Or in Electron's `startFlaskProxy()`:
```javascript
if (flaskProcess) {
    try { flaskProcess.kill(); } catch {}
    flaskProcess = null;
}
```
