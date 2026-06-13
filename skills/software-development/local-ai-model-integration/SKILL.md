---
name: local-ai-model-integration
description: Integrate a self-hosted open-source AI model (TTS, LLM, image, audio, multimodal) into a Python or Node application via its serving framework's HTTP API. Covers the model card → cookbook → blog → API contract workflow, OpenAI-compatible endpoint patterns, control token injection (emotion, style, prosody for TTS; sampling params for LMs; CFG/scheduler for diffusion), voice cloning / LoRA / IP-Adapter reference handling, streaming SSE chunk reassembly, and graceful failure when the model server isn't running. Use when the user wants to consume a model on Hugging Face that has a serving framework (SGLang-Omni, vLLM, TGI, llama.cpp, ComfyUI, etc.), or when they ask how to wrap a model API in their own app.
---

# Local AI Model Integration

The class of work: **a self-hosted open-source AI model is on Hugging Face, has a serving framework, and you want to consume it from a Python or Node application.** This is the practical work of "I have a model URL and a model card — how do I call it?"

## When to use

- User wants to integrate a HF-hosted model (TTS, LLM, image, audio, multimodal) into their own app
- Model card points to a serving framework (SGLang-Omni, vLLM, TGI, llama.cpp, ComfyUI, etc.) with an HTTP API
- User is self-hosting the model on their own GPU (or on a remote box they control)
- You need to choose between consuming via the framework's native API or via the OpenAI-compatible surface it almost always provides

## When NOT to use

- The model is on a hosted API (OpenAI, Anthropic, etc.) — use a vendor SDK instead
- The model has no serving framework and no PyTorch/Transformers export — different problem
- User just wants to fine-tune or run inference in a notebook — different problem

## The 5-phase workflow (the one that actually works)

Phase ordering matters. Skipping a phase gets you stuck mid-build.

### Phase 1: Read the model card on Hugging Face

**Why first:** the model card is the source of truth for architecture, capabilities, control tokens, and license restrictions. Don't trust blog posts or third-party tutorials for the API contract — they go stale.

**What to extract:**
- **Architecture** (autoregressive decoder, diffusion, multi-stage, etc.) — affects latency and batching behavior
- **Input format** (text, audio, image, video, control tokens) and **output format** (sample rate, dimensions, file type)
- **Special tokens / control tags** — for TTS this is the `<|emotion:...|>` set; for LLMs it might be chat templates; for diffusion it might be CFG scale / scheduler args
- **Context length, VRAM footprint, recommended batch sizes** — sizing for the GPU
- **License restrictions** — research-only, non-commercial, voice cloning consent, etc. (the Boson Higgs v3 Research License is the strictest common case)
- **Cookbook or quickstart links** — usually a blog post or repo subdirectory

### Phase 2: Confirm the serving framework

**Why second:** the serving framework determines the actual HTTP API, not the model card. Most modern frameworks expose an **OpenAI-compatible surface** (POST `/v1/audio/speech`, `/v1/chat/completions`, `/v1/images/generations`), which is the easiest thing to consume.

**Checklist:**
- Is the framework on PyPI? (`pip install sgl-omni`) — if not, it's source-only
- Linux-only? — affects install plan (WSL vs native Windows)
- CUDA version requirements? — may not match the user's driver
- Documented startup command (e.g. `sgl-omni serve --model-path ...`)?
- Can you test with `curl` in 30 seconds? — if not, the framework isn't ready for production use
- **For `sglang` specifically:** NEVER install `sglang[all]` — the `[all]` extra pulls in flashinfer, sgl-kernel, xformers, and 200+ CUDA transitive deps that can hang `uv`'s resolver for 10+ minutes on machines with large pre-existing caches. Install `sglang` core-only, then let `sglang-omni`'s own source install (`pip install -e .`) pull in what it actually needs. Flashinfer and friends are optional accelerators — SGLang-Omni falls back to PyTorch native attention without them.

**Risk signal:** if the framework has under 1000 GitHub stars, no PyPI release, and "install from source" is the only path, plan a fallback. Source-only early-stage frameworks are the number one source of build-blocked projects.

**Model download hygiene:** use the standard HF cache (huggingface-cli without --local-dir). Serving frameworks resolve --model-path by looking in the standard cache tree. Using --local-dir creates a flat directory the framework may not find. Before re-downloading after a failed attempt, clean stale lock files: find ~/.cache/huggingface -name '*.lock' -path '*<model-name>*' -delete. Never run two simultaneous downloads of the same model. On WSL2, the 9P filesystem layer produces I/O errors from concurrent writes that cascade into WSL relay crashes.

### Phase 3: Lock the API contract from the cookbook

**Why third:** before writing any code, you need the exact JSON shape that the serving framework accepts and returns. Get this from the framework's cookbook (not the model card).

**What to capture:**
- Endpoint paths (`/v1/audio/speech`, `/v1/chat/completions`, etc.)
- Request body schema (required fields, optional fields, defaults)
- Response body schema (for streaming: SSE event names and payload shapes)
- Reference / clone format (audio path + transcript, IP-Adapter image, LoRA adapter name)
- Sampling parameters and their default values (temperature, top_k, top_p, max_new_tokens, CFG, etc.)
- Streaming mode toggle (`"stream": true` → SSE; otherwise blocking)

**Build a minimal curl test in this phase.** Don't write Python until the curl works. A 5-line `curl` that produces correct output is the highest-leverage debugging tool you'll ever have.

### Phase 4: Build a thin client as a single seam

**Why fourth:** with the API contract locked, the integration is just HTTP. Encapsulate it in one class/module — the "deep module" with a small stable interface.

**The interface should be:**
```python
class BackendClient:
    def __init__(self, backend_url, timeout): ...
    def generate(self, **kwargs) -> bytes: ...           # blocking, returns raw artifact
    def stream_generate(self, **kwargs) -> Iterator[bytes]: ...  # streaming, yields chunks
```

**The implementation does:**
- Request body construction (control token injection, reference handling, parameter mapping)
- HTTP request (use `requests` with a session)
- For streaming: parse SSE events, base64-decode chunks, yield raw bytes
- Error handling: clear exceptions with the backend's error message

**Anti-pattern:** the renderer / Flask layer calling the backend directly. Always go through this seam. When the serving framework changes (it will — they're all moving fast), only this one file needs updating.

### Phase 5: Verify end-to-end with real artifacts

**Why fifth:** unit tests on a mock backend don't catch real API mismatches. Run a real synthesis/generation, save the artifact, listen to it / look at it / read it back.

**What to verify:**
- A real artifact is produced (file exists, correct format, correct size)
- The artifact plays/opens/decodes correctly (don't trust file extension alone — verify with `ffprobe`, `PIL.Image.open()`, `soundfile.read()`, etc.)
- Latency is acceptable (a 30-second TTS call that takes 5 minutes is broken even if the output is correct)
- Streaming mode works (if supported) and chunks arrive in order
- Reference / clone produces output that actually matches the reference (not just the prompt)
- Error paths: bad input, missing reference, model not loaded — all should give clear error messages, not 500s

## Common control-token patterns

### TTS (Higgs Audio v3 example)

```python
# Control tags are inline in the input text
# Categories: emotion (21), style (3), prosody (10), SFX (9)
text = "<|emotion:amusement|><|prosody:speed_fast|>Wait, that was hilarious. <|sfx:laughter|>Hehe."
```

The model card has the full token list. Build a helper that takes structured UI selections (emotion dropdown, SFX toggles) and produces the right tag prefix.

### LLMs (chat models)

Most chat models follow the OpenAI chat completions format. Sampling params (`temperature`, `top_p`, `top_k`, `max_tokens`) are the standard knobs. Some models (Qwen, Llama) have their own chat templates — pass them through `transformers` if you're not using the OpenAI surface.

### Image / diffusion

Two main shapes:
- **Stable Diffusion WebUI / A1111 / Forge** — `POST /sdapi/v1/txt2img` with prompt, negative_prompt, sampler, steps, CFG scale, width/height, seed
- **ComfyUI** — workflow JSON via `POST /prompt`; the workflow is the API. This is its own class of integration (see the `comfyui` skill)

For **HuggingFace diffusers** served via a custom backend, the API is usually bespoke. Read the serving repo's docs.

### Voice cloning / reference conditioning

Pattern is consistent across TTS models (Higgs, Fish Audio, CosyVoice, etc.):
```json
{
  "input": "Text to synthesise",
  "references": [
    {
      "audio_path": "/abs/path/to/ref.wav",
      "text": "Transcript of the reference audio"
    }
  ]
}
```
The `text` field is often **as important as the audio** — it's the alignment signal that lets the model learn the speaker's voice. Always require it in your UI.

**WSL path pitfall:** if your Flask proxy runs on Windows but the serving framework runs inside WSL2, reference audio stored at `C:\Users\...` is NOT accessible from WSL. You must translate: replace `C:\\` with `/mnt/c/` and backslashes with forward slashes. Build a `_wsl_path()` helper in the proxy that does this before building the `references` list. Without it, the model returns 500 because it can't open the audio file.

## Audio post-processing (TTS-specific)

Most local TTS models output quiet audio. Higgs Audio v3 and similar raw-decoder models produce 16-bit PCM WAV with peak amplitudes around 30-40% of max — fine for research, too quiet for casual listening.

**Gain / volume normalization** — apply linear gain to 16-bit PCM samples after receiving from the backend:

```python
import struct, io, wave

def apply_gain(wav_bytes: bytes, gain: float = 1.8) -> bytes:
    if not wav_bytes or gain == 1.0:
        return wav_bytes
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        params = wf.getparams()
        frames = wf.readframes(params.nframes)
    fmt = f"<{params.nframes}h"
    samples = list(struct.unpack(fmt, frames))
    peak = 32767
    amplified = [max(-peak, min(peak, int(s * gain))) for s in samples]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setparams(params)
        wf.writeframes(struct.pack(fmt, *amplified))
    return buf.getvalue()
```

Use stdlib `struct` + `wave` — no numpy dependency. Default 1.8× gain works for Higgs; adjust per model. Clamp to [-32767, 32767] to avoid wraparound distortion.

**Peak normalization** — more conservative than fixed gain. Find max amplitude, scale to a target (e.g. 0.85 of 16-bit max). Useful when the user wants a consistent loudness regardless of input text length or voice.

**Long-form chunked synthesis** — for texts longer than ~300 characters, a single generate call exhausts the token budget and produces trailing silence. Solution: split text on sentence boundaries, synthesize each chunk separately, concatenate WAV files with a crossfade:

```python
# concat_with_crossfade: overlap last 50ms of chunk A with
# first 50ms of chunk B, fading A→0 while B→1.
# See higgs-tts-serving references/crossfade.py for the full impl.
combined = concat_with_crossfade(wavs, crossfade_ms=50)
```

**Pitfall: combined silence trim eats endings.** After concatenating all chunks, do NOT run `trim_silence()` on the combined WAV. The last chunk is often the quietest (model tapers off), and the trim function finds the \"last loud window\" before the actual end, truncating the final sentences. Per-chunk trimming already handles silence — remove the combined trim entirely.

```python
def concat_wavs(wavs: list[bytes]) -> bytes:
    """Concatenate mono 16-bit WAVs with identical sample rate into one."""
    # Read params from first WAV, accumulate frames, write combined
    with wave.open(io.BytesIO(wavs[0]), "rb") as wf:
        params = wf.getparams()
    all_frames = b"".join(
        wave.open(io.BytesIO(w)).readframes(wave.open(io.BytesIO(w)).getparams().nframes)
        for w in wavs
    )
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setparams(params._replace(nframes=len(all_frames) // (params.sampwidth * params.nchannels)))
        wf.writeframes(all_frames)
    return buf.getvalue()
```

The Flask endpoint pattern: `POST /api/tts/long` splits by sentence (regex on `[.!?] +`), generates each chunk with its own token budget, applies gain to each, concatenates. The renderer auto-detects long text and switches to this endpoint. Show chunk count in the UI (`"3 chunks"`).

**Token budget scaling** — TTS models generate audio tokens at a fixed rate (e.g. Higgs: 25 fps × 8 codebooks = 200 tokens/second). The `max_new_tokens` parameter must account for this:

| Text length | Speech duration (est.) | Tokens needed | Recommended `max_new_tokens` |
|---|---|---|---|
| <100 chars | ~5s | ~1000 | 1024 |
| 100-350 chars | ~15-30s | ~3000-6000 | 4096 |
| 350-800 chars | ~30-60s | ~6000-12000 | per-chunk 2048 (use chunking) |
| >800 chars | >60s | >12000 | Chunk into ≤350-char pieces, 2048/chunk |

The renderer's Advanced settings should default to 4096, and the server should auto-scale if the user-provided value is too low for the text length. The long-form chunking endpoint automatically gives each chunk its own budget, so it handles arbitrarily long texts.

## Streaming reassembly

For models that stream output, the chunks are usually base64-encoded inside SSE `data:` events. Pattern:
```python
for line in r.iter_lines(decode_unicode=True):
    if not line or not line.startswith("data:"): continue
    raw = line[len("data:"):].strip()
    if raw == "[DONE]": break
    obj = json.loads(raw)
    chunk_b64 = obj.get("audio_b64") or obj.get("data") or obj.get("audio")
    if chunk_b64:
        yield base64.b64decode(chunk_b64)
```

**Pitfall:** the field name varies (`audio_b64`, `data`, `audio`) across serving frameworks. Try them all if the obvious one is empty.

## Graceful failure when the server isn't running

Your client must not crash when the model server is down — the desktop app should show "Model: not ready" and recover when the server comes up.

```python
try:
    r = self._session.post(url, json=payload, timeout=self.timeout)
    r.raise_for_status()
    return r.content
except requests.exceptions.ConnectionError:
    raise BackendUnavailable("Model server not running. Start it with: <command>")
```

The error message should tell the user **how to fix it**, not just what failed.

## Risk assessment: framework is unstable?

| Signal | Risk level | Fallback |
|---|---|---|
| Has PyPI release, > 1k stars, recent commits | Low | Proceed |
| Source-only, < 1k stars, last commit > 30 days | Medium | Plan a 2-3 hour fallback (different framework or raw transformers) |
| No releases, no PyPI, < 500 stars, "WIP" in README | High | Don't build on this. Find a more stable framework or wait. |

For the Higgs Audio v3 case, SGLang-Omni is at the "Medium" level — source-only, 464 stars, but the cookbook works and the API contract is stable. Plan a `transformers`-loop fallback that bypasses SGLang-Omni entirely (slower, but doesn't depend on the framework).

## Companion skills to load

- `desktop-app-shell-windows` — if the integration is going into a desktop app
- `comfyui` — for ComfyUI workflow-based generation specifically
- `llama-cpp` — for local GGUF model inference
- `firecrawl-scrape` / `firecrawl-search` — for fetching model cards and cookbooks when you need to verify the API contract

## Reference files in this skill

- `references/api-contract-extraction.md` — the 5-line curl test pattern + checklist for locking the API contract.
- `references/control-token-injection.md` — how to build a `build_input_text()` helper that takes structured UI selections and produces inline control tokens.
- `references/streaming-reassembly.md` — SSE chunk reassembly patterns, base64 vs raw, field name variations.
- `references/vram-exhaustion-diagnosis.md` — diagnosing and fixing `avail_mem=0.00 GB` during CUDA graph capture.
- `references/lm-studio-bridge-pattern.md` — Node bridge server that connects a browser game to LM Studio: runtime model detection, graceful offline fallback, per-NPC markdown memory, in-game model/URL switching, and JSON extraction hardening for model output.
- `templates/backend-client.py.template` — the deep-module pattern (small stable interface, hidden complexity).
- `scripts/probe-backend.sh` — a 30-second smoke test (curl + check status + check content-type) for any OpenAI-compat backend.
