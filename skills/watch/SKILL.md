---
name: watch
description: "Watch YouTube videos with FFmpeg scene-detection frame extraction + transcript fusion. Analyzes both what was SAID and what was SHOWN. Produces a fused intelligence report; optionally saves to Obsidian."
version: 1.0.0
category: media
metadata:
  hermes:
    tags: [youtube, video, vision, ffmpeg, scene-detection, frames, transcript, obsidian, knowledge-base]
  related_skills: [yt-transcribe, obsidian]
---

# watch-video — Visual + Transcript Video Intelligence

Extract key frames via FFmpeg scene-change detection, pair with transcript, run vision analysis, produce fused report. **Not** for transcript-only curation — use `yt-transcribe` for that.

**Why scene detection over fixed-interval sampling:** 100 frames evenly spaced = 1 frame every 6 minutes on a 10hr video (blind). Scene detection captures a frame only when visual content *actually changes* — slides advancing, demos, motion graphics. Frame count adapts to content density, not video length.

Real timestamps via ffmpeg `showinfo` filter placed after `select` in the chain.

## Prerequisites

```bash
pkg install ffmpeg yt-dlp python           # core
pip install youtube-transcript-api          # fast transcript path (captioned videos)
# OR: whisper.cpp — see yt-transcribe skill  # any video, CPU/mobile
# Vision analysis: requires vision-capable model (provider-dependent)
```

## Quick Reference (Run This)

```bash
# 1. ACQUIRE
yt-dlp -f "best[height<=720][ext=mp4]/best[height<=720]/best" -o "watch_video.mp4" "URL"
yt-dlp --print "%(title)s -- %(uploader)s -- %(duration)s" "URL"  # metadata

# 2. DRY-RUN (tune threshold before extracting)
python3 ~/.hermes/skills/watch-video/scripts/extract_frames.py watch_video.mp4 /tmp/dry/ \
  --dry-run --threshold 0.3

# 3. EXTRACT FRAMES
python3 ~/.hermes/skills/watch-video/scripts/extract_frames.py watch_video.mp4 watch_frames/ \
  --threshold 0.3 --output-json frames.json

# 4. TRANSCRIBE
python3 ~/.hermes/skills/media/youtube-content/scripts/fetch_transcript.py "URL" \
  --text-only --timestamps > transcript.txt
# OR: skill_view('scribe') for whisper.cpp/openai-whisper

# 5. ANALYZE FRAMES — vision_analyze(image_url=frame_path, question="...")
#    Sample to ≤30 frames. Batch 5-10 per call. Describe code/diagrams/UI/slides visible.

# 6. FUSE — produce report (see template below)

# 7. SAVE — optional Obsidian via skill_view('note-taking/obsidian')
#    Naming: {Sanitized Title} -- {Uploader} -- Watch Report.md

# Cleanup
rm watch_video.mp4
```

## extract_frames.py Parameters

| Flag | Default | Purpose |
|---|---|---|
| `--threshold` / `-t` | 0.3 | Scene-change sensitivity. Lower = more frames. |
| `--max-frames` / `-m` | 100 | Hard cap. Exceeded → auto-tunes threshold +0.15 up to 4×. |
| `--scale` / `-s` | 640 | Resize width (height auto). |
| `--no-tune` | off | Disable auto-tuning. |
| `--dry-run` | off | Estimate count without extracting. Run before downloading large videos. |
| `--output-json` / `-o` | none | Save results to file instead of stdout. |

**Output JSON:** `video_path`, `video_duration_sec`, `threshold_used`, `frame_count`, `output_dir`, `frames[]` (each: `index`, `path`, `timestamp_sec`, `timestamp_display`, `filesize_bytes`).

## Content-Type Threshold Guide

| Content Type | Threshold | Reason |
|---|---|---|
| Talking head / interview | 0.4–0.5 | Cut only on B-roll; most frames identical |
| Slide presentation | 0.15–0.25 | Subtle text changes between slides |
| Coding tutorial / screen recording | 0.15–0.2 | Small pixel deltas; keystrokes matter |
| Cinematic / high-motion | 0.3–0.4 | Hard cuts obvious; avoid mid-transition |
| Whiteboard / drawing | 0.1–0.15 | Incremental hand-drawn changes |
| Unknown / mixed | 0.3 | Default — use `--dry-run` to preview |

## Fused Report Template

```markdown
# {AI-Authored Title}
**Source:** {URL} | **Duration:** {HH:MM:SS} | **Speaker:** {Uploader}

## At a Glance
- {Core argument in 2-3 sentences}
- {Key visual elements: slides, demos, diagrams}
- **Frames:** {N} via scene detection (threshold={X})

## Visual Timeline
| Timestamp | Frame | What's On Screen |
|---|---|---|
| 00:00 | frame_0001.jpg | Title card |
| 03:45 | frame_0012.jpg | Architecture diagram... |
| ... | ... | ... |

## Content Summary
{Section-by-section: what was said + what was shown}

## Key Visual Moments
{3-5 highest-information frames with paths}

## ⚠️ Limitations
- Timestamps from showinfo — accurate to frame precision
- Sub-second scene changes may be under-sampled (threshold-dependent)
- Vision model descriptions are interpretive
```

## Skill Integration

| Task | Delegates To |
|---|---|
| Audio pipeline | `yt-transcribe` (dual-path whisper CPU/GPU) |
| KB save | `obsidian` (vault read/write/wikilinks) |
| Vision analysis | `vision_analyze` tool |
| Curation | This skill (fused visual+audio output) |

## Pitfalls

| Problem | Fix |
|---|---|
| Frame explosion on long/dynamic videos | Auto-tuning handles this. Extreme: `--threshold 0.7 --no-tune` |
| Vision API token costs | Sample ≤30 frames. Scale width 480 for slide text. Skip Stage 4 if visuals are secondary. |
| Scene detection misses subtle changes | Lower threshold: `--threshold 0.15` for slides/code |
| Non-English content | Adjust vision analysis prompts to video's language |
| 720p downloads 500MB+ on mobile | Use `best[height<=360]` or `worst[ext=mp4]` for audio-only |

## Verification

1. Frame count reasonable (20-60 for 30min at threshold=0.3)
2. Spot-check 3 frames — distinct visual states at their timestamps
3. Transcript non-empty, correct language
4. Report visual timeline adds info beyond transcript alone
5. Cleanup: `rm watch_video.mp4`

## References

- `references/ffmpeg-showinfo-pattern.md` — showinfo filter technique, parser code, test video recipe
- `references/threshold-testing.md` — empirical calibration data per content type
