---
name: write-a-skill
description: Create new agent skills with proper structure, progressive disclosure, and bundled resources. Use when user wants to create, write, or build a new skill.
---

# Writing Skills

## Process

1. **Gather requirements** - ask user about:
   - What task/domain does the skill cover?
   - What specific use cases should it handle?
   - Does it need executable scripts or just instructions?
   - Any reference materials to include?

2. **Draft the skill** - create:
   - SKILL.md with concise instructions
   - Additional reference files if content exceeds 500 lines
   - Utility scripts if deterministic operations needed

3. **Review with user** - present draft and ask:
   - Does this cover your use cases?
   - Anything missing or unclear?
   - Should any section be more/less detailed?

## Skill Structure

```
skill-name/
├── SKILL.md           # Main instructions (required)
├── REFERENCE.md       # Detailed docs (if needed)
├── EXAMPLES.md        # Usage examples (if needed)
└── scripts/           # Utility scripts (if needed)
    └── helper.js
```

## SKILL.md Template

```md
---
name: skill-name
description: Brief description of capability. Use when [specific triggers].
---

# Skill Name

## Quick start

[Minimal working example]

## Workflows

[Step-by-step processes with checklists for complex tasks]

## Advanced features

[Link to separate files: See [REFERENCE.md](REFERENCE.md)]
```

## Description Requirements

The description is **the only thing your agent sees** when deciding which skill to load. It's surfaced in the system prompt alongside all other installed skills. Your agent reads these descriptions and picks the relevant skill based on the user's request.

**Goal**: Give your agent just enough info to know:

1. What capability this skill provides
2. When/why to trigger it (specific keywords, contexts, file types)

**Format**:

- Max 1024 chars
- Write in third person
- First sentence: what it does
- Second sentence: "Use when [specific triggers]"

**Good example**:

```
Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when user mentions PDFs, forms, or document extraction.
```

**Bad example**:

```
Helps with documents.
```

The bad example gives your agent no way to distinguish this from other document skills.

## When to Add Scripts

Add utility scripts when:

- Operation is deterministic (validation, formatting)
- Same code would be generated repeatedly
- Errors need explicit handling

Scripts save tokens and improve reliability vs generated code.

## When to Split Files

Split into separate files when:

- SKILL.md exceeds 100 lines
- Content has distinct domains (finance vs sales schemas)
- Advanced features are rarely needed

## Token Efficiency (mandatory target)

User preference: skills must be token-dense — no filler, no redundancy, no essay sections. Target ≤8 KB for even complex skills. Techniques proven across multiple skill rewrites:

| Technique | Example | Reduction |
|---|---|---|
| **Quick Reference format** | Pipeline stages → single bash block with numbered comments | Collapses 7 verbose stage sections into 1 block |
| **Adaptive templates** | 6 near-identical curator templates → 1 universal rules list + routing table showing only type-specific differences | 66 rule statements → 6 universal + 6×3 cell table |
| **Problem/Fix tables** | 10 verbose Pitfall subsections → `\| Problem \| Fix \|` table | ~1,200 chars → ~400 |
| **Core Concepts tables** | 5 exposition paragraphs explaining theory → `\| Concept \| Rule \|` table | ~2,000 chars → ~600 |
| **Merge overlapping lists** | "Rationalizations" table (11 rows) + "Red Flags" list (12 items) with 90% semantic overlap → one 7-row table | ~2,400 chars → ~800 |
| **Cut filler sections** | "Why Order Matters" (5 straw-man rebuttals), "Hermes Agent Integration" (agents know their own tools), "See Also" (use `skills_list`), "Real-World Impact" (marketing) | Zero information loss — all cut content is either redundant or tool-trivial |

**Structure rules for new skills:**
1. Frontmatter → 2-line intro → Quick Reference (the pipeline) → reference tables → pitfalls table → verification checklist. That order.
2. If a skill has >2 near-identical variants (templates, paths, modes), use ONE canonical version + a routing/difference table. Never repeat full blocks.
3. Every paragraph must survive the test: "Does this tell the agent something the table/Quick Reference didn't already convey?"
4. Prefer tables over prose. Prefer bullets over paragraphs. Prefer one code block over many.
5. The "SKILL.md under 100 lines" rule is secondary to token density. A 145-line skill at 5.9 KB beats a 100-line skill at 15 KB.

## Designing for Effectiveness (protocol over prose)

A skill is effective in proportion to how little it leaves to the executing agent's discretion. Philosophy/doctrine sections set direction, but only protocol produces repeatability. When writing or improving a skill that governs recurring stateful work:

1. **Canonical loop first.** Put a numbered, ordered session protocol at the TOP of SKILL.md ("run this FIRST, every session, in order"). Doctrine goes below it. Without the loop, rules are orphaned; with it, every rule has a home (a step where it fires).
2. **Quantified triggers.** Rules without observable thresholds are dead code. "When the user approaches competence" never fires; "3 consecutive retrieval passes" does. Every conditional rule needs a numeric/observable condition.
3. **Dedicated state file.** If the skill tracks anything across sessions (scores, statuses, deadlines), give quantitative state its own structured file (e.g. LEDGER.md with tables), separate from qualitative notes/records. One read = all state. Never scatter tracking fields across N record files, and never let prose scratchpads carry parseable state.
4. **Definition of done.** Work items need explicit closure states with mechanical transitions (e.g. active → review → closed), or the workspace accumulates forever. Closure should produce an artifact (reference doc) and retire the item from active rotation.
5. **One-line scoreboard.** End each protocol run by rendering measurable state in one line. You can't steward what you don't measure.

When improving an existing skill: rank-order candidate fixes by "discretion reduced per unit of text added" and implement the most upstream one first (the one others depend on) — the skeleton before the organs.

## Pitfalls

- **Patching skills in categorized or external dirs**: `skill_manage(action='patch')` may fail with "not found" for skills addressed by path (e.g. `.agents/skills/teach`) or when names collide across dirs. Workaround: call `skill_view` to get the absolute `path` field, then use the generic `patch` tool directly on that file path.
- **Verify before diagnosing "missing files."** Before claiming a skill lacks templates/references, list its directory (`search_files` target='files' on the skill_dir). Asserting gaps from inference instead of inspection wastes a patch cycle on the wrong problem.
- **Respect the existing format's philosophy when extending.** If a skill's record format says "not a journal," don't bolt tracking fields onto it — add a separate artifact that preserves the original separation of concerns.

## Review Checklist

After drafting, verify:

- [ ] Description includes triggers ("Use when...")
- [ ] SKILL.md under 100 lines
- [ ] No time-sensitive info
- [ ] Consistent terminology
- [ ] Concrete examples included
- [ ] References one level deep
