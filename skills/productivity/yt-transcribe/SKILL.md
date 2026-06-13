---
name: yt-transcribe
description: "Download YouTube audio, transcribe with Whisper Turbo, curate into polished markdown with AI-authored title. Full pipeline: yt-dlp → ffmpeg → whisper → curation → .md. Includes chapter timestamps, confidence flagging, adaptive curation, filename sanitization, language auto-detect, and dry-run mode."
version: 3.0.0
category: productivity
metadata:
  hermes:
    tags: [youtube, transcription, whisper, ffmpeg, markdown, audio, curation]
---

# YouTube Transcription + Curation Pipeline

Download any YouTube video's audio, transcribe it with OpenAI Whisper (Turbo by default), then **curate** the output — not just proofread. The AI acts as an editor: it authors a substantive title (discarding YouTube clickbait), reorganizes content around the core argument, adds chapter timestamps, flags low-confidence segments, and produces a navigable, polished markdown document.

## When to Use

- Transcribing lectures, talks, podcasts, or sermons from YouTube
- Creating searchable, well-organized notes from video content
- Any time you need a *curated* transcript — not a raw stenography dump

## Philosophy: Stenographer → Editor

YouTube titles are engineered for clicks, not accuracy. A talk titled "This ONE Trick Changed My Life" might actually be a 20-minute exposition on first-principles reasoning. The AI's job is to:

1. **Read the content** and determine what was *actually* discussed
2. **Author a title** that accurately describes the substance
3. **Restructure** around the core framework, not the speaker's chronological delivery order
4. **Add editorial value** — pull quotes, summary tables, chapter timestamps, "Why This Matters" framing
5. **Flag uncertainty** — surface low-confidence segments for human review
6. **Trim** — remove promotional plugs, repetition, tangents that don't serve the argument

The original YouTube title is preserved as metadata only.

## Prerequisites

```bash
# Core tools
yt-dlp --version       # ≥ 2025.08 (update with yt-dlp -U)
ffmpeg -version        # any recent build

# Python packages (CUDA GPU strongly recommended)
uv pip install openai-whisper torch --index-url https://download.pytorch.org/whl/cu128
# Verify CUDA:
python -c "import torch; print(torch.cuda.is_available())"  # must be True
```

**GPU requirement:** Whisper Turbo on CPU is ~32x slower. On RTX 3090: ~32x realtime (20 min audio in ~37s). On CPU: expect 5-10 min for the same file.

## Pipeline (7 Stages)

### Stage 0 (Optional): DRY RUN — Validate Before Committing

For videos over 10 minutes, run a pre-flight check to avoid wasting GPU time on doomed runs:

```bash
# 1. Metadata only — verify the video is accessible
yt-dlp --print "%(title)s -- %(uploader)s -- %(duration)s" "URL"

# 2. Sample 30 seconds of audio and test-transcribe
yt-dlp -f "bestaudio[ext=m4a]/bestaudio" \
  --postprocessor-args "-ss 00:01:00 -t 30" \
  -o "sample.%(ext)s" "URL"
ffmpeg -i "sample.m4a" -ar 16000 -ac 1 -sample_fmt s16 "sample_16k.wav" -y
python -c "
import whisper, time
m = whisper.load_model('turbo')
t0 = time.time()
r = m.transcribe('sample_16k.wav', language=None, verbose=False)
elapsed = time.time() - t0
full_est = elapsed * (FULL_DURATION / 30)
print(f'Sample OK. Estimated full transcription: {full_est:.0f}s')
"
rm sample.m4a sample_16k.wav
```

If the sample fails (CUDA error, model not cached, DRM block), fix the issue before running the full pipeline.

### Stage 1: ACQUIRE — Download Audio + Provisional Metadata

```bash
# Download best audio
yt-dlp -f "bestaudio[ext=m4a]/bestaudio" \
  -o "/path/to/output/%(title)s.%(ext)s" \
  "https://www.youtube.com/watch?v=VIDEO_ID"

# Capture provisional metadata (YouTube title is NOT the final title)
yt-dlp --print "%(title)s -- %(uploader)s -- %(duration)s" "URL"
```

**Fallbacks if DRM blocks:**
- Update yt-dlp first: `yt-dlp -U`
- If still blocked, the video is truly DRM-protected — report and skip.

**The YouTube title is provisional.** It's captured for reference but will be replaced by an AI-authored title in Stage 5.

### Stage 2: CONVERT — 16kHz Mono WAV

Whisper models expect 16kHz mono 16-bit PCM WAV. Convert with ffmpeg:

```bash
ffmpeg -i "input.m4a" -ar 16000 -ac 1 -sample_fmt s16 "output_16k.wav" -y
```

Always use a short, ASCII-safe filename for the WAV to avoid path escaping issues with ffmpeg on Windows.

### Stage 3: TRANSCRIBE — Whisper Turbo (with Confidence + Auto-Detect)

```python
import whisper
import json

model = whisper.load_model("turbo")  # or "large-v3", "small", "medium"

# language=None enables auto-detection
result = model.transcribe(
    "audio_16k.wav",
    language=None,          # Auto-detect — removes the English-only hardcode
    verbose=False,
    word_timestamps=False
)

detected_lang = result["language"]
print(f"Detected: {detected_lang} (non-English may affect curation quality)")

# Save raw transcript WITH confidence scores
with open("raw_transcript.json", "w", encoding="utf-8") as f:
    json.dump(result["segments"], f, indent=2, default=str)

# Also save human-readable version
with open("raw_transcript.txt", "w", encoding="utf-8") as f:
    for seg in result["segments"]:
        conf = seg.get("confidence", seg.get("avg_logprob", None))
        f.write(f"[{seg['start']:.1f}s -> {seg['end']:.1f}s] (conf={conf:.2f}) {seg['text'].strip()}\n")

# Identify low-confidence segments for flagging
LOW_CONF_THRESHOLD = 0.75  # tune up/down based on model
low_conf = [s for s in result["segments"] if s.get("confidence", s.get("avg_logprob", 0)) < LOW_CONF_THRESHOLD]
if low_conf:
    print(f"⚠️  {len(low_conf)} low-confidence segments flagged for review")
```

**Model selection guide:**

| Model | Size | Speed (RTX 3090) | Accuracy | Best For |
|-------|------|-------------------|----------|----------|
| `turbo` | 809M | ~32x realtime | Excellent | Default — fast + accurate |
| `large-v3` | 1.5B | ~16x realtime | Best | Highest accuracy, rare terms, non-English |
| `small` | 244M | ~60x realtime | Good | Quick drafts, dry runs |
| `medium` | 769M | ~40x realtime | Very Good | Balanced alternative |

**Language auto-detection behavior:**
- If detected language ≠ English: proceed with transcription, but note in the output that curation quality may be reduced
- If detected language confidence < 0.8: flag for human verification
- Non-English transcripts still get curated, but the curator should note language limitations

### Stage 4: READ — Absorb + Classify the Raw Transcript

Before editing, read the full raw transcript. Identify:

- **The core argument** — what is the speaker actually trying to say? What's the framework, thesis, or model?
- **The content type** — classify into one of the structural templates below. This determines the curation strategy.
- **The natural divisions** — where do conceptual breaks occur? These may NOT match the speaker's delivery order.
- **The best lines** — what sentences deserve to be pull quotes?
- **What to cut** — promotional plugs, "like and subscribe," repetitive examples, tangents
- **Low-confidence segments** — review the flagged segments from Stage 3. Are they hallucinated? Fix or annotate.

#### Content Type Detection (Determines Curation Template)

Read the transcript and classify into ONE of these types. The curation structure adapts accordingly:

| Type | Signature | Curation Strategy |
|------|-----------|-------------------|
| **Framework Talk** | Presents a model, taxonomy, or system (e.g., "four types of X," "the three principles of Y") | Framework-first: lead with the model, use stories as illustrations, "At a Glance" table |
| **Interview / Conversation** | Multiple speakers, Q&A rhythm, back-and-forth exchanges | Thematic grouping: cluster exchanges by topic, not chronology. Speaker labels preserved. |
| **Sermon / Lecture** | Single speaker, expositional, scripture/text-anchored, application at the end | Passage → exposition → application. Keep the interpretive flow. |
| **Tutorial / How-To** | Step-by-step instruction, numbered sequence, "first do X, then Y" | Chronological with numbered steps. Code blocks or terminal commands preserved verbatim. |
| **Narrative / Story** | Personal journey, no explicit framework, emotional arc | Chronological with thematic headers. Pull quotes for emotional beats. |
| **Debate / Panel** | Opposing views, rebuttals, moderated discussion | Position → counter-position → synthesis. Preserve the tension. |

**If uncertain between types, default to Framework Talk** — it's the most common for long-form YouTube content and produces the most readable output.

### Stage 5: CURATE — Apply the Adaptive Template

This is the core of the pipeline. The AI acts as an **editor**, not a proofreader. Follow the curator prompt template for the detected content type.

#### Curator Prompt Template (Adaptive)

Load the template matching the content type from Stage 4:

---

**FRAMEWORK TALK template** (use when: speaker presents a model/taxonomy/system):

```
You are curating a transcript of a framework talk. Apply these rules in order:

1. TITLE: Write a substantive title naming the framework. No clickbait. No ALL CAPS.
2. CHAPTERS: Map each major section to a timestamp. Format as a table: | Timestamp | Section |
3. AT A GLANCE: Front-load the framework as a summary table or bullet list. Reader must get the argument in 30 seconds.
4. WHY THIS MATTERS: 2-3 sentences of editorial framing.
5. BODY: Present each component of the framework as a section. Lead with the concept, then use the speaker's stories/analogies as illustrations. Do NOT follow chronological delivery order.
6. PULL QUOTES: Exactly one > blockquote per major section. Choose the most quotable line.
7. HOW TO APPLY: Extract any diagnostic tool, checklist, or method.
8. THE TRAP: If the talk has a meta-insight (e.g., "seeing your own system"), give it its own section.
9. ABOUT THE SPEAKER: Personal narrative at the end. Context, not argument.
10. LOW CONFIDENCE: Append a "⚠️ Segments for Review" section listing flagged timestamps with text and confidence scores.
11. TRIM: Remove newsletter plugs, "like and subscribe," repetitive examples.
```

---

**INTERVIEW template** (use when: multiple speakers, Q&A rhythm):

```
You are curating a transcript of an interview/conversation. Apply these rules in order:

1. TITLE: "{Guest Name} on {Core Topic}" or the most substantive quote from the conversation.
2. CHAPTERS: Map each thematic section to a timestamp.
3. AT A GLANCE: 3-5 bullet points — the key claims or insights from the conversation.
4. BODY: Group exchanges by topic, not chronology. Each section = one topic cluster with relevant Q&A pairs. Preserve speaker labels (Host: / Guest:).
5. PULL QUOTES: One standout quote per topic section.
6. KEY TAKEAWAYS: Bullet list at the end synthesizing the conversation.
7. LOW CONFIDENCE: Flagged segments appendix.
8. TRIM: "Thanks for having me," throat-clearing, excessive banter that doesn't advance the topic.
```

---

**SERMON / LECTURE template** (use when: expositional, scripture/text-anchored, single speaker):

```
You are curating a transcript of a sermon or lecture. Apply these rules in order:

1. TITLE: "{Passage/Text Reference}: {Core Message}" — substantive and specific.
2. CHAPTERS: Timestamp map.
3. AT A GLANCE: The passage reference, the main point, and the application in 2-3 lines.
4. BODY: Passage/Text → Exposition (what it means) → Application (what to do). Preserve the interpretive flow. Scripture quotations in > blockquotes.
5. PULL QUOTES: The central exhortation or interpretive insight.
6. LOW CONFIDENCE: Flagged segments appendix.
7. TRIM: Extended anecdotes that don't serve the exposition. Keep illustrations that illuminate the text.
```

---

**TUTORIAL / HOW-TO template** (use when: step-by-step instruction):

```
You are curating a transcript of a tutorial. Apply these rules in order:

1. TITLE: "How to {Goal}: {Method}" — descriptive and searchable.
2. CHAPTERS: Timestamp map.
3. AT A GLANCE: The end result (what you'll have built/learned) + prerequisites.
4. BODY: Chronological with numbered steps. Code blocks, terminal commands, and config files preserved verbatim in ``` fences. Each step = one section with explanation + code.
5. PULL QUOTES: Key warnings or "gotcha" moments as > blockquotes.
6. LOW CONFIDENCE: Flagged segments appendix — especially important for code/commands.
7. TRIM: "Smash that like button," channel promos. Keep setup/context if it explains why.
```

---

**NARRATIVE / STORY template** (use when: personal journey, no explicit framework):

```
You are curating a transcript of a narrative/story. Apply these rules in order:

1. TITLE: The emotional or thematic core in one line. Not clickbait, but can be evocative.
2. CHAPTERS: Timestamp map.
3. AT A GLANCE: The arc in 3-4 beats — where it starts, the turn, where it lands.
4. BODY: Chronological with thematic section headers. Preserve the narrative flow — do not front-load a framework that doesn't exist.
5. PULL QUOTES: Emotional peaks and turning points as > blockquotes.
6. ABOUT THE SPEAKER: Brief context at the end (if not already obvious from the story).
7. LOW CONFIDENCE: Flagged segments appendix.
8. TRIM: Tangents that break narrative momentum.
```

---

**DEBATE / PANEL template** (use when: opposing views, rebuttals, moderated):

```
You are curating a transcript of a debate or panel. Apply these rules in order:

1. TITLE: "{Topic}: {Position A} vs. {Position B}" or the central contested question.
2. CHAPTERS: Timestamp map by topic/round.
3. AT A GLANCE: The motion/question + each side's core claim in one sentence.
4. BODY: Per-topic sections with Position → Counter-Position → Rebuttal → (if present) Synthesis. Preserve speaker labels.
5. PULL QUOTES: The strongest formulation of each side's argument.
6. LOW CONFIDENCE: Flagged segments appendix.
7. TRIM: Moderator throat-clearing, procedural exchanges, audience applause breaks.
```

---

#### Post-Curation Steps (All Types)

After applying the template:

1. **Map chapter timestamps** — for each section header, find the corresponding timestamp in the raw transcript. Format as `HH:MM:SS` (YouTube auto-links these).
2. **Flag low-confidence segments** — append a `⚠️ Segments for Human Review` section at the bottom with timestamp, transcribed text, and confidence score.
3. **Sanitize the filename** (see Stage 6).
4. **Run the verification checklist** (see Verification section).

### Stage 6: SAVE — Sanitized Filename + Cleanup

```python
import re

def sanitize_filename(title: str) -> str:
    """Replace characters illegal in Windows filenames with em-dash."""
    return re.sub(r'[<>:"/\\|?*]', '—', title)

safe_title = sanitize_filename(f"{curated_title} -- {uploader}")
# safe_title is now filesystem-safe on Windows, macOS, and Linux
```

```bash
# Save the curated markdown
# Filename: {sanitized AI-authored title} -- {Speaker Name}.md

# Remove intermediate files:
rm audio_16k.wav input.m4a raw_transcript.txt raw_transcript.json sample.m4a sample_16k.wav 2>/dev/null
```

**Naming convention:** Use the **AI-authored title**, sanitized for filesystem safety, not the YouTube title. The filename is `{Sanitized Curated Title} -- {Uploader}.md`.

### Stage 7: VERIFY — Post-Curation Checklist

After saving, run through this checklist:

1. **The title test** — does the title describe what was actually discussed? Is it free of clickbait?
2. **The 30-second test** — can a reader get the core argument from "At a Glance" alone?
3. **Chapter timestamps** — do the timestamps in the chapter index match the video? Click one to verify.
4. **Low-confidence review** — spot-check 2-3 flagged segments against the original audio. Fix or annotate.
5. **Filename** — uses the AI-authored title (sanitized), not the YouTube title.
6. **No promotional content** — newsletter plugs, "like and subscribe" are cut or footnoted.
7. **Personal narrative placement** — speaker's bio/backstory is at the end, not in the introduction.

## Curatorial Principles (Quick Reference)

When curating, apply these heuristics regardless of content type:

| Principle | Rule |
|---|---|
| **Framework first** | If the talk has a model/framework/system, lead with it. Stories are illustrations. |
| **Personal narrative last** | The speaker's bio/backstory is context, not argument. Move it to the end. |
| **One idea per section** | Each markdown section should make one point, supported by the best available story/analogy. |
| **Cut the ask** | Remove promotional content. If the speaker is genuinely insightful, footnote it at most. |
| **The 30-second test** | The "At a Glance" section should give a reader the entire argument in 30 seconds. |
| **Title must be true** | If someone read only the title, they should know what the piece is actually about. |
| **Flag uncertainty** | Low-confidence segments get their own appendix. Don't silently publish Whisper's guesses. |
| **Timestamps are navigational** | Chapter timestamps let readers jump to sections in the YouTube video. They're not decorative. |

## Pitfalls

### brotli Decoding Error on Model Download
```
httpx.DecodingError: brotli: decoder process called with data when 'can_accept_more_data()' is False
```
**Fix:** `uv pip install brotli` (replaces brotlicffi).

### cublas64_12.dll Not Found
```
RuntimeError: Library cublas64_12.dll is not found or cannot be loaded
```
**Fix:** Install PyTorch with CUDA support: `uv pip install torch --index-url https://download.pytorch.org/whl/cu128`. The CPU-only wheel ships without CUDA libraries.

### yt-dlp DRM Protection
Some YouTube videos are DRM-protected at the server level. yt-dlp will error with "This video is DRM protected." No workaround exists — flag and skip.

### Windows Path Issues with ffmpeg
MSYS/bash paths like `/c/Users/...` may fail with ffmpeg (Windows-native build). **Fix:** `cd` into the directory first and use relative filenames, or use Windows-style paths.

### CPU Transcription is Impractically Slow
A 20-minute video on CPU (int8) can exceed 5 minutes of processing time. Always verify CUDA is available before transcribing files over 5 minutes. Use the dry-run (Stage 0) to catch this early.

### Audio Duration Mismatch
ffmpeg may report a different duration than the original (e.g., 14:13 vs 19:56). This is a display artifact during conversion — the output WAV contains the full audio. Verify with `ffprobe` if concerned.

### Filename OSError on Windows
The AI-authored title may contain `:`, `/`, `\`, `?`, `*`, `<`, `>`, `|`, or `"` — all illegal in Windows filenames. **Fix:** Always run `sanitize_filename()` from Stage 6 before writing. A silent `OSError` after 5 stages of work is an embarrassing failure mode.

### Non-English Curation Quality
When language auto-detect fires for non-English content, the transcription will be accurate but the AI curator's restructuring may be less reliable (the editor doesn't understand the language). **Mitigation:** Note the detected language prominently in the output header and apply a lighter curation touch — fix Whisper errors and add timestamps, but don't restructure heavily.
