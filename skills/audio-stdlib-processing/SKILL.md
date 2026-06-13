---
name: audio-stdlib-processing
description: "Process 16-bit mono WAV audio with zero dependencies — pure Python wave + struct. Gain, silence, concatenation, crossfade."
version: 1.0.0
category: software-development
metadata:
  hermes:
    tags: [audio, wav, pcm, stdlib, wave, struct, dsp]
---

# Audio Processing with Python Stdlib

Process 16-bit mono WAV audio files using only `wave` and `struct` from the Python standard library. No numpy, no scipy, no ffmpeg. Suitable for post-processing TTS output.

## When to Use

- Post-processing TTS output (volume boost, silence trimming, concatenation)
- Any 16-bit mono PCM WAV at arbitrary sample rates
- Environments where numpy/scipy aren't available or desirable

## Core Operations

### Amplify (Fixed Gain)

Multiply every sample by a linear gain factor. Clip to 16-bit range.

```python
import io, struct, wave

def apply_gain(wav_bytes: bytes, gain: float = 1.8) -> bytes:
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

### Generate Silence

Produce `N` milliseconds of digital zeroes as a valid WAV.

```python
def silence_ms(duration_ms: int, sample_rate: int = 24000) -> bytes:
    nframes = int(sample_rate * duration_ms / 1000)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
        wf.writeframes(b'\x00\x00' * nframes)
    return buf.getvalue()
```

### Concatenate with Crossfade

Join multiple WAVs. Optional `crossfade_ms` fades between chunks (warning: fades first word of chunk B — use `crossfade_ms=0` with `gap_ms` instead if preserving speech).

```python
def concat_wavs(wavs: list[bytes], crossfade_ms: int = 0, gap_ms: int = 100) -> bytes:
    if len(wavs) == 1: return wavs[0]
    # Parse all WAVs into sample arrays
    parsed = []; ref_params = None
    for wav in wavs:
        with wave.open(io.BytesIO(wav), "rb") as wf:
            p = wf.getparams()
            if ref_params is None: ref_params = p
            frames = wf.readframes(p.nframes)
            fmt = f"<{p.nframes}h"
            parsed.append(list(struct.unpack(fmt, frames)))
    # Generate gap silence if needed
    gap = []
    if gap_ms > 0:
        gap_wav = silence_ms(gap_ms, ref_params.framerate)
        with wave.open(io.BytesIO(gap_wav), "rb") as wf:
            gf = wf.readframes(wf.getnframes())
            gap = list(struct.unpack(f"<{wf.getnframes()}h", gf))
    # Build output with crossfade and gaps
    xfade_frames = max(1, int(ref_params.framerate * crossfade_ms / 1000))
    output = parsed[0]
    for i in range(1, len(parsed)):
        if gap: output.extend(gap)
        if crossfade_ms > 0 and len(output) >= xfade_frames and len(parsed[i]) >= xfade_frames:
            for j in range(xfade_frames):
                t = j / xfade_frames
                idx_prev = len(output) - xfade_frames + j
                output[idx_prev] = int(output[idx_prev] * (1.0 - t) + parsed[i][j] * t)
            output.extend(parsed[i][xfade_frames:])
        else:
            output.extend(parsed[i])
    # Write output
    buf = io.BytesIO()
    new_params = ref_params._replace(nframes=len(output))
    with wave.open(buf, "wb") as wf:
        wf.setparams(new_params)
        wf.writeframes(struct.pack(f"<{len(output)}h", *output))
    return buf.getvalue()
```

## Pitfalls

### Crossfade Eats First Word of Each Chunk

The crossfade algorithm fades chunk B in from 0 at t=0 to full volume at t=crossfade_ms. This means the first `crossfade_ms` of every chunk after the first is attenuated, potentially eating short opening words. **Prefer `gap_ms` with `crossfade_ms=0` when preserving speech boundaries.**

### Trim Silence is Unreliable with Variable-Amplitude Speech

Both ratio-based (threshold as % of peak) and absolute-threshold trimming fail with voice-cloned audio where amplitude varies per chunk. A quiet sentence may have a peak of 500 (out of 32767); a 2% threshold = 10, which overlaps with the model's trailing noise floor (±5-50). **Do not rely on silence trimming for TTS output — structure the generation to avoid trailing noise instead.**

### Fixed Gain Can Clip

If the input already peaks at 32767, applying gain > 1.0 will clip samples. The `apply_gain` function above clips safely, but this changes the waveform. Consider peak normalization instead for variable-volume inputs.
