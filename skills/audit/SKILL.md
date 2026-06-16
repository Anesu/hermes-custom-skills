---
name: audit
description: "Automated SKILL.md quality audit: size grading, table/prose ratio, bloat score, anti-pattern detection, required section checks. Run before committing skill changes or to audit the full skills directory."
version: 1.0.0
category: software-development
metadata:
  hermes:
    tags: [meta-skill, audit, quality, bloat-detection, token-efficiency]
---

# Skill Health Checker

Audit any SKILL.md for bloat and quality. Scores 0-100 (lower = leaner). Detects anti-patterns we just fixed across 5 skills.

## Quick Reference

```bash
# Audit a single skill
python3 ~/.hermes/skills/skill-health-checker/scripts/audit_skill.py watch-video

# Audit all skills, show top 10 worst offenders
python3 ~/.hermes/skills/skill-health-checker/scripts/audit_skill.py --all --top 10

# JSON output for programmatic use
python3 ~/.hermes/skills/skill-health-checker/scripts/audit_skill.py yt-transcribe --json
```

## Metrics

| Metric | Range | Description |
|---|---|---|
| **Size grade** | excellent / good / bloated / critical | <3KB excellent, 3-8KB good, 8-15KB bloated, >15KB critical |
| **Table/prose ratio** | 0.0–∞ | Higher = denser content. >0.5 is good. |
| **Required sections** | 0–5 | Pitfalls, verification, quick reference, prerequisites, parameters table |
| **Anti-pattern count** | 0–N | Repeated templates, rationale essays, integration filler, "See Also", marketing fluff |
| **Bloat score** | 0–100 | Composite. <25 lean, 25-50 moderate, 50-75 bloated, >75 critical |

## Anti-Patterns Detected

| Pattern | Why it's bloat |
|---|---|
| Repeated curator/instruction templates (>2) | Merge into one adaptive template + routing table |
| "Why Order Matters" style rebuttal section | The Iron Law already stated the rule |
| "Hermes Agent Integration" filler | Agents know their own tools |
| "Common Rationalizations" + separate "Red Flags" section | Overlapping content — merge into one table. A single consolidated Red Flags section WITHOUT a separate Rationalizations table is legitimate. |
| "See Also" section | `skills_list` handles discovery |
| "Real-World Impact" / marketing claims | "15-30 min vs 2-3 hours" — cut |
| Verbose description (>200 chars in frontmatter) | Tighten to one sentence |

## Output Format

```
BLOAT  GRADE     SIZE    SIZE_GRADE  RATIO  CHECKS  ANTI  SKILL
  85  critical   25847B  critical    0.31   4/5     [repeated_templates, ...]  yt-transcribe (pre-streamline)
  12  lean        7379B  good        0.85   4/5     [none]                     yt-transcribe (post-streamline)
  16  lean        5936B  good        1.10   5/5     [none]                     watch-video
  37  moderate    4507B  good        0.39   1/5     [red_flags]                test-driven-development
```

**Calibration note:** Scores were calibrated against a 5-skill streamlining pass (June 2026) that reduced 74KB → 27KB (63%) with zero content loss. A score of 12–40 with "good" size grade is a healthy, production-quality skill. Scores >50 with "bloated/critical" size grade warrant attention. See `references/streamlining-patterns.md` for the techniques used.

## Pitfalls

| Problem | Fix |
|---|---|
| Script can't find skill by name | Use full path or the skill's directory name exactly |
| False positives on anti-patterns | The patterns are regex-based. A skill might legitimately use "Red Flags" for non-bloat content. Triage manually. |
| JSON output is verbose | Pipe to `| python3 -m json.tool` or use `--top` for summaries |

## References

- `references/streamlining-patterns.md` — 7 proven patterns that delivered 65% reduction across 5 skills (Quick Reference, adaptive templates, Problem/Fix tables, etc.)
- `scripts/audit_skill.py` — the audit engine
