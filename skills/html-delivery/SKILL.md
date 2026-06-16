---
name: html-delivery
description: "Package substantive agent outputs as interactive mobile-first HTML and deliver via Telegram Bot API. Decision tree determines when to generate HTML and which template to use. Four templates: framework, analysis, roadmap, generic."
version: 1.0.0
category: productivity
metadata:
  hermes:
    tags: [html, delivery, telegram, interactive, mobile, output]
---

# HTML Delivery Skill

Package substantive outputs as interactive, mobile-first HTML files and deliver them to the user via Telegram Bot API.

## When to Use

**Trigger conditions (any one):**
1. User explicitly asks: "html this" / "send as html" / "make interactive"
2. Output is a framework, model, analysis, plan, or teaching reference AND the user would benefit from revisiting it
3. The output has multiple sections, exercises, or action items that suit tabbed navigation

**Do NOT trigger for:** quick answers, single facts, chat conversation, tool confirmations.

## Decision Tree

```
Output ready
│
├── Substantive? (framework / analysis / plan / teaching)
│   ├── NO → deliver as text. STOP.
│   └── YES → continue
│
├── Content type?
│   ├── Framework/Model (habits, systems, taxonomies)
│   │   └── Template: framework.html (tabs: overview, cards, exercises, checklist)
│   ├── Analysis/Breakdown (incident reports, chain analysis, diagnostic)
│   │   └── Template: analysis.html (tabs: findings, chain, root-cause, actions)
│   ├── Plan/Roadmap (project plans, financial roadmaps, phase plans)
│   │   └── Template: roadmap.html (tabs: summary, phases, blockers, next)
│   └── Default
│       └── Template: generic.html (tabs: summary, details, actions)
│
├── Build HTML
│   ├── Load template file from templates/
│   ├── Inject title, sections, content
│   ├── Write to ~/deliverables/<sanitized-title>.html
│   └── Verify: file exists, > 1KB
│
├── Deliver
│   ├── Telegram configured? → python scripts/send-telegram.py <file>
│   ├── Discord configured?  → python scripts/send-discord.py <file>
│   └── Neither → cp to ~/storage/shared/Download/ + tell user
│
└── Confirm
    ├── HTTP 200 → "Delivered ✓"
    └── Error → fallback to Downloads + manual share
```

## Configuration

Delivery credentials live in environment variables set once per session:

```bash
# Telegram (from @BotFather)
export HERMES_TELEGRAM_BOT_TOKEN="123456:ABC..."
export HERMES_TELEGRAM_CHAT_ID="87654321"

# Discord (optional fallback)
export HERMES_DISCORD_WEBHOOK="https://discord.com/api/webhooks/..."
```

Credentials are NEVER written to disk. They live in shell environment only.

## Templates

All templates share these invariants:
- Zero external dependencies (single HTML file)
- Mobile-first (max-width 640px container)
- Dark theme (#0d0d0d background, #d4a853 amber accent)
- Tab navigation with persistent state
- Interactive: accordion cards, checklists (localStorage), expand/collapse
- Works offline

### Template Selection

| Template | Use When | Tabs |
|---|---|---|
| `framework.html` | Model/taxonomy/system with exercises | Overview, Cards, Exercises, Checklist |
| `analysis.html` | Diagnostic, incident report, root-cause chain | Findings, Chain, Root Cause, Actions |
| `roadmap.html` | Phased plan or roadmap | Summary, Phases, Blockers, Next |
| `generic.html` | Teaching, reference, mixed content | Summary, Details, Actions |

## Worked Examples

| Example | Template | Description |
|---|---|---|
| `references/example-analysis-readme.md` | analysis.html | NZ trip preparedness incident — full 4-tab breakdown with cost analysis, failure chain, exposed assumptions, corrective systems |

The live HTML file lives at `~/deliverables/nz-preparedness-analysis.html` on the user's device.

## Scripts

### send-telegram.py
Sends a file via Telegram Bot API. Reads `HERMES_TELEGRAM_BOT_TOKEN` and `HERMES_TELEGRAM_CHAT_ID` from environment.

Usage: `python scripts/send-telegram.py <file_path> [caption]`

### send-discord.py
Sends a file via Discord webhook. Reads `HERMES_DISCORD_WEBHOOK` from environment.

Usage: `python scripts/send-discord.py <file_path> [message]`

## Pitfalls

1. **Don't HTML everything.** Quick replies are text-only.
2. **Credentials expire.** 401 = token revoked.
3. **File size.** Bot API limit is 50MB — HTML files are 20-60KB, not a constraint.
4. **HTML injection.** Templates use textContent for user content (never innerHTML).
5. **Filename collisions.** Sanitize with em-dash replacement for `<>:"/\|?*`.
