---
name: higgs-tts-serving
description: Serve Higgs Audio v3 TTS locally via SGLang-Omni. Covers install quirks, chunking strategy for long text, silence trimming, WSL path translation, VRAM management, and common pitfalls.
---

# Higgs TTS Serving

Serve [Higgs Audio v3 TTS](https://huggingface.co/bosonai/higgs-audio-v3-tts-4b) locally via SGLang-Omni on an NVIDIA GPU. The model generates 24kHz speech across 102 languages with voice cloning and inline emotion/style/prosody control.

## Trigger conditions
- User wants to run Higgs Audio v3 TTS locally
- User needs SGLang-Omni setup for any omni-model
- User reports audio truncation, silence, or corruption during long Higgs synthesis
- User is building a TTS desktop app with Flask/Electron proxy pattern

---

## 1. SGLang-Omni Install (WSL2 on Windows)

The model is served via `sgl-omni` — NOT `sglang` directly. The package is `sglang-omni`, installed from source (not on PyPI — `pip install sgl-omni` 404s).

```bash
# In WSL2:
git clone https://github.com/sgl-project/sglang-omni.git ~/sglang-omni
python3 -m venv ~/.higgs-sglang-venv
source ~/.higgs-sglang-venv/bin/activate

# CRITICAL: install sglang CORE only, not [all]
# sglang[all] pulls flashinfer/xformers/sgl-kernel — hundreds of packages
# that hang uv's resolver for 10+ minutes. Higgs TTS doesn't need them.
uv pip install "sglang"

# Then install sglang-omni from source:
cd ~/sglang-omni
uv pip install -v -e .

# Download model (~8 GB):
huggingface-cli download bosonai/higgs-audio-v3-tts-4b

# Serve:
sgl-omni serve --model-path bosonai/higgs-audio-v3-tts-4b --port 8000
```

**Pitfall: bash pipefail kills install scripts.** `nvidia-smi | head -10` causes SIGPIPE when `head` closes the pipe. Always add `set +o pipefail` in install scripts, or use:
```bash
nvidia-smi 2>&1 | head -10 || true
```

**Pitfall: `--mem-fraction-static` rejected.** SGLang-Omni's Higgs pipeline rejects this flag. VRAM management must be done by freeing GPU memory before launch (close LM Studio, Brave, ComfyUI).

**Pitfall: `--cuda-graph-max-bs` and `--max-total-tokens` rejected.** These are SGLang flags, not SGLang-Omni flags. Higgs TTS pipeline has its own config (`HiggsTtsPipelineConfig`).

---

## 2. The 4,096-Token Buffer Problem (Issue #163)

Higgs v3 has a **hard 4,096-token buffer** and **no EOS token**. The model generates audio until the buffer is exhausted, then produces silence/padding. At 50 audio tokens/second, the safe limit is ~80 seconds of speech.

**Symptoms:**
- First 20-30 seconds of audio are perfect speech
- Remainder is silence, breath noise, or garbled audio
- Total WAV file is much longer than expected

**Fix: sentence-level chunking with silence trimming.**

Split text into ~200-char chunks (≤200 chars = ~16s speech = ~800 tokens — safely under 4,096). Synthesize each chunk separately, then concatenate WAVs.

```
200 chars → ~16s speech → ~800 tokens ← well within 4,096 limit
```

**Token budget formula** (chars → max_new_tokens):
```
min(4096, max(768, int(len(text) / 8 * 50 * 2.0)))
```
- `/8` = chars per second of speech (8 for Shona; 12 for English)
- `×50` = audio tokens per second
- `×2.0` = safety margin

---

## 3. Silence Trimming

After each chunk, strip trailing low-energy audio. Use a sliding-window amplitude detector:

```python
def trim_silence(wav_bytes, threshold_ratio=0.02, pad_sec=0.2, window_ms=50):
    """
    threshold_ratio: fraction of peak amplitude below which = silence
    pad_sec: keep this much audio after last loud window (breath room)
    window_ms: sliding window size for energy detection
    """
```

**Tuning for Higgs:**
- `threshold_ratio=0.02` (2% of peak) — Higgs generates low breath noise after speech, not true silence. 0.03 clips legitimate speech, 0.01 misses breath noise.
- `pad_sec=0.2` — short pad between chunks
- Apply per-chunk ONLY. **Do NOT trim the concatenated output** — the combined `trim_silence()` on the final WAV clips the quiet ending of the last chunk, cutting off the final sentences of the story. Per-chunk trimming already handles silence; the concatenated file needs no further processing.

**Pitfall: combined trim eats endings.** The last chunk of a long text is often the quietest (model tapers off amplitude at the end). Running `trim_silence()` on the fully concatenated WAV finds the "last loud window" well before the actual end and truncates. Fix: remove the combined trim entirely. Only trim per-chunk.

**Crossfade between chunks.** Hard cuts between concatenated chunks create audible clicks. Apply a 50ms crossfade: overlap the last N frames of chunk A with the first N frames of chunk B, fading A out while fading B in (linear interpolation). This is cheap (no extra dependencies) and makes the concatenation sound like one continuous recording. See `references/crossfade.py` for the implementation.

---

## 4. WSL Path Translation

SGLang-Omni runs inside WSL2 and cannot read native Windows paths (`C:\Users\...`). Reference audio files must be mapped to `/mnt/c/Users/...`:

```python
def _wsl_path(windows_path: str) -> str:
    import re
    p = windows_path.replace('\\', '/')
    m = re.match(r'^([A-Za-z]):/', p)
    if m:
        p = f'/mnt/{m.group(1).lower()}/{p[3:]}'
    return p
```

---

## 5. VRAM Reality

Higgs 4B on RTX 3090 (24GB):
- Model weights: ~8GB BF16
- CUDA graphs: ~2-4GB
- Pipeline stages (4): ~2-3GB each during inference
- **Total: ~18-22GB**

**Must have >22GB free VRAM** for reliable operation. Close GPU-heavy apps (LM Studio, Brave with hardware acceleration, ComfyUI) before launching. VRAM pressure causes OOM crashes during CUDA graph capture or mid-synthesis.

---

## 6. Process Management

**Multiple Flask processes accumulate** — on restart, if old processes aren't killed, port 7861 gets multiple listeners all serving stale code. Always:
```bash
# Kill all on target port before restarting
netstat -ano | grep ":7861" | grep LISTENING | awk '{system("taskkill -PID "$5" -F")}'
```

**`detached: true` creates orphans** — on Windows, `child_process.spawn` with `detached: true` means the child survives parent exit. For WSL-based subprocesses, `process.kill()` doesn't propagate through cmd.exe → wsl.exe → bash. Always kill WSL-side too:
```bash
wsl -d Ubuntu -- bash -c "pkill -f sgl-omni"
```

**`.bat` spawn on Windows requires `shell: true`** — otherwise `EINVAL`. The `.bat` wrapper must use `wsl -d Ubuntu --` (not bare `wsl`) to target the correct distro.

---

## 7. Verified Configuration

| Component | Value |
|---|---|
| GPU | RTX 3090 24GB |
| Model | `bosonai/higgs-audio-v3-tts-4b` |
| Serving | SGLang-Omni (source, `sglang` core-only) |
| Python | 3.11.14 (WSL2 venv) |
| VRAM used | ~21.5GB loaded, ~2.5GB free |
| Port layout | SGLang-Omni :8000, Flask proxy :7861 |

**Proven with Shona (1,251 chars, 8 chunks, 1.6min audio, zero failures):**
```python
# Long-form endpoint — auto-chunks + silence trimming
POST /api/tts/long
{
    "text": "...full story...",
    "voice_id": "42cf79d2cb",
    "chunk_size": 200,
    "volume": 1.8
}
# → 114s synthesis, 4.3MB WAV, ~96s clean audio, zero silence padding
```

## 8. Support Files

- `references/audio-postprocessing.py` — reusable `trim_silence`, `apply_gain`, `concat_wavs`

---

## 8. Quick Test

```bash
# From inside WSL:
curl -X POST http://127.0.0.1:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input":"Hello, this is a test.", "max_new_tokens": 256}' \
  --output test.wav

# With voice cloning:
curl -X POST http://127.0.0.1:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input":"Hello.", "references": [{"audio_path": "/path/to/ref.wav", "text": "Reference transcript"}], "max_new_tokens": 256}' \
  --output test.wav
```
