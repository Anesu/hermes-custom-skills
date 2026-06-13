---
name: tts-serving
description: Serve and debug Text-to-Speech models with SGLang-Omni. Token budgeting, chunking, silence handling, VRAM management, and audio quality debugging for models without EOS tokens.
---

# TTS Model Serving & Debugging

Serve and debug Text-to-Speech models (Higgs, Fish, Voxtral, Qwen3-TTS) via SGLang-Omni. Covers token budgeting for models without EOS, chunking long-form text, silence/noise management, VRAM monitoring, and audio quality debugging.

## Trigger

Load when:
- Serving a TTS model via SGLang-Omni and hitting silence/truncation/corruption
- Debugging audio quality in chunked TTS synthesis (missing words, gaps, trailing noise)
- Setting up a Flask proxy between a desktop app and SGLang-Omni
- Connecting Electron/desktop UI to a local TTS inference server

## Core Architecture

```
Desktop UI (Electron) → Flask proxy :7861 → SGLang-Omni :8000 → GPU
                         /api/tts           /v1/audio/speech
                         /api/tts/long      OpenAI-compatible
```

## TTS Model No-EOS Problem

Many TTS models (Higgs Audio v3, others) lack an end-of-sequence token. Given `max_new_tokens`, the model generates audio until the budget is exhausted, producing trailing noise/silence after the speech ends.

**Do NOT fight this with silence trimming.** Trimming algorithms (energy-threshold, window-based) are unreliable — they either eat real speech tails or keep noise. Instead:

### The Tight-Budget Approach

Give the model barely enough tokens to speak the text. Minimal margin = minimal trailing noise = no trimming needed.

```
max_new_tokens = chars / speaking_rate * audio_tokens_per_sec * margin

Example (Shona, Higgs v3):
  speaking_rate = 13 chars/sec  (calibrate per language)
  audio_tokens_per_sec = 50     (Higgs: 24kHz / 480 downsample)
  margin = 1.3                  (30% safety)

  For 200 chars: 200/13 * 50 * 1.3 = 1,000 tokens (~20s)
```

**Calibrate `speaking_rate` per language.** English ≈15 chars/sec. Shona ≈13 chars/sec (longer words). If audio is longer than expected, lower the rate. If words are cut, raise the margin or lower the rate.

## Chunking Long-Form Text

For text exceeding the model's buffer (Higgs: 4,096 tokens max safe, issue #163):

1. Split on sentence boundaries (`.!?` followed by space, or `\n\n`)
2. Chunk size: 150-200 chars. Shorter = safer per-chunk, but more chunks = more boundary issues
3. Each chunk gets its own tight token budget
4. Concatenate chunks with a small silence gap (50-100ms) — NOT crossfade

**Why no crossfade:** Crossfade fades the first N ms of each subsequent chunk from 0→full volume, eating the first word. Use hard silence gaps instead.

```python
def _split_sentences(text, max_chunk=200):
    import re
    parts = re.split(r"(?<=[.!?])\s+|\n\n+", text)
    chunks = []
    buf = ""
    for p in parts:
        p = p.strip()
        if not p: continue
        if len(buf) + len(p) + 1 <= max_chunk:
            buf = (buf + " " + p).strip() if buf else p
        else:
            if buf: chunks.append(buf)
            buf = p
    if buf: chunks.append(buf)
    return chunks if chunks else [text]
```

## Audio Concatenation

Use a tiny silence gap between chunks. Do NOT crossfade. Do NOT trim silence on individual chunks.

```python
def concat_wavs(wavs, gap_ms=100):
    # Insert silence between chunks, no crossfade
    # gap_ms=100 is ~0.1s — natural sentence pause
```

## VRAM Management

TTS models consume significant VRAM. SGLang-Omni accumulates memory across generations (CUDA graph caching, KV cache fragmentation).

**Symptoms of VRAM exhaustion:**
- Chunks return near-empty WAVs (few KB, near-zero audio)
- All chunks report "0 failed" but audio is silent
- VRAM free drops below 500MB

**Fix:** Restart SGLang-Omni. `pkill -f sgl-omni && sgl-omni serve ...`

**Monitor VRAM:** Add GPU memory to Flask `/api/health`:
```python
import subprocess
out = subprocess.check_output(
    ["nvidia-smi", "--query-gpu=memory.used,memory.total,memory.free",
     "--format=csv,noheader,nounits"], timeout=5, text=True
)
```

## SGLang-Omni Install

Source-only (no PyPI). Install in WSL2 (Linux-only):

```bash
# In WSL2:
uv venv --python 3.11 ~/.higgs-sglang-venv
source ~/.higgs-sglang-venv/bin/activate
git clone https://github.com/sgl-project/sglang-omni.git
cd sglang-omni
uv pip install "sglang"         # core only — [all] hangs resolver
uv pip install -v -e .          # sglang-omni from source
```

**Pitfalls:**
- `sglang[all]` hangs `uv` for 10+ minutes — install core only
- `--mem-fraction-static` not supported by Higgs pipeline config (rejected with validation error)
- `--cuda-graph-max-bs` and `--max-total-tokens` also rejected

## Voice Cloning Path Translation (WSL2)

When SGLang-Omni runs in WSL2 and Flask runs on Windows, voice reference audio paths need translation:

```python
def _wsl_path(windows_path):
    """C:\Users\...\audio.wav → /mnt/c/Users/.../audio.wav"""
    import re
    p = windows_path.replace('\\', '/')
    m = re.match(r'^([A-Za-z]):/', p)
    if m:
        p = f'/mnt/{m.group(1).lower()}/{p[3:]}'
    return p
```

## References

- `references/higgs-v3-details.md` — Higgs-specific: buffer limits, token rates, issue #163
