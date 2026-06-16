---
name: vidnote
description: "One-command fused pipeline: download video → extract frames (scene detection) → transcribe → vision analysis → fused report → save to Obsidian. Chains watch-video + yt-transcribe, eliminating duplicate download/convert stages."
version: 1.0.0
category: media
metadata:
  hermes:
    tags: [youtube, video, transcription, pipeline, automation, obsidian]
  related_skills:
    - watch
    - scribe
    - obsidian
---

# Watch → Notes Pipeline

One command to watch a video and produce structured notes. Chains `watch-video` (frames + vision) and `yt-transcribe` (audio + curation) into a single workflow, eliminating duplicate stages.

**When to use:** Tutorials with on-screen code, lectures with slides, presentations where BOTH what was said AND what was shown matter. Not for audio-only — use `yt-transcribe` directly. Not for visual-only analysis — use `watch-video` directly.

## Quick Reference (Run This)

```bash
URL="https://youtu.be/VIDEO_ID"

# 1. ACQUIRE — download once (video for frames, extract audio)
yt-dlp -f "best[height<=720][ext=mp4]/best[height<=720]/best" -o "video.mp4" "$URL"
ffmpeg -i "video.mp4" -ar 16000 -ac 1 -sample_fmt s16 "audio_16k.wav" -y
METADATA=$(yt-dlp --print "%(title)s -- %(uploader)s -- %(duration)s" "$URL")

# 2. DRY-RUN — preview frame count, tune threshold
python3 ~/.hermes/skills/watch-video/scripts/extract_frames.py video.mp4 /tmp/dry/ \
  --dry-run --threshold 0.3

# 3. EXTRACT FRAMES — scene detection
python3 ~/.hermes/skills/watch-video/scripts/extract_frames.py video.mp4 frames/ \
  --threshold 0.3 --output-json frames.json

# 4. TRANSCRIBE — CPU (whisper.cpp) or GPU (openai-whisper)
# CPU:
~/whisper.cpp/build/bin/whisper-cli -m ~/whisper.cpp/models/ggml-base.en.bin \
  -f "audio_16k.wav" -l en -otxt -osrt -of "transcript"
# GPU: use whisper.load_model("turbo").transcribe("audio_16k.wav")

# 5. ANALYZE FRAMES — vision_analyze sampled frames (≤30 frames, batch 5-10)

# 6. FUSE — produce TWO outputs:
#    a) Curated transcript (yt-transcribe template — see that skill for content-type routing)
#    b) Visual timeline report (watch-video template — timestamps + frame descriptions)

# 7. SAVE — Obsidian
# skill_view('note-taking/obsidian')
# Save both notes: "{Title} -- Transcript.md" and "{Title} -- Visual Report.md"
# Cross-link them with [[wikilinks]]

# 8. CLEANUP
rm video.mp4 audio_16k.wav transcript.* raw_transcript.* 2>/dev/null
# Keep frames/ if useful for review
```

## Content-Type Routing

Before curating, classify the video using `yt-transcribe`'s content-type detection:

| Type | Curation Focus | Visual Report Priority |
|---|---|---|
| **Framework Talk** | Restructure around the model, not chronological order | High — diagrams and frameworks on screen are critical |
| **Tutorial / How-To** | Chronological with code blocks verbatim | Very High — every code change matters |
| **Sermon / Lecture** | Passage → exposition → application | Low-Medium — typically talking head, flag slides only |
| **Interview** | Thematic grouping with speaker labels | Low — faces talking, occasional B-roll |
| **Debate / Panel** | Position → counter-position → synthesis | Low — talking heads |

**Default threshold by content type:** Tutorial/code → 0.15, Framework/Slides → 0.2, Talking-head → 0.4.

## Obsidian Integration

Two linked notes per video:

```markdown
# {AI-Authored Title} — Transcript
**Source:** {URL} | **Duration:** {HH:MM:SS} | **Speaker:** {Uploader}
**Visual report:** [[{Title} — Visual Report]]

{Curated transcript content — see yt-transcribe Curator Templates}
```

```markdown
# {AI-Authored Title} — Visual Report
**Source:** {URL} | **Duration:** {HH:MM:SS} | **Speaker:** {Uploader}
**Transcript:** [[{Title} — Transcript]]
**Frames:** {N} via scene detection (threshold={X})

## Visual Timeline
| Timestamp | Frame | What's On Screen |
|---|---|---|
| ... | ... | ... |

## Key Visual Moments
{3-5 highest-information frames}
```

## Skill Delegation Map

| Stage | Skill | Why |
|---|---|---|
| Frame extraction | `watch-video` (extract_frames.py) | Scene detection, real timestamps |
| Transcription | `yt-transcribe` | Dual-path whisper, curation templates |
| Vision analysis | `vision_analyze` tool | Frame-by-frame descriptions |
| Curation | `yt-transcribe` (transcript) + `watch-video` (visual report) | Each owns its output format |
| Save | `obsidian` | Vault read/write/wikilinks |

## Pitfalls

| Problem | Fix |
|---|---|
| Duplicate download | Pipeline downloads video once, extracts audio via ffmpeg instead of separate yt-dlp audio download |
| Frame explosion on long tutorials | Use `--dry-run` first. For 2hr+ coding videos, start at `--threshold 0.25` |
| Vision API costs (both frames + transcript curation) | Sample frames to ≤20 for long videos. Skip visual report for talking-head content. |
| Whisper model mismatch | Check `whisper-cli` and model files exist before running |
