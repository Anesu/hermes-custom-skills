---
name: scribe
description: "Download YouTube audio, transcribe (whisper.cpp CPU/mobile OR openai-whisper GPU), curate into polished markdown with AI-authored title. Pipeline: yt-dlp → ffmpeg → whisper → curation → .md."
version: 4.1.0
category: productivity
related_skills:
  - watch
metadata:
  hermes:
    tags: [youtube, transcription, whisper, whisper-cpp, ffmpeg, markdown, audio, curation, cpu, mobile]
---

# yt-transcribe — YouTube Transcription + Curation

Transcribe any YouTube video, then **curate** — the AI acts as editor: authors a substantive title (discarding clickbait), restructures around the core argument, adds chapter timestamps, flags low-confidence segments, produces navigable polished markdown. Not a raw stenography dump.

## Engine Selection

| Engine | Hardware | Speed (12-min) | Accuracy | Setup |
|---|---|---|---|---|
| **whisper.cpp** (default) | CPU / ARM / mobile | ~3-5 min | Excellent (base.en) | `git clone whisper.cpp`, download model, cmake build |
| **openai-whisper** | NVIDIA GPU (CUDA) | ~30-60 sec | Excellent (turbo) | `pip install openai-whisper torch` |

**Auto-detect:** `python -c "import torch; print(torch.cuda.is_available())"` → True = GPU path, else CPU.

## Prerequisites

```bash
# Both paths
pkg install ffmpeg yt-dlp python          # core tools

# CPU path (whisper.cpp) — one-time setup
cd ~ && git clone --depth 1 https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp && bash ./models/download-ggml-model.sh base.en
cmake -S . -B build -DGGML_NO_OPENMP=ON && cmake --build build -j"$(nproc)"
# Binary: ./build/bin/whisper-cli | Model: models/ggml-base.en.bin

# GPU path (openai-whisper)
uv pip install openai-whisper torch --index-url https://download.pytorch.org/whl/cu128
```

## Quick Reference (Run This)

```bash
# 0. DRY-RUN (videos >10 min)
yt-dlp --print "%(title)s -- %(uploader)s -- %(duration)s" "URL"

# 1. ACQUIRE — download audio
yt-dlp -f "bestaudio[ext=m4a]/bestaudio" -o "input.m4a" "URL"
yt-dlp --print "%(title)s -- %(uploader)s -- %(duration)s" "URL"  # metadata

# 2. CONVERT — 16kHz mono WAV
ffmpeg -i "input.m4a" -ar 16000 -ac 1 -sample_fmt s16 "audio_16k.wav" -y

# 3. TRANSCRIBE
# CPU (whisper.cpp):
~/whisper.cpp/build/bin/whisper-cli -m ~/whisper.cpp/models/ggml-base.en.bin \
  -f "audio_16k.wav" -l en -otxt -osrt -of "raw_transcript"
# GPU (openai-whisper): use whisper.load_model("turbo").transcribe("audio_16k.wav")

# 4. READ — classify content type (see table below), read raw transcript, identify core argument

# 5. CURATE — apply template matching content type (see Curator Templates below)

# 6. SAVE
python3 -c "
import re
title = re.sub(r'[<>:\"/\\\\|?*]', '—', f'{curated_title} -- {uploader}')
open(f'{title}.md', 'w').write(report)
"
rm audio_16k.wav input.m4a raw_transcript.* 2>/dev/null

# 7. VERIFY — run checklist (see Verification below)
```

## Content-Type Detection

Classify the transcript into ONE type. The curation template adapts accordingly:

| Type | Signature | Curation Strategy |
|---|---|---|
| **Framework Talk** | Model, taxonomy, system (e.g. "four types of X") | Framework-first; stories as illustrations |
| **Interview** | Multiple speakers, Q&A rhythm | Thematic grouping, not chronological |
| **Sermon / Lecture** | Single speaker, scripture/text-anchored | Passage → exposition → application |
| **Tutorial / How-To** | Step-by-step, numbered sequence | Chronological; code blocks verbatim |
| **Narrative / Story** | Personal journey, emotional arc | Chronological with thematic headers |
| **Debate / Panel** | Opposing views, rebuttals | Position → counter-position → synthesis |

**Default to Framework Talk** if uncertain — most common for long-form YouTube.

## Curator Templates

All types share these **universal rules**:
1. **TITLE** — substantive, no clickbait, names the core argument/framework
2. **CHAPTERS** — timestamp map: `| HH:MM:SS | Section |`
3. **AT A GLANCE** — reader gets the argument in 30 seconds (summary table or bullets)
4. **PULL QUOTES** — one `>` blockquote per major section
5. **LOW CONFIDENCE** — append `⚠️ Segments for Review` appendix (GPU path only; CPU/whisper.cpp skips)
6. **TRIM** — remove promotional plugs, "like and subscribe", repetitive examples, throat-clearing

**Type-specific adaptations** (apply ON TOP of universal rules):

| Type | Title Format | Body Structure | Extra Sections |
|---|---|---|---|
| **Framework Talk** | Names the framework | Lead with concept, then speaker's stories as illustrations. NOT chronological. | WHY THIS MATTERS, HOW TO APPLY, THE TRAP (meta-insight), ABOUT THE SPEAKER |
| **Interview** | `{Guest} on {Topic}` or best quote | Group by topic cluster. Preserve `Host:` / `Guest:` labels. | KEY TAKEAWAYS |
| **Sermon / Lecture** | `{Passage}: {Core Message}` | Passage → Exposition (what it means) → Application (what to do). Scripture in `>` blockquotes. | — |
| **Tutorial / How-To** | `How to {Goal}: {Method}` | Chronological numbered steps. Code/commands in ``` fences. | Prerequisites |
| **Narrative / Story** | Emotional/thematic core | Chronological with thematic headers. Preserve arc. | ABOUT THE SPEAKER |
| **Debate / Panel** | `{Topic}: {Position A} vs {Position B}` | Per-topic: Position → Counter-Position → Rebuttal → Synthesis. Preserve speaker labels. | — |

**Post-curation:** (1) Map chapter timestamps to `HH:MM:SS` format. (2) Append low-confidence appendix if GPU path. (3) Sanitize filename — replace `<>:"/\|?*` with `—`.

## Model Reference

| Model | Disk | Speed | Best For |
|---|---|---|---|
| whisper.cpp `tiny.en` | 75 MB | ~1.5 min | Fast drafts |
| whisper.cpp `base.en` | 141 MB | ~3-4 min | **Default** |
| whisper.cpp `small.en` | 480 MB | ~8-10 min | Detailed |
| whisper.cpp `medium.en` | 1.5 GB | ~20 min | Near GPU quality |
| openai-whisper `turbo` | 809M params | ~32× realtime | GPU default |
| openai-whisper `large-v3` | 1.5B params | ~16× realtime | Non-English, rare terms |

## Verification

1. Title describes what was *actually* discussed, free of clickbait
2. "At a Glance" delivers the core argument in 30 seconds
3. Chapter timestamps match the video — spot-check one
4. Low-confidence segments reviewed (2-3 spot-checks, GPU path)
5. Filename uses AI-authored title (sanitized), not YouTube title
6. No promotional content
7. Speaker bio/backstory at the end, not in the introduction

## Pitfalls

| Problem | Fix |
|---|---|
| `pkg_resources` missing (Python 3.13+) | `pip install "setuptools<68" && pip install openai-whisper --no-build-isolation` |
| cublas64_12.dll not found | `pip install torch --index-url https://download.pytorch.org/whl/cu128` |
| whisper.cpp build fails (ARM clang segfault) | `cmake -DCMAKE_C_FLAGS="-march=armv8-a" -DCMAKE_CXX_FLAGS="-march=armv8-a"` |
| whisper.cpp hangs (OpenMP on Termux) | Always `-DGGML_NO_OPENMP=ON` on Android |
| CPU transcription too slow (openai-whisper) | Switch to whisper.cpp — 3-5× realtime on ARM |
| yt-dlp DRM block | Update yt-dlp; if still blocked, skip |
| Audio duration mismatch (ffmpeg) | Display artifact — WAV contains full audio; verify with ffprobe |
| Filename OSError (Windows) | Always run `sanitize_filename()` before writing |
| Non-English curation quality | Note detected language in header; lighter curation touch |
