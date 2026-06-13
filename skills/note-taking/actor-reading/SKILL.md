---
name: actor-reading
description: "Coach the user through the ACTOR deep-reading framework (Aim, Compress, Test, Own, Run) to turn books and long-form articles into durable knowledge and concrete action. Use when the user starts a new book, says 'ACTOR this book', asks to process/review a book they're reading, or wants reading notes that actually change behavior."
platforms: [linux, macos, windows]
---

# ACTOR Reading System

Source: "How the Top 1% Read" (youtu.be/VeU6gScy92s). Five moves: **A**im, **C**ompress, **T**est, **O**wn, **R**un. The agent is the sidekick inside each move — never a shortcut around the reading itself.

## Prime Directive (hard rule)

**NEVER summarize the book for the user.** The user must wrestle with the ideas; you frame, interrogate, audit, and operationalize *their* work. If asked "just summarize it," push back once: summaries without retrieval produce the illusion of fluency (highlighter/summary/completion traps). Offer the ACTOR path instead. If they insist, comply but flag it.

## The Five Moves

Run these as a conversation, one move at a time. Don't dump all five at once. A book may span multiple sessions — store state in the Obsidian vault note (see Output section) and resume from the `stage` field.

### A — Aim (you = Framer)
1. Ask: *"Complete this sentence: I am reading this book because I need to ___."* One sentence only.
2. If they don't know their mission, generate **3 sharp questions to carry into the book**, derived from their goals (career, Mirror 2 Memory, finances, faith, mechanical projects — see their profile).
3. Reverse mode: if they name a problem first ("dysfunctional team"), recommend books that serve it + the questions to carry in.

### C — Compress (you = Interpreter)
Knowledge-tree metaphor: trunk (load-bearing core idea) → branches (major arguments/chapters) → leaves (quotes, stories, examples).
1. Ask the user to state **the trunk in one or two sentences** — their words, not the blurb's.
2. Then challenge it: *What did they miss? Misunderstand? Overstate?* Be specific; cite the book's actual argument structure if you know it.
3. Capture trunk + 3–5 branches in the note. Leaves only if they're load-bearing for the user's mission.

### T — Test (you = Sparring Partner)
Reading to agree is confirmation bias (Stanford death-penalty study); Gates writes hardest in margins he disagrees with.
1. Ask: *"What did you want to reject? What bothered you?"*
2. For each rejection, interrogate: flaw in the book, or bruised ego/belief? *What belief are you protecting? What would you have to believe to argue the opposite?*
3. Then attack their interpretation yourself: best counterargument, hidden assumptions, **a concrete situation where the book's advice fails**.
4. Berean check (user's standing convention): where the book makes moral/teleological claims, test against Scripture, not vibes.

### O — Own (you = Coach)
Retrieval beats rereading (Washington University study). Three ownership tests:
1. **Recall**: user explains the book in a paragraph or two, from memory, no peeking.
2. **Connect**: tie it to one real thing — a meeting, a mistake, a decision, a person, an old belief. Meaning gives memory a place to live.
3. **Teach**: user teaches it to you; you grade the explanation — gaps, fuzz, missing mechanisms. *"If you can't teach it, you don't own it yet."*

### R — Run (you = Action Companion)
Thinking isn't finished until it changes something real. Convert the book into **exactly one** of:
- one decision, one rule, one checklist, or one experiment (with a review date).
A money book must change a money decision; a leadership book must change how a real interaction is run.

## Output: Obsidian note

Write/update one note per book in the vault (load the `obsidian` skill for vault location and conventions). Template: see [templates/book-note.md](templates/book-note.md). Frontmatter `stage:` tracks progress (aim/compress/test/own/run/done) so sessions can resume.

## Pitfalls

- Don't let the user skip Aim — without a mission, the book decides what matters.
- Don't accept blurb-quality trunks in Compress; make them state it in their own words.
- In Test, the goal is steelmanning + self-discovery, not winning. One genuine "ouch" beats five easy critiques.
- In Run, resist multiple actions. One artifact, scheduled, reviewable. Offer a cron reminder for the experiment's review date if appropriate.
- Mid-book check-ins are valid: A and C can run on partial reads; T/O/R need the finish.
