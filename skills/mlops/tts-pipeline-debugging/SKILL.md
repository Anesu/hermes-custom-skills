---
name: tts-pipeline-debugging
description: Debug audio synthesis quality issues — silence, truncation, missing words, corruption. Covers token budget calibration, silence-trimming pitfalls, chunking strategies for long-form TTS, and server-health-as-root-cause for generative model pipelines.
triggers:
  - TTS audio has silence, truncation, missing words, or corruption
  - Long-form speech synthesis (stories, narration) producing incomplete output
  - Debugging chunked/segmented audio generation
  - User reports "first word missing" or "ending cut off" in synthesized speech
  - VRAM exhaustion during inference causing degraded output
---

# TTS Pipeline Debugging

Debugging audio synthesis quality for chunked/long-form text-to-speech pipelines (SGLang-Omni, Higgs, Kokoro, or similar generative audio models).

## Core principle: server freshness dominates algorithm tuning

Through 11 iterations of trimming algorithms, token budgets, and crossfade configurations, the single largest variable in output quality was **SGLang server freshness**. A freshly-restarted server produced clean audio with every trim strategy. A degraded server (multiple prior syntheses without restart) produced silent/corrupt chunks regardless of the algorithm.

**Always restart the inference server before debugging trimming/chunking.**

## Token budget calibration

For models without an EOS token (Higgs Audio v3, similar AR decoders):

| Approach | Result |
|---|---|
| Generous budget (2-3× needed) | Model fills budget with trailing noise → needs trimming → trimming eats words |
| Tight budget (1.1-1.3× needed) | Model finishes text and stops with minimal trailing noise → no trimming needed |

**Formula:** `tokens = chars / speaking_rate * audio_tokens_per_sec * margin`

For Shona (~13 chars/sec): `chars / 13 * 50 * 1.3`
For English (~12 chars/sec): `chars / 12 * 50 * 1.3`

## Silence trimming pitfalls

### Ratio-based trimming (DANGEROUS)
`threshold = peak * ratio` — if a chunk has naturally quiet speech (voice clone variance, low-energy phonemes), the threshold scales down and **eats real speech**. Do not use for voice-cloned audio.

### Absolute-threshold trimming (SAFE)
`cut where abs(sample) < 100` (post-gain). Real speech samples are ±500–20,000. Model trailing noise is ±5–50. This threshold cleanly separates them regardless of per-chunk volume variance.

### Crossfade between chunks
Crossfading fades chunk B's first N ms from 0 → full volume. **This eats the first word of every chunk after #1.** Use hard cuts with a small silence gap (100ms) instead.

### Last-chunk protection
Never trim the last chunk of a multi-chunk synthesis. The model's natural amplitude decay at sentence endings will be misinterpreted as "silence" and cut by any trim algorithm.

## Chunking strategy for long-form narration

- **200 chars/chunk** is a good default for Shona/English
- Each chunk must get its own token budget (see formula above)
- Split on sentence boundaries (`(?<=[.!?])\s+`)
- Gap between chunks: 100ms silence (clean separation, no word-eating)
- Volume boost: 1.8× for Higgs (output is naturally quiet)

## VRAM exhaustion pattern

SGLang-Omni accumulates VRAM across synthesis requests without releasing it. Symptoms:
- Later chunks become near-silent or corrupted
- `avail_mem=0.00 GB` during CUDA graph capture
- Audio file sizes shrink dramatically across runs (6MB → 4MB → 47KB)

**Fix:** Restart the inference server. For SGLang-Omni: `pkill -f sgl-omni && sgl-omni serve ...`

## Reference files

- `references/v1-v11-iteration-log.md` — complete 11-version debugging history for 1,253-char Shona folktale
- `references/rungano-architecture.md` — Electron + Flask + WSL2 SGLang-Omni three-process architecture

## Debugging workflow

1. Restart inference server (fresh VRAM)
2. Test with a single short sentence — verify clean audio
3. Test with 2-3 chunks — verify chunk boundaries, first words, endings
4. Run full text
5. If quality degrades: restart server, not the trimming algorithm
