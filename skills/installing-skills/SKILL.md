---
name: installing-skills
description: |
  Install, upgrade, and verify third-party agent skills (Claude Code, opencode,
  Hermes, and other SKILL.md-based ecosystems) from GitHub repos, raw URLs, or
  local paths. Use when the user says "install this skill", points at a
  github.com/<user>/<repo>/blob/.../SKILL.md URL, asks to upgrade an existing
  skill to a newer version, or wants to verify a skill install is intact. Covers
  the single-file case (just SKILL.md), the package case (SKILL.md + assets/ +
  references/ + scripts/), license/frontmatter divergence detection, URL format
  quirks (tag vs branch vs commit SHA), and post-install path-integrity
  verification. Does NOT cover authoring original skills (use
  hermes-agent-skill-authoring for that).
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skill-management, github, installation, verification, third-party]
    category: software-development
    related_skills: [hermes-agent-skill-authoring, write-a-skill, hermes-agent]
---

# Installing Third-Party Skills

Acquire, upgrade, and verify agent skills that follow the SKILL.md convention
(Claude Code, opencode, Hermes, and the broader MCP-style skill ecosystem).
Treats every install as a **supply-chain event** — provenance, integrity, and
license matter as much as the file copy.

---

## Core Task

When given a skill source (GitHub URL, raw URL, local path, or "upgrade X to Y"):

1. **Classify the source** — single file vs package, public vs private, pinned vs floating
2. **Stage safely** — never overwrite blindly; clone to /tmp first, then copy
3. **Detect divergence** — license in `LICENSE` vs license in SKILL.md frontmatter
4. **Install to the right root** — Hermes: `~/.hermes/skills/` · Claude Code: `~/.claude/skills/` · opencode: vendor docs
5. **Verify integrity** — every path the SKILL.md references must exist on disk
6. **Smoke-test** — syntax-check scripts, confirm templates load, flag any missing assets
7. **Report** — concise install report; never invent success

---

## Source Classification

A user-provided URL falls into one of four shapes. Each needs a different
fetch strategy.

| Shape | Example | Fetch with |
|---|---|---|
| `github.com/<u>/<r>/blob/<ref>/SKILL.md` | `github.com/foo/bar/blob/main/SKILL.md` | Convert to `raw.githubusercontent.com/foo/bar/<ref>/SKILL.md` |
| `raw.githubusercontent.com/...` | `raw.githubusercontent.com/foo/bar/refs/heads/main/SKILL.md` | `curl -fsSL` direct |
| `<u>/<r>` with "install skill" intent | `github.com/foo/bar` | First hit `/api/repos/<u>/<r>/contents/` to enumerate; SKILL.md may be in a subdir |
| `git clone <url>` or "<u>/<r> skill" with no path | full repo | `git clone --depth=1` to `/tmp/<name>-staging` |

**Always prefer raw URLs or git clone.** `web_extract` summarises — it can
truncate a 600-line SKILL.md to 50 lines and you'll miss entire sections
(layouts, validators, image pipelines). For single-file fetches where the file
is small enough to read in full, `web_extract` is fine. For anything bigger
than ~5 KB, fetch raw.

### URL format pitfalls

- **Tag-only URLs return 404 if the tag isn't vendored as a branch.** If
  `https://raw.githubusercontent.com/<u>/<r>/v2.8.0/SKILL.md` 404s, retry
  against the `main` branch and pin to a commit SHA locally.
- **`/refs/heads/main/` is the explicit branch form**; `/main/` is shorthand
  and sometimes gets redirected. Use the explicit form for `curl` to skip the
  redirect.
- **Path traversal in user-supplied URLs** — if the user pastes a URL with
  `..` or backslashes, sanitize before composing the curl URL.

---

## Single-File vs Package Judgment

Before fetching, decide whether the skill is one file or many. The two signals:

1. **Grep the SKILL.md body for `assets/`, `references/`, `scripts/`** — if
   they appear, it's a package.
2. **Hit `/api/repos/<u>/<r>/contents/` and inspect the file tree** — if there
   are sibling directories, it's a package.

For a **single file** (just SKILL.md, plus maybe LICENSE), `skill_manage
action=write_file` is enough:

```bash
# Hermes
~/.hermes/skills/<name>/SKILL.md
# Claude Code
~/.claude/skills/<name>/SKILL.md
```

For a **package**, never use `write_file` for the SKILL.md alone — `cp -r` the
whole staging tree. The package is broken if any asset is missing.

```bash
SKILL_DIR=~/.hermes/skills/<name>
rm -rf "$SKILL_DIR"  # never silently overwrite; the user may have local edits
mkdir -p "$SKILL_DIR"
cp -r /tmp/<name>-staging/assets     "$SKILL_DIR/"
cp -r /tmp/<name>-staging/references "$SKILL_DIR/"
cp -r /tmp/<name>-staging/scripts    "$SKILL_DIR/"
cp    /tmp/<name>-staging/SKILL.md   "$SKILL_DIR/"
cp    /tmp/<name>-staging/LICENSE    "$SKILL_DIR/"
# README/CONTRIBUTING/SPONSORS optional but cheap and useful
```

**Rule:** if you can't see the whole repo tree, ask the user before installing
single-file only. The cost of pulling assets is near zero; the cost of a broken
skill reference is a confused next agent.

---

## License & Frontmatter Divergence

Upstream skill authors frequently get this wrong. The `LICENSE` file is the
legally binding artifact; the SKILL.md `license:` frontmatter is documentation
that can be stale. Always check both.

| `LICENSE` | `license:` frontmatter | Action |
|---|---|---|
| MIT | MIT | ✅ Match, no action |
| MIT | (missing) | Add `license: MIT` to frontmatter via patch |
| AGPL-3.0 | MIT | 🚨 **MISMATCH** — surface to user, do not silently fix; the binding license is the file |
| AGPL-3.0 | (missing) | Add `license: AGPL-3.0` |
| (no LICENSE) | MIT | 🚨 Unverified — surface to user, request clarification |
| Apache-2.0 | MIT | 🚨 MISMATCH — surface |

For personal/internal use, the license rarely matters at install time. For
anything redistributed, generated, or shipped downstream, **AGPL-3.0 in
particular has a network-copyleft clause** that bites hard if generated decks
or outputs are served over a network. Always surface AGPL before the first
generation, not after.

---

## Upgrade Protocol

When the user says "upgrade X" or "X is at v2.8, install it":

1. **Read the installed version first** — `head -20 ~/.hermes/skills/<name>/SKILL.md`
2. **Diff what changed** — if you can, hit the upstream version and compare
3. **Decide on overwrite vs in-place patch** —
   - **Overwrite** when upstream shipped a full rewrite of SKILL.md (most
     upgrades) — preserve any local frontmatter blocks (e.g. `metadata.hermes`)
     by re-applying after the overwrite
   - **Patch** when the upstream change is small and you want to preserve any
     user edits — `skill_manage action=patch` with `old_string`/`new_string`
4. **Verify** — re-run the path-integrity check and smoke tests

A common pitfall: the upstream SKILL.md frontmatter shape changes between
versions (e.g. v2.5.1 used a `hermes:` block, v2.8.0 uses flat `name/version/
description/license/compatibility`). After an upgrade, check whether the
auto-discovery still works for the new shape, and surface any category
metadata the user previously had.

---

## Post-Install Verification

Three checks, in order:

### 1. Path integrity

For every `references/<x>.md` and `assets/<y>` mentioned in SKILL.md, confirm
it exists on disk:

```bash
grep -oE 'references/[a-zA-Z0-9._-]+\.md' SKILL.md | sort -u
# compare against
ls references/ | sort
```

If any reference points at a file you didn't install, the skill is broken at
first invocation. Either pull the missing files or report the gap to the user.

### 2. Template/script smoke test

For HTML templates, confirm the structural markers load (CSS class names,
font family references) — a 0-byte file would silently pass `wc -l` and break
later.

```bash
grep -c "h-hero" assets/template.html       # >=1
grep -c "Noto Serif SC" assets/template.html # >=1
```

For Node.js validator scripts: `node --check <script>.mjs` (silent exit = OK,
errors = broken).

### 3. Cleanup

`rm -rf /tmp/<name>-staging` after install. Staging dirs with secrets
(`GITHUB_TOKEN`, private repo clones) must not survive the session.

---

## Common Pitfalls

- **Trusting `web_extract` for the whole SKILL.md** — it summarises. The
  truncation in this very skill (the `claude-design` recipe) cut the
  placeholder table, screenshot section, and validator doc. Always fetch raw
  for files >5 KB.
- **Overwriting an installed skill without diffing** — the user may have
  hand-edited the local copy. Show the diff first when both versions exist.
- **Installing to the wrong root** — Hermes uses `~/.hermes/skills/`, Claude
  Code uses `~/.claude/skills/`, opencode uses a different path again. Check
  the SKILL.md `compatibility:` field and match to the host agent.
- **Leaving a `git clone` on disk** — the `.git` directory in staging carries
  commit history and may include private repo metadata. Always `rm -rf` after
  the copy.
- **Silent success on partial installs** — if a `curl` fails for one asset,
  report the gap, don't pretend the install worked. Reporting a blocker
  honestly is always better than inventing a result.
- **Frontmatter shape changes on upgrade** — if v_old had a `hermes:` block
  and v_new uses a flat shape, the skill's category/tags may disappear from
  the discovery UI. Surface this to the user and offer to re-add the metadata
  block.
- **AGPL license on output generators** — if a skill generates user-facing
  artifacts (PPTs, HTML, images) and the skill is AGPL, the *generated
  output's* distribution is potentially subject to AGPL's source-disclosure
  requirements. Surface this BEFORE the first generation, not after.
- **Path-integrity check requires the full file** — if the SKILL.md is on
  disk in truncated form (e.g. from `web_extract` summary), the grep will
  miss references. Always do integrity checks against the raw file.

---

## Install Report Shape

When reporting back to the user, use a tight table or list:

```
| | |
|---|---|
| Source | <u>/<r> @ <ref> |
| Install path | ~/.hermes/skills/<name>/ |
| Size | <X> MB |
| Files | <N> |
| Path integrity | ✅ All <K> references/ and <J> assets/ present |
| Templates | <Style A>, <Style B> — both ready |
| Discovery | Auto |
| License | <spdx> — <note any divergence> |
```

Then a short usage line:

```
/skill <name>
```

And a `⚠️ Flags` section for anything that needs the user's attention:
license mismatches, dependency on system binaries, sponsor info in the
frontmatter, language mismatches, etc. Never pad with prose — the user is
high-signal, not high-pleasantry.

---

## References

- `references/license-divergence-cases.md` — concrete AGPL/MIT mismatches seen
  in real skill installs and what to do about them
- `references/url-format-quirks.md` — known 404 patterns and workarounds
  across common skill hosters
- `templates/install-report.md` — copy/paste install report template
