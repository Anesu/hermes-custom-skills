---
name: berean
description: "Inductive Bible study: Observation → Interpretation → Application. Genre-sensitive, cross-reference aware, Obsidian-native output. Integrates with meta-cognition Berean check."
version: 1.0.0
category: self-development
metadata:
  hermes:
    tags: [bible, scripture, study, inductive, hermeneutics, exegesis, obsidian, sola-scriptura]
  related_skills:
    - radar
    - obsidian
---

# Scripture Study — Inductive Method

Study any passage using Observation → Interpretation → Application. Genre-sensitive questions guide each phase. Scripture interprets Scripture via cross-references. Outputs structured Obsidian notes with `[[wikilinks]]`.

**Not a commentary.** The skill supplies the method, the text supplies the authority. You do the thinking — the agent frames the questions, surfaces parallels, and structures the output.

## When to Use

- Studying a passage for personal devotion or teaching prep
- Working through a book chapter-by-chapter
- Preparing a sermon, Bible study, or small group discussion
- Cross-referencing a topic across Scripture
- Any time the Berean check (meta-cognition Mode 3) is active and the material IS Scripture

## Prerequisites

- Obsidian vault with Bible notes (`skill_view('note-taking/obsidian')`)
- meta-cognition skill loaded if using Berean check during study

## Quick Reference

```
1. Select passage → identify pericope boundaries
2. Detect genre → load genre-specific Observation questions
3. OBSERVATION: what does the text say? (no interpretation yet)
4. INTERPRETATION: what did it mean to the original audience? Cross-reference.
5. APPLICATION: what does it mean for us? Bridge the gap.
6. Save to Obsidian with [[wikilinks]]
```

## Genre Detection

Classify the passage into ONE genre. Each has distinct Observation questions:

| Genre | Books/Examples | Key Observation Questions |
|---|---|---|
| **Narrative** | Gospels, Acts, OT history | Who are the characters? What is the setting? What conflict or tension drives the plot? Where is God/Christ in the story? What does the narrator emphasize or omit? |
| **Epistle** | Romans–Jude | What is the argument structure? (trace therefore/for/because) What problem is the author addressing? What commands follow from what doctrine? Where is the indicative→imperative pivot? |
| **Poetry / Wisdom** | Psalms, Proverbs, Job, Ecclesiastes, Song | What is the parallel structure? (synonymous/antithetic/synthetic) What emotion is expressed? What imagery/metaphor is used? Is this a promise, proverb (general truth), or lament? |
| **Prophecy** | Isaiah–Malachi, Revelation | What is the historical context? (pre-exile/exile/post-exile) Is there a near-fulfillment AND far-fulfillment? What covenant is referenced? What does this reveal about God's character/judgment/mercy? |
| **Law** | Exodus–Deuteronomy (legal sections) | What type of law? (moral/ceremonial/civil) What principle underlies the specific command? How does Christ fulfill or transform this? What does this reveal about God's holiness? |

**Default to Epistle** if the passage teaches doctrine; **Narrative** if it tells a story.

## Observation (What Does It Say?)

Answer WITHOUT interpretation. Stick to what's on the page.

1. **Context:** What comes immediately before and after? Where does this fit in the book's structure?
2. **Key words:** What terms repeat? What words carry theological weight? (Note original language if accessible — Greek/Hebrew via Strong's or interlinear.)
3. **Grammar:** Who is the subject? What are the verbs — commands, promises, warnings? Note conjunctions (therefore, but, for, if, so that).
4. **Structure:** How is the passage organized? Contrast, comparison, cause-effect, question-answer, climax?
5. **Quotations:** Does the passage quote or allude to OT texts? Flag for cross-reference.

## Interpretation (What Did It Mean?)

Bridge to the original audience. What did the author intend the original readers to understand?

1. **Author's intent:** Why did the author write THIS to THESE people at THIS time?
2. **Cross-reference:** Scripture interprets Scripture. Find parallel passages that illuminate this one:
   - Same author on same topic elsewhere
   - Same topic in a different genre
   - OT passages quoted or alluded to
   - Clear passages that interpret difficult ones (analogy of faith)
3. **Historical context:** What was happening in Israel/the church when this was written? What cultural assumptions did the original readers share?
4. **Theological synthesis:** What does this passage contribute to the whole counsel of Scripture on this topic? How does it point to Christ (Luke 24:27)?

## Application (What Does It Mean for Us?)

Bridge from then to now. The gap is real — don't collapse it.

1. **Identify the gap:** What's different between then and now? (culture, covenant, circumstance, audience)
2. **Find the principle:** What timeless truth transcends the cultural form?
3. **Personalize:** Is there a:
   - Sin to confess?
   - Promise to trust?
   - Command to obey?
   - Truth to believe?
   - Example to follow/avoid?
   - Warning to heed?
4. **Specificity:** "Be more loving" is a platitude. "Call my brother this week about the conflict from Tuesday" is application.

## Cross-Reference Workflow

```bash
# Search your existing Obsidian notes for cross-references
# Use the obsidian skill to search vault for verses/topics
skill_view('note-taking/obsidian')
# Then: search_files for verse references or topics in your vault

# For new cross-references, note them in the output with [[wikilinks]]
# e.g., "See also [[Romans 3 - Justification by Faith]]"
```

## Obsidian Output Template

```markdown
---
book: "{Book Name}"
chapter: {Chapter}
verses: "{Start}–{End}"
genre: "{Genre}"
date: {YYYY-MM-DD}
tags: [scripture, {book-tag}, {topic-tags}]
cross-refs: [{linked-note-refs}]
---

# {Book} {Chapter}:{Verses} — {Theme/Title}

## Observation
{Key words, structure, context, quotations}

## Interpretation
{Author's intent, cross-references, historical context, theological synthesis}

## Application
- Sin to confess:
- Promise to trust:
- Command to obey:
- Truth to believe:
- Example/Warning:

## Cross-References
- [[Passage A — Theme]]
- [[Passage B — Theme]]

## Key Verse
> {Most impactful verse from passage}

## Prayer / Response
{Personal response to the text}
```

## Integration with Meta-Cognition

When `meta-cognition` Mode 3 (Berean check) is active during study:
- The text IS the authority testing everything else — not the reverse
- Every interpretation must be accountable to the text
- Flag when your own preferences or cultural assumptions are driving the reading
- The radar catches when you're passively "reading" Scripture without engaging

## Pitfalls

| Problem | Fix |
|---|---|
| Skipping Observation → jumping to Application | Observation forces you to see what's there, not what you assume |
| Eisegesis (reading INTO the text) | Cross-reference before concluding. Let clear passages interpret difficult ones. |
| Ignoring genre | A proverb is not a promise. Apocalyptic is not epistle. |
| Collapsing the gap | "They were just like us" — no. Bridge honestly. |
| Proof-texting | One verse without context is a pretext. Trace the argument. |
| Neglecting OT context of NT passages | NT authors were OT-saturated. Find the reference. |
| Making everything about "me" | Ask: what does this reveal about GOD first? |
