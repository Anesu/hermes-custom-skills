---
name: debug
description: "4-phase root cause debugging: understand bugs before fixing."
version: 1.2.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
    related_skills: [tdd, plan, subagent-driven-development]
---

# Systematic Debugging

## Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

Random fixes waste time, create new bugs. Symptom fixes are failure. Complete each phase before proceeding.

## When to Use

Any technical issue (test failures, bugs, unexpected behavior, performance, builds). **Especially** under time pressure, when "one quick fix" seems obvious, after multiple failed fixes, or when you don't fully understand the issue.

## The Four Phases

| Phase | Key Activities | Success Criteria |
|---|---|---|
| **1. Root Cause** | Read errors completely, reproduce consistently, check recent changes (`git log`, `git diff`), trace data flow upstream to source | Understand WHAT and WHY |
| **2. Pattern** | Find working examples in same codebase, compare against references, list every difference | Know what's different |
| **3. Hypothesis** | State: "I think X is root cause because Y." Test with SMALLEST possible change. One variable at a time. | Confirmed or new hypothesis |
| **4. Implementation** | Write failing regression test, fix root cause (one change), verify (`pytest tests/ -q`) | Bug resolved, all tests pass |

### Phase 1 Detail: Root Cause Investigation

1. **Read error messages** — don't skip. Stack traces, line numbers, error codes often contain the solution.
2. **Reproduce consistently** — exact steps. Not reproducible → gather more data, don't guess.
3. **Check recent changes** — `git log --oneline -10`, `git diff`.
4. **Multi-component systems:** instrument each boundary — log data in/out per component. Find WHERE it breaks, then investigate that component.
5. **Trace data flow** — where does the bad value originate? Keep tracing upstream to the source. Fix at source, not symptom.

### Phase 4 Detail: The Rule of Three

- **< 3 fixes failed:** Return to Phase 1 with new information.
- **≥ 3 fixes failed: STOP. Question the architecture.** Pattern: each fix reveals new shared state/coupling; fixes require "massive refactoring"; each fix creates new symptoms. Discuss architectural refactor with user before attempting more fixes.

## Rationalizations vs. Reality

| If you think... | Reality |
|---|---|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast either way. |
| "Emergency, no time" | Systematic is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from start. |
| "I'll write test after confirming fix" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern. |

## Red Flags — STOP, Return to Phase 1

"Quick fix now, investigate later." "Just try changing X." "Add multiple changes." "Skip the test." "It's probably X." "I don't fully understand but this might work." Proposing solutions before tracing data flow. **If 3+ fixes failed: question architecture, don't fix again.**

## Verification

- [ ] Root cause identified and understood (not just symptoms)
- [ ] Issue reproduced consistently
- [ ] Regression test written and fails (proves the bug)
- [ ] Single fix applied at root cause
- [ ] Regression test passes + full suite clean
- [ ] No "while I'm here" changes bundled in

## Anti-Patterns

- Guessing fixes without investigation
- Fixing at symptom level (where error surfaces) instead of source
- Bundling multiple changes — can't isolate what worked
- Skipping regression test — bug will return
