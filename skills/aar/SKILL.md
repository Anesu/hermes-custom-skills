---
name: aar
description: "Structured After-Action Review: intended vs. actual result, root cause of delta, sustain/improve actions. Military-grade debrief adapted for exercises, projects, sprints, and personal goals."
version: 1.0.0
category: self-development
metadata:
  hermes:
    tags: [aar, debrief, retrospective, review, military, project-management, post-mortem]
  related_skills:
    - debug
    - radar
---

# After-Action Review (AAR)

Structured debrief: what was supposed to happen → what actually happened → why the difference → what to do about it. Military origin, universal application.

## When to Use

- After a field exercise, training event, or operation
- Project post-mortem or sprint retrospective
- After a major decision or personal goal attempt (week/month/quarter review)
- Mirror 2 Memory retrospectives
- Any time an outcome didn't match intent and you need to extract lessons

## The Four Questions

Run these in order. No skipping. No rushing to solutions before understanding the delta.

### 1. What was supposed to happen?

State the intended outcome with precision. Include:
- **Objective:** What was the goal? (measurable, time-bound)
- **Plan:** What was the intended sequence of actions?
- **Assumptions:** What did we assume would be true? (terrain, resources, cooperation, timing)

### 2. What actually happened?

State the actual outcome without judgment or blame. Include:
- **Result:** What was the actual outcome? (same metrics as the objective)
- **Sequence:** What actually occurred? (timeline of events)
- **Surprises:** What happened that nobody planned for?

### 3. Why the difference?

Root cause analysis. For EACH delta (positive and negative):
- **Direct cause:** What immediately caused the divergence?
- **Root cause:** What underlying condition made the direct cause possible? (five whys if needed)
- **Controllable vs. uncontrollable:** What could we have influenced? What was genuinely external?

**Positive deltas matter too.** A "lucky" success that you don't understand is a future failure waiting to happen.

### 4. What do we sustain? What do we improve?

| Category | Sustain (worked — keep doing) | Improve (didn't work — change) |
|---|---|---|
| **Planning** | | |
| **Preparation** | | |
| **Execution** | | |
| **Communication** | | |
| **Contingency** | | |

Each item: specific, owned by a person, with a deadline if actionable.

### 5. Dissemination (optional)

Who needs to know? Share lessons horizontally (peers) and vertically (leadership). Unshared lessons are lessons lost.

## Output Template

```markdown
---
type: aar
event: "{Exercise / Project / Goal}"
date: {YYYY-MM-DD}
participants: [{names}]
tags: [aar, {context-tags}]
---

# AAR: {Event Name} — {Date}

## Intended
- **Objective:** {measurable goal}
- **Plan:** {intended sequence}
- **Assumptions:** {what we assumed}

## Actual
- **Result:** {actual outcome, same metrics}
- **Sequence:** {what actually occurred}
- **Surprises:** {unexpected events}

## Delta Analysis
| Delta | Direct Cause | Root Cause | Controllable? |
|---|---|---|---|
| {+ or −} {what diverged} | {immediate reason} | {underlying reason} | {Yes/No/Partial} |

## Sustain / Improve
| Category | Sustain | Improve |
|---|---|---|
| Planning | {what to keep} | {what to change} |
| Preparation | | |
| Execution | | |
| Communication | | |
| Contingency | | |

## Action Items
- [ ] {action} — {owner} by {deadline}

## Lessons for Dissemination
- {lesson} — share with {audience}
```

## Integration

- **With `debug`:** AAR's "why the difference" maps to Phase 1 (root cause). Use debugging workflow if the delta is technical.
- **With `radar`:** The AAR itself requires active cognition — the radar should be on during the review. Don't passively fill out the template; interrogate each answer.
- **With Obsidian (`obsidian` skill):** Save AARs to vault. Cross-link with project notes, exercise logs, or goal-tracking pages via `[[wikilinks]]`.

## Pitfalls

| Problem | Fix |
|---|---|
| Blame-seeking instead of cause-seeking | Focus on systems and conditions, not individuals. "What made it rational for that person to do that?" |
| Skipping positive deltas | Success you don't understand is fragile. Analyze wins as rigorously as losses. |
| Vague sustain/improve items | "Communicate better" → "Weekly 15-min standup, Tuesdays 0900, owner: Smith" |
| Rushing to solutions before understanding | Don't propose fixes during question 2. Finish the delta analysis first. |
| Lessons die in the notebook | Disseminate. If nobody else learns, the same mistake happens again. |
