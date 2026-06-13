---
name: knowledge-tree-explorer-dev
description: Develop and extend the Knowledge Tree Explorer v3+ — a wuxia cultivation-themed 3D scripture study game. Covers the Node bridge server, Three.js frontend (game3d.js), book manifests, LLM integration endpoints, particle systems, and the cultivation stage mechanics. Use when modifying or debugging any KTX v3 code.
---

# Knowledge Tree Explorer v3 — Development Guide

## Project Layout
```
v3/
  .env               — LMSTUDIO_BASE_URL, MODEL, PORT, TEMPERATURE, MAX_TOKENS, LLM_TIMEOUT_MS
  server.js          — Node bridge (pure stdlib, no npm deps)
  public/
    index.html       — HTML shell + CSS + import map for Three.js CDN
    game3d.js        — All game logic (~700 lines): 3D scene, state machine, modals, particles
    bridgeClient.js  — Canonical API seam for all bridge endpoints
  books/
    <book-id>/
      book.json      — { id, title, author, totalChapters, chapters: [{index, title, file?}] }
      full.md        — Full text (bridge splits by \n<N>\n pattern for chapter extraction)
      insights.json  — Cached LLM-extracted insights + summaries (auto-generated)
  memory/
    npc-*.md         — Per-creature memory files (written by bridge)
    actor-game-state-3d-*.json — Per-book, per-slot save files
```

### LM Studio URL Configuration
LM Studio runs on **Windows directly** (not inside WSL2), so use `http://localhost:1234/v1` in `.env`. The WSL2 virtual-adapter IP (`169.254.x.x`) shifts on reboot and will break the connection. If the bridge shows `llm: false` on `/api/health`, check:
1. LM Studio is running (tasklist shows `LM Studio.exe`)
2. Port 1234 is listening (`netstat -ano | grep 1234`)
3. The URL in `.env` is `localhost:1234`, not a WSL2 IP
4. If WSL2 IP was used, kill the old server, update `.env` + `server.js` fallback, restart

## Tooling & Editing Patterns

### Prefer `patch` for game3d.js edits
The file is large (~680 lines). Use `patch` with exact old_string/new_string. Match the file's literal content — template literals use backticks with unescaped double quotes inside them.

### Regex Display Artifact — VERIFY BEFORE DISMISSING
When `read_file` shows a regex like `split(/[\\r\\n]+/)` split across two physical lines, it MAY be a display artifact OR a genuine syntax error. The viewer can show `\\r` as a line break when it's actually on one line. **Always verify with `node --check`:** if Node reports `Invalid regular expression: missing /`, the regex is genuinely broken across lines and must be fixed by rejoining them. Do NOT dismiss the error without checking.
→ See `references/rollback-recovery.md` for the full rollback procedure when bulk changes fail.
→ See `references/regex-across-lines-bug.md` for the split-regex recovery pattern.

### Fixing Split Regex Lines
If a regex is genuinely split (confirmed by `node --check` failing):
```js
// BROKEN — line break inside regex literal:
const lines = text.split(/[\r
]+/);

// FIXED — single line:
const lines = text.split(/[\\r\\n]+/);
```
Use `execute_code` with Python to fix, since `patch` struggles with embedded carriage returns in old_string/new_string.

### `write_file` Backslash Doubling Pitfall
The `write_file` tool doubles backslashes in its `content` parameter. A string like `replace(/<\\/?small>/gi,'')` written via `write_file` becomes `replace(/<\\\\/?small>/gi,'')` in the file (four backslashes), which is a syntax error. **Never use `write_file` for JavaScript files containing regex literals with backslashes.** Use `execute_code` with Python instead for precise byte-level control. Alternatively, use `patch` for small targeted edits.

### Terminal Python for Binary Fixes
If `patch` can't handle a string with embedded carriage returns, use:
```bash
python -c "
with open('game3d.js', 'r', newline='') as f:
    content = f.read()
# ... fix ...
with open('game3d.js', 'w', newline='') as f:
    f.write(content)
"
```
**CRITICAL: NEVER use `newline=''` with `writelines()`.** `writelines` with `newline=''` strips all CRLF → LF, collapsing the file to a single line. This causes `//` comments to eat all subsequent code on that line, destroying the file. Use `f.write(content)` with a single string instead, or use `newline='\r\n'` explicitly for Windows line endings.

### Post-Edit Verification
After ANY edit to game3d.js, run `node --check public/game3d.js` from the v3 directory. A passing check means the file is syntactically valid. If it fails, do NOT reload the page — fix the error first. The browser's module loader will silently fail with empty-message exceptions that are hard to diagnose.

### Bridge Endpoint Pattern
All endpoints follow the same routing style in server.js:
```js
if (url.pathname.includes('/some-path')) {
  // handle GET/POST
  return send(res, 200, { ... });
}
```
Route ordering matters — specific paths (insights, summary, chapter) must be checked BEFORE the generic `/api/books/:id` catch-all.

### Server Restart Required
Any server.js change requires restarting `node server.js`. Frontend changes (game3d.js, index.html) only need a browser refresh.

## Cultivation Theme State

### Stages (in game3d.js)
```js
const STAGES = [
  { name:'Qi Condensation',  emoji:'🌊', threshold:0,  orbSize:0.8,  emissive:1.0, lightRange:16, color:0xffd700 },
  { name:'Foundation Est.',  emoji:'🏛️', threshold:5,  orbSize:1.05, emissive:1.3, lightRange:20, color:0xffd700 },
  { name:'Golden Core',      emoji:'☀️', threshold:12, orbSize:1.35, emissive:1.7, lightRange:26, color:0xffaa00 },
  { name:'Nascent Soul',     emoji:'👁️', threshold:22, orbSize:1.7,  emissive:2.2, lightRange:35, color:0xffffff },
];
```

### Terminology Map (cultivation ↔ original)
| Cultivation | Original |
|-------------|----------|
| Heart Demon | Doubt Creature |
| Enlightenment Pool | Memory Shrine |
| Heavenly Ascension | The Crown |
| Heavenly Tribulation | Crown access gate |
| Break Formation | Compress Gate |
| Spirit Herbs / Techniques | Leaves / Cards |
| Qi (☯) | Hearts (♥) |
| Spirit Sense | NPC brain / LM Studio |
| Karmic Records | NPC Memory |
| Sacred Scripture Tree | Knowledge Tree |
| Scripture / Scroll | Book / Chapter |
| Cultivation Record | (new — user's journal) |

### Color Palette
- Background: #080d18 (deep ink)
- Panel: #151f2e, Line: #1e3040
- Text: #e0d5c0 (parchment), Muted: #8a8070
- Gold: #ffd700 (player core, Qi particles, headings)
- Crimson: #991b1b (demons, errors)
- Jade: #2a4a35 (branches), Dark jade: #1a2a20 (trunk)
- Imperial gold: #f59e0b (crown, accent)
- Spirit violet: #7c3aed (shrines/enlightenment pools)

### Key Game State Fields (schema v5)
```js
gs = {
  schemaVersion: 5,
  qi: 3,                  // Replaces old `health`
  cultivationStage: 0,    // Index into STAGES
  insightCount: 0,        // Herbs collected + demons defeated
  branchesUnlocked: [],
  leavesCollected: [],
  creaturesDefeated: [],
  shrinesActivated: [],
  crownDone: false,
  deck: [],               // Spirit herb cards
  journalEntries: [],     // { type, chapter, prompt, answer, ts }
  checkpointBranch: -1,
}
```

## Current Visual State (post-rollback)

The v4 visual overhaul (nebula, bonsai branches, foliage, terrain, follow-cam) was attempted in session 2026-06-11 but **rolled back** because bulk application introduced cascading reference errors (1000 `meshes.foliage is not iterable` per frame). The working baseline is:

### What IS active (kept from v4 attempt)
- **World-tree scale parameters**: TRUNK_R=5.0, SPACING=40, BRANCH_LEN=30, 600 Qi particles, 2000 stars
- **Ghost soul player**: multi-layered cyan wisp Group (core + inner glow + outer shell + 6 tendrils + cyan PointLight)
- **No-gravity movement**: direct up/down translation, Space pushes radially outward, smooth radius lerp
- **Gnarled trunk**: vertex-displaced CylinderGeometry with 7 root structures
- **Blood-red rim light** from below, darker fog (`FogExp2`)
- **Spirit Sense modal exit**: overlay click calls `hideModal()` before restoring state
- **OrbitControls** still active (follow-cam was rolled back)

### What was rolled back (apply ONE at a time, test after each)
| Feature | Why rolled back |
|---|---|
| Follow camera (lerp-based) | `meshes.foliage` scope error masked cam issues |
| Nebula sky sphere | `createNebulaTexture()` scope errors |
| Bonsai TubeGeometry branches | Required `meshes.foliage` array not fully wired |
| Foliage clusters | `meshes.foliage is not iterable` — 1000 errors/sec |
| Undulating terrain | Cascaded from above failures |

### Re-application approach
Apply ONE visual feature at a time, verify with `node --check` AND browser console (zero errors), THEN move to the next. Do not batch. The order should be:
1. Terrain (independent of other systems)
2. Nebula sky (independent)
3. Follow camera (depends on nothing new)
4. Organic branches + foliage (requires `meshes.foliage` wiring — see pitfall below)

### General `meshes.X` Array Addition Checklist
When adding ANY new mesh collection array to `meshes`, update ALL THREE locations:
1. Declaration: `const meshes = { ..., X:[] }`
2. Cleanup loop: `meshes.X.forEach(m=>scene.remove(m))`
3. Reset block: `meshes.X=[]`
Missing any one causes `TypeError: meshes.X is not iterable` flooding the console every animation frame.

### Movement System (current)
- **No gravity** — up/down keys translate directly along trunk at `MOVE_SPEED=22`
- **Space** pushes radially outward: `pTargetRadius = TRUNK_R + BRANCH_LEN*0.9`
- Smooth radius lerp: `pRadius += (pTargetRadius - pRadius) * Math.min(1, 8*dt)`
- Auto-retract toward trunk when not actively jumping
- Max radius clamped to full branch length
- Double-click branch to auto-fly to it (targetBranch system unchanged)
- OrbitControls still active for manual camera rotation

### Scale Parameters (CURRENT)
| Parameter | v3 (original) | Current |
|---|---|---|
| TRUNK_R | 1.6 | **5.0** |
| SPACING | 16 | **40** |
| BRANCH_LEN | 13 | **30** |
| Qi particles | 250 | **600** |
| Star field | 800 | **2000** |
| Demon size | 1.1 | **1.8** |
| Shrine size | 1.4 | **2.2** |
| Crown size | 2.0 | **3.5** |
| Ground | r=60 flat disc | r=120 flat disc |

## Key Functions Map (game3d.js)
| Function | Purpose |
|----------|---------|
| `buildSceneFromWorld()` | Rebuilds 3D scene + Qi streams on tree change |
| `rebuildQiStreams(h)` | Creates 250-particle golden spiral |
| `spawnBurst(origin, color, count, ms)` | Short-lived particle explosion |
| `updateParticles(dt, now)` | Animates Qi + burst cleanup |
| `assessStage()` | Checks insightCount → updates stage + visuals |
| `updatePlayerVisuals()` | Scales orb, shifts emissive/light per stage |
| `addJournalEntry(type, ch, prompt, ans)` | Saves answer to gs.journalEntries |
| `renderScrollHtml(text)` | Markdown → HTML with headings + key-passage highlights |
| `fetchSummary(bookId, idx)` | Calls bridge for LLM chapter summary |
| `buildBookJournal()` | Fetches book manifest + insights cache → journal |
| `generateInsights()` | UI flow for POST /api/books/:id/insights |

## Books Currently Available
- `atomic-habits` — 4 chapters with individual .md files
- `total-money-makeover` — 13 chapters, no chapter files (needs full.md)
- `proverbs` — 31 chapters KJV, downloaded via Bible API, 77K chars

## Adding a New Book
1. Create `books/<id>/book.json` with chapters array
2. Add `books/<id>/full.md` with full text (use `\n<N>\n` chapter boundaries)
3. Bridge auto-scans on startup
4. User runs "✨ Generate Insights" from save slots to extract LLM insights
