---
name: github
description: GitHub operations — auth setup, repo management, PR lifecycle, code review, issue triage — via gh CLI or curl fallback.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Authentication, Git, gh-cli, Pull-Requests, Issues, Code-Review, Repositories, Releases, CI/CD]
---

# GitHub

Complete GitHub workflow — authentication, repository management, pull request lifecycle, code review, and issue triage. Every section supports two paths: `gh` CLI (if installed) and `git` + `curl` (always available).

## Quick Auth Detection

Every GitHub operation starts with this block to determine whether to use `gh` or fall back to `git` + `curl`:

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if _hermes_env="${HERMES_HOME:-$HOME/.hermes}/.env"; [ -f "$_hermes_env" ] && grep -q "^GITHUB_TOKEN=" "$_hermes_env"; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$_hermes_env" | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi

# Owner/Repo from git remote
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

---

## 1. Authentication Setup

### Git-Only (HTTPS token)
1. User creates token at https://github.com/settings/tokens (scopes: `repo`, `workflow`)
2. `git config --global credential.helper store`
3. Do one `git ls-remote https://github.com/<user>/<repo>.git` — enter username + token as password
4. `git config --global user.name "Name"` / `git config --global user.email "email@example.com"`

### Git-Only (SSH)
1. `ssh-keygen -t ed25519 -C "email" -f ~/.ssh/id_ed25519 -N ""`
2. Add public key at https://github.com/settings/keys
3. `git config --global url."git@github.com:".insteadOf "https://github.com/"`
4. Test: `ssh -T git@github.com`

### gh CLI
1. `gh auth login` (interactive browser) or `echo "<TOKEN>" | gh auth login --with-token` (headless)
2. `gh auth setup-git`
3. Verify: `gh auth status`

### Curl API fallback
```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

---

## 2. Repository Management

### Clone
```bash
git clone https://github.com/owner/repo.git
gh repo clone owner/repo   # gh shorthand
```

### Create
```bash
gh repo create my-project --public --clone
# curl fallback:
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos \
  -d '{"name":"my-project","private":false,"auto_init":true}'
```

### Fork
```bash
gh repo fork owner/repo --clone
# curl: POST /repos/owner/repo/forks, then git clone + git remote add upstream
```

### Sync fork
```bash
git fetch upstream && git checkout main && git merge upstream/main && git push origin main
```

### Releases
```bash
gh release create v1.0.0 --title "v1.0.0" --generate-notes
# curl: POST /repos/$OWNER/$REPO/releases -d '{"tag_name":"v1.0.0",...}'
```

### Secrets (Actions)
```bash
gh secret set API_KEY --body "value"
gh secret list
```

### Branch protection, repo settings
```bash
gh repo edit --description "..." --visibility public --enable-auto-merge
# curl: PATCH /repos/$OWNER/$REPO
```

### Quick Reference
| Action | gh | curl |
|--------|-----|------|
| Clone | `gh repo clone o/r` | `git clone https://github.com/o/r.git` |
| Create | `gh repo create name --public` | `POST /user/repos` |
| Fork | `gh repo fork o/r --clone` | `POST /repos/o/r/forks` + clone |
| Release | `gh release create v1.0` | `POST /repos/o/r/releases` |
| List CI | `gh workflow list` | `GET /repos/o/r/actions/workflows` |
| Rerun CI | `gh run rerun ID` | `POST /repos/o/r/actions/runs/ID/rerun` |
| Set secret | `gh secret set KEY` | `PUT /repos/o/r/actions/secrets/KEY` |

---

## 3. Pull Request Workflow

### Branch
```bash
git checkout main && git pull origin main
git checkout -b feat/description   # or fix/, refactor/, docs/, ci/
```

Naming: `feat/`, `fix/`, `refactor/`, `docs/`, `ci/`

### Commit (Conventional Commits)
```bash
git add <files>
git commit -m "feat: short description

- Bullet points explaining the change"
```
Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`

### Push
```bash
git push -u origin HEAD
```

### Create PR
```bash
gh pr create --title "feat: ..." --body "## Summary\n..." [--draft] [--reviewer user]
# curl: POST /repos/$OWNER/$REPO/pulls -d '{"title":"...","head":"$BRANCH","base":"main"}'
```

### Monitor CI
```bash
gh pr checks [--watch]
# curl: GET /repos/$OWNER/$REPO/commits/$SHA/status + check-runs
```

### Auto-fix CI failures (loop)
1. `gh run list --branch $(git branch --show-current)` — find failed run
2. `gh run view <ID> --log-failed` — read errors
3. Fix code, `git add . && git commit -m "fix: ..." && git push`
4. Re-check CI — repeat up to 3 times

### Merge
```bash
gh pr merge --squash --delete-branch
# curl: PUT /repos/$OWNER/$REPO/pulls/$PR/merge -d '{"merge_method":"squash"}'
# Then: git checkout main && git pull origin main && git branch -d <branch>
```

Methods: `merge`, `squash`, `rebase`

---

## 4. Code Review

### Local (pre-push)
```bash
git diff main...HEAD --stat       # scope
git diff main...HEAD              # full diff
git log main..HEAD --oneline      # commits
```

### PR review on GitHub
```bash
gh pr view 123
gh pr diff 123 [--name-only]
# Check out locally: git fetch origin pull/123/head:pr-123 && git checkout pr-123
```

Inline comments with gh:
```bash
HEAD_SHA=$(gh pr view 123 --json headRefOid --jq '.headRefOid')
gh api repos/$OWNER/$REPO/pulls/123/comments --method POST \
  -f body="Suggestion" -f path="src/file.py" -f commit_id="$HEAD_SHA" -f line=45 -f side="RIGHT"
```

Submit review:
```bash
gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --request-changes --body "See inline comments."
```

### Review output format
```
## Code Review Summary
### Critical — file:line → problem
### Warnings — file:line → concern
### Suggestions — file:line → improvement
### Looks Good — positives
```

---

## 5. Issue Management

### View / Search
```bash
gh issue list [--state open --label "bug" --assignee @me]
gh issue view 42
# curl: GET /repos/$OWNER/$REPO/issues?state=open&labels=bug
```

### Create
```bash
gh issue create --title "..." --body "## Description\n..." --label "bug,backend" --assignee "user"
# curl: POST /repos/$OWNER/$REPO/issues
```

### Manage
```bash
gh issue edit 42 --add-label "priority:high" --remove-label "needs-triage"
gh issue edit 42 --add-assignee @me
gh issue comment 42 --body "Investigated..."
gh issue close 42 [--reason "completed"|"not planned"]
gh issue reopen 42
```

### Link to PRs
Automatic closure with keywords in PR body: `Closes #42`, `Fixes #42`, `Resolves #42`

### Bulk operations
```bash
gh issue list --label "wontfix" --json number --jq '.[].number' | xargs -I {} gh issue close {} --reason "not planned"
```

### Quick Reference
| Action | gh | curl |
|--------|-----|------|
| List | `gh issue list` | `GET /repos/o/r/issues` |
| Create | `gh issue create ...` | `POST /repos/o/r/issues` |
| Label | `gh issue edit N --add-label X` | `POST /repos/o/r/issues/N/labels` |
| Comment | `gh issue comment N --body ...` | `POST /repos/o/r/issues/N/comments` |
| Close | `gh issue close N` | `PATCH /repos/o/r/issues/N` |

---

## Complete Workflow Example

```bash
# Start
git checkout main && git pull origin main
git checkout -b fix/login-bug

# Code changes made...

# Commit and push
git add src/auth.py tests/test_auth.py
git commit -m "fix: correct redirect after login"
git push -u origin HEAD

# Create PR
gh pr create --title "fix: correct redirect after login" --body "Fixes #42"

# Monitor CI
gh pr checks --watch

# Merge when green
gh pr merge --squash --delete-branch
```

## Common Pitfalls

1. **Credentials not persisting** — check credential helper: if using gh, `git config --global credential.helper` may be empty because `gh auth setup-git` sets per-domain helpers (`credential.https://github.com.helper`). Run `git config --global --list | grep credential` to see the full picture. For git-only HTTPS, check `git config --global credential.helper` is `store` or `cache`.
2. **Token lacks scopes** — needs `repo` and `workflow` at minimum
3. **gh not installed, no sudo** — use git + curl fallback; no installation needed
4. **SSH port 22 blocked** — add `Port 443` + `Hostname ssh.github.com` to `~/.ssh/config`
5. **Multiple GitHub accounts** — use per-repo credential URLs or SSH host aliases
6. **Review comments on wrong line** — `line` field is the NEW file line number; use `side: "LEFT"` for deletions
