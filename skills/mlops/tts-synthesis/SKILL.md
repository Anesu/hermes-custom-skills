---
name: tts-synthesis
description: Text-to-speech synthesis with local models (Higgs, Kokoro, etc.) — chunking, VRAM management, audio post-processing, and debugging silent/corrupted output.
trigger:
  - User asks to generate speech/audio from text
  - User asks to synthesize/narrate a story
  - User reports silent audio, missing words, or corrupted TTS output
  - User asks about chunking text for TTS
  - User asks about voice cloning with reference audio
---

# TTS Synthesis

## Architecture pattern

The proven stack for local TTS with a desktop UI:

```
Electron (renderer) → Flask proxy → SGLang-Omni (or equivalent server) → model on GPU
```

- Flask sits between the UI and the inference server
- `/api/tts` for single-chunk short text
- `/api/tts/long` for auto-chunked long text
- `/api/health` reports GPU VRAM + server status
- Voice catalog manages preset + custom (cloned) voices

## Chunking strategy for long text

Local TTS models (Higgs, Kokoro, etc.) have hard token buffer limits. Higgs: **4,096 tokens max** (issue #163). No EOS token — model generates until budget exhausted, then pads silence.

### Default config (proven for Shona)

| Parameter | Value | Why |
|---|---|---|
| `chunk_size` | 200 chars | ~16s speech — stays under 4,096 tokens |
| Token budget | `min(4096, max(768, len(chars)/8 * 50 * 2.0))` | Generous enough to never truncate |
| `trim_silence` per chunk | On all chunks **except the last** | Prevents eating the ending |
| `trim_silence` threshold | 0.02 (2% of peak) | Catch trailing noise, not quiet speech |
| `crossfade_ms` | 0 | Crossfade eats first words of subsequent chunks |
| `gap_ms` between chunks | 100 | Clean separation without audible silence |

### Why NOT to crossfade

A crossfade fades the incoming chunk from 0→full volume over N ms. The first N ms of every chunk (after #1) plays at reduced volume — this eats short opening words like "Kare" or "Zuva."

Use explicit silence gaps instead (`gap_ms=100`).

### Why NOT to trim the last chunk

`trim_silence` scans forward for the last window above threshold. On the final chunk, the model's trailing quiet ending (~5–10% of peak) falls below threshold and gets cut — losing the final sentence. Skip trimming on `chunks[-1]`.

## VRAM management

Local models leak VRAM across synthesis runs. Symptoms:
- Chunks return near-empty WAVs (47KB for 1,253 chars)
- `sglang_ready=true` but 429MB free out of 24GB
- Model health endpoint reports healthy but all output is silent

**Fix**: restart the inference server between long sessions.
```bash
# In WSL:
pkill -f sgl-omni
sgl-omni serve --model-path <model> --port 8000
```

Monitor VRAM before synthesis. If free VRAM < 2GB, restart.

## Audio post-processing pipeline

1. **Raw WAV from model** — may be quiet (Higgs outputs low amplitude)
2. **`apply_gain(wav, gain=1.8)`** — linear multiplication, clips to 16-bit range
3. **`trim_silence(wav, threshold_ratio=0.02, pad_sec=0.2)`** — strips trailing noise
4. **`concat_wavs(wavs, crossfade_ms=0, gap_ms=100)`** — joins chunks with silence gap

Do NOT apply `trim_silence` a second time on the combined output — it can eat the ending of the last chunk.

## Voice cloning

SGLang-Omni accepts reference audio via the OpenAI-compatible endpoint:
```json
{
  "input": "Text to speak",
  "references": [{"audio_path": "/path/to/ref.wav", "text": "What the reference says"}],
  "temperature": 0.8, "top_k": 50, "max_new_tokens": 2048
}
```

- Reference audio: 10–30s, clean, matching transcript
- Path must be WSL-accessible (`/mnt/c/Users/...`) when SGLang runs in WSL2
- Files with spaces in names work when passed through JSON (no quoting issue)

## Debugging silent/corrupted output

| Symptom | Cause | Fix |
|---|---|---|
| All chunks near-empty (47KB total for 1,253 chars) | VRAM exhaustion | Restart inference server |
| Last sentence missing | `trim_silence` on final chunk | Skip trim on `chunks[-1]` |
| First word of chunks 2+ missing | Crossfade fading in from 0 | `crossfade_ms=0`, use `gap_ms` instead |
| Mid-chunk words missing | Token budget too tight | Increase budget multiplier (2.0→3.0) |
| Entire chunks silent | `trim_silence` threshold too aggressive | Lower `threshold_ratio` (0.03→0.02→0.01) |
| Multiple Flask processes on same port | Process leaks from kills | `netstat -ano \| grep :PORT \| grep LISTENING` then `taskkill` |

## SGLang-Omni install notes

- **Not on PyPI** — source-only install: `git clone` + `uv pip install -v -e .`
- `uv pip install "sglang[all]"` hangs (hundreds of deps) — use `sglang` core-only
- `set -euo pipefail` breaks on `nvidia-smi | head` (SIGPIPE) — disable pipefail
- Model download: dual `huggingface-cli` processes corrupt WSL filesystem — use single sequential download
- Higgs model: `huggingface-cli download bosonai/higgs-audio-v3-tts-4b`
- Higgs v3 uses SGLang-Omni, NOT the deprecated `boson-ai/higgs-audio` repo

## WSL2 command patterns from Windows

Always use `-d Ubuntu` to avoid "User not found" and empty-shell issues:
```bash
wsl -d Ubuntu -- bash -c "command here"
```

Not `wsl bash -c` (may fail with "bash: not found" or "User not found").
