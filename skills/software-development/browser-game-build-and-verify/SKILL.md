---
name: browser-game-build-and-verify
description: Build a self-contained browser game or interactive canvas/JS widget from a design spec AND verify it by driving the real running app in a headless browser — not by asserting it works. Covers the spec-to-tiers workflow, the "factory + thin host/widget wrappers" structure that makes a host-bound widget verifiable, driving the game's state machine via the browser console + a debug `_api`, the console-eval single-line constraint, and post-build spec critique. Use whenever the task is "build me a game / interactive widget / canvas app from this spec" and the deliverable must actually run, especially when the real integration target (a Space widget, an embedded renderer) can't be executed directly in the agent's environment.
---

# Browser Game / Interactive Widget: Build and Verify

For tasks of the form "build a complete game / interactive canvas app / widget from this spec, see it to completion." The deliverable is a **running, verified artifact** — code that was actually loaded in a browser and driven through its states — not a plausible-looking file declared done.

## When to use
- User hands a design spec for a browser game, canvas app, or interactive widget and wants it built end-to-end.
- The real integration target is host-bound (a Space `renderWidget`, an embedded SDK renderer) that the agent CANNOT execute directly.
- "Complete" / "to completion" / "see it through" language — meaning verification is part of the job, not optional.

## Core principle: verify by driving, not by asserting
A browser game's correctness lives in its **state machine and collision/interaction logic**, which a static read can't confirm. The job is not done when the file is written; it's done when you have loaded it in a real browser, driven it through every state, and read **zero console errors** out of an actual run. Reporting "it should work" is the failure mode this skill exists to prevent.

## The workflow

### 1. Align on deliverable shape BEFORE writing 1000+ lines
State the two structural decisions up front and proceed on defensible defaults (don't block waiting):
- **Stack** — default to a single self-contained HTML5 Canvas + vanilla JS artifact (zero install, fully verifiable in-browser). Only deviate if the spec demands it.
- **Verifiability of a host-bound target** — see §2. This is the alignment call that lets you actually run the thing.

Build through the spec's milestones but commit as ONE coherent artifact when the user asked for "complete" (not piecemeal drops). Use a `todo` list mirroring the spec's milestone table.

### 2. The "factory + thin wrappers" structure (the key trick)
When the real target is a host-bound widget you can't execute (e.g. `async (parent, currentSpace, context) => {...}`), do NOT build only that. Build:

1. **A self-contained factory** — `createTheThing(parentEl, opts)` that owns everything (canvas, loop, storage, state) and takes a plain DOM parent + options.
2. **A thin widget wrapper** matching the host's exact required signature, which just loads the factory, reads host state, mounts, and returns a cleanup fn.
3. **A standalone `index.html` host** that mounts the SAME factory into a plain `<div>`.

The standalone host is what makes verification possible — you load it, drive it, read the console. Same engine logic backs both; zero duplication. This satisfies "build the widget" AND "prove it runs" at once. Flag this as an `[ALIGNMENT_WARNING]`-style note: you built the extra host specifically so it could be verified rather than declared-done-on-faith.

### 3. Expose a debug `_api` from the factory
Return `{ destroy, _api }` where `_api` exposes: `getState()`, `setState()`, `getGameState()`, `getWorld()`, the state-machine constants, and **deterministic shortcuts** (`forceUnlockAll()`, `collectBranchLeaves(id)`, etc.). This lets you teleport the player / set up exact preconditions to test a state without flaky physics navigation. It is the difference between a 5-minute verification and an hour of fighting gravity.

### 4. Serve + drive in the real browser
- Serve the dir over HTTP (`npx http-server -p PORT -c-1` in background) — cleaner than `file://` for localStorage origin behaviour and `fetch()` of side files.
- `curl` the assets for 200s first, then `browser_navigate`.
- After every meaningful action: `browser_console` (no expression) to assert **0 messages / 0 errors**, and `browser_vision` to confirm the render visually.
- Drive the FULL state machine: title → each interaction state → win → lose/restart. Use the `_api` to set preconditions, dispatch real `KeyboardEvent`s on `window` to exercise the actual input handler, and click real DOM modal buttons.

### 5. Critique the spec after building (when asked, or proactively offer)
Having implemented it, you know where the spec is hollow. The most valuable critique targets where the spec is **precise about cosmetics but silent about what makes it work** (e.g. pins hex colors but leaves win-correctness undefined). Rank by leverage: broken-core-loop fixes first, gaps second, scope flags last. See `references/spec-critique-checklist.md`.

## Pitfalls (all hit in real sessions)
- **`browser_console` expression must be ONE line / no trailing `//` comments.** Multi-line arrow IIFEs and lines ending in `//` comment before a newline fail with `SyntaxError: Unexpected end of input`. Wrap logic in `(function(){ ...; return JSON.stringify({...}); })()` on a single line. Returning a Promise from the evaluator is unreliable — split "dispatch keys + setTimeout" and "read state" into two separate calls.
- **A widget renderer alone is NOT verifiable.** If you only write the host-bound renderer, you cannot run it. Always build the standalone host (§2).
- **Trigger-radius ordering bugs are invisible in code review, obvious when driven.** Collect/pickup checks vs hostile-trigger checks: order and radii matter; driving the player onto the exact overlap point surfaces it instantly.
- **Don't physically walk the player to every test location** — it's slow and flaky. Use the `_api` to set position/state directly, then let the update loop fire the trigger.
- **Keyboard `preventDefault()` on Space/arrows breaks all form inputs.** Browser games that call `e.preventDefault()` on navigation keys (Space, arrows) unconditionally on `keydown` will silently swallow those keys inside `<textarea>`, `<input>`, `<select>`, AND `<button>` elements — meaning the user can't type spaces, navigate text, or activate focused buttons with the keyboard. Fix: gate the `preventDefault()` behind a tagName check: `if (!/^(INPUT|TEXTAREA|SELECT|BUTTON)$/.test(e.target.tagName)) e.preventDefault()`. BUTTON must be included or Tab+Space on modal dismiss/cancel buttons is dead.
- **Proximity-triggered modals re-open instantly after dismissal.** When a game loop checks trigger radii every frame and a "Skip" button only hides the modal without moving the player out of the trigger zone, `checkTriggers()` fires on the very next animation frame and re-opens the same modal — indistinguishable from "nothing happened." Fix: add a per-trigger cooldown map (`gateCooldown[triggerId] = performance.now()` on dismiss, skip in the trigger loop if within ~2s). Radius-only fixes (pushing `pRadius` back) are unreliable when the trigger checks distance at specific angular alignments.
- **localStorage-coupled apps need a journal/data-change guard.** If the app builds its world from external data (a journal, a config), add a `schemaVersion` + a hash of that data to the saved state; soft-reset stale saves on load instead of restoring entity IDs that may no longer exist. This is the single most likely real-world crash for data-driven games.
- **localStorage-seeded defaults shadow real API data — every book/level looks like the demo.** When the app seeds localStorage with demo data on startup (`localStorage.setItem(KEY, demoJournal)`) and ALL subsequent world-build calls read from localStorage (`loadJournal()`), user-selected real data from the API is NEVER loaded — regardless of what the user picks in the UI. Fix: check whether a real source is active (`activeBook`) and fetch from the API FIRST, only falling back to localStorage if the API is unreachable. Pattern: `journal = activeSource ? (await fetchFromAPI() || loadFromLocalStorage()) : loadFromLocalStorage()`. The demo-only path (`activeSource=null`) stays untouched.
- **Modal overlay onclick must call `hideModal()` — restoring state is not enough.** When a game modal's backdrop (overlay) click handler only sets `state = prevState` without calling `hideModal()`, the CSS `#overlay.show` class remains and the modal stays visible. The user perceives "clicking outside does nothing." Fix: `overlay.onclick = () => { hideModal(); state = prevState; };` — both operations are required because modal visibility is CSS-driven, not state-driven.
- **Regex literals with `\r\n` can split across physical lines on Windows.** A regex like `/[\r\n]+/` where `\r` (0x0D) sits at end-of-line followed by `\n` (0x0A, the CRLF line ending) can get parsed as a real line break by some editors/tools, splitting the regex across two lines. Symptom: `SyntaxError: Invalid regular expression: missing /` on module import. Fix: ensure these regexes are on a single physical line. Detect with `od -c`. Full file-corruption recovery patterns in `references/file-corruption-and-tool-quirks.md`.
- On Windows, pass **native `C:\...` backslash paths** to `write_file`/`patch`, never `/c/...` (silently misfiles). See the `windows-shell-handling` skill §1a.
- **A background server that "won't pick up your fix" is usually still the OLD process.** `pkill` often fails to free a Windows-bound port; the stale instance keeps the socket and you test against old code, chasing phantom bugs. Confirm the port is free and kill by PID (`netstat -ano | grep ':PORT' | grep LISTENING` → `taskkill //F //PID <pid>`) before suspecting your code.
- **`.env` numeric values can render as `***` in tool output** — that's display-layer secret redaction, not file corruption. Probe the real bytes (length / first char / parse in Node) before "fixing" an already-correct file.

## Going beyond a self-contained widget: 3D + local-LLM NPCs + disk-backed memory
When the user asks to make the game **3D** and give NPCs **memory via a local LLM** (LM Studio / Ollama / OpenAI-compatible) that writes `.md` files, the browser sandbox can't write files or hold a model connection — so the widget MUST become a **local Node-bridge app** (`node server.js` serving a Three.js front-end). State this boundary as an ALIGNMENT_WARNING; don't pretend the widget can write files. Full playbook — bridge route shapes, runtime-mutable model config + in-game Settings picker, per-NPC markdown memory, the JSON-judgement contract with a hardened extractor + graceful keyword fallback, Three.js-via-CDN, the **truncated-JSON-is-a-token-budget-bug** trap, LLM-driven content extraction with file caching, and atmospheric particle systems (ambient streams + event bursts) — is in `references/llm-npc-and-3d-upgrade.md`. File-corruption debugging patterns (split regexes, `//`-comment cascade, backslash doubling from agent tools, stale Windows port processes) are in `references/file-corruption-and-tool-quirks.md`.

## Adding depth to a working game: progression, journaling, theming
Once the core loop works, three patterns add significant depth with modest effort: **stage-based progression** with named thresholds and visual feedback (player orb grows, light expands, content gates behind stage requirements), **answer journaling** (save every gate/battle/shrine/crown answer to a permanent record the player can review), and **systematic theme reskinning** (color palette mapping + terminology mapping table before touching code). Full playbook — stage schema design, visual-feedback dispatch, content gating with friendly messages, schema migration, journal entry shape and viewer, and the two-table reskinning method — is in `references/progression-and-journaling.md`.

## Verification done = you can state, from real output
- "Loaded in browser, **0 console errors** across a full playthrough."
- Each state named, with the observed transition and the `_api`/DOM evidence that drove it.
- Screenshots of the key states (title, core interaction, win).
