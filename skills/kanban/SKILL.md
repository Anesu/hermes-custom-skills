---
name: kanban
description: Hermes Kanban multi-agent work queue — orchestrator decomposition playbook and worker pitfalls for both roles.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, worker, routing, collaboration, workflow]
---

# Kanban — Multi-Agent Work Queue

Hermes Kanban is a durable SQLite board for multi-profile / multi-worker collaboration. Two roles: orchestrator (route + decompose) and worker (execute one task). The core lifecycle is auto-injected into every worker's system prompt; this skill is the deeper playbook for both roles.

---

## When to Use the Board (vs delegate_task)

Create Kanban tasks when any are true:
1. **Multiple specialists needed** — different profiles for different lanes
2. **Work must survive crash/restart** — long-running, important
3. **Human-in-the-loop** — operator may need to interject
4. **Parallel subtasks** — fan-out for speed
5. **Review/iteration expected** — reviewer profile loops on drafter output
6. **Audit trail matters** — board rows persist in SQLite forever

If none apply → use `delegate_task` or answer directly.

---

## Orchestrator — Decomposition Playbook

### Step 0: Discover profiles
`hermes profile list` — the dispatcher silently fails on unknown assignee names.

### The anti-temptation rules
- Do NOT execute the work yourself — route it
- For any concrete task, create a Kanban task and assign
- Split multi-lane requests before creating cards
- Run independent lanes in parallel — don't link unless data depends
- Never create dependent work as independent ready cards — use `parents=[...]`

### Decompose
1. Understand the goal (clarify if ambiguous)
2. Extract lanes from the request, map each to a profile
3. Present graph to user before creating cards
4. Create tasks: capture ids, link with `parents=[...]` during creation

```python
t1 = kanban_create(title="research: cost comparison", assignee="<profile-A>", body="...")["task_id"]
t2 = kanban_create(title="research: performance", assignee="<profile-A>", body="...")["task_id"]
t3 = kanban_create(title="synthesize recommendation", assignee="<profile-B>", body="...", parents=[t1, t2])["task_id"]
```

### Common patterns
- **Fan-out + fan-in:** N research cards → 1 synthesis card with all as parents
- **Pipeline with gates:** planner → implementer → reviewer, each `parents=[prev]`
- **Same-profile queue:** N tasks, same profile, no deps → dispatcher serializes
- **Human-in-the-loop:** `kanban_block()` to wait for input; dispatcher respawns on `/unblock`

### Goal-mode cards
For open-ended work (multi-turn, "keep going until X is true"):
```python
kanban_create(..., goal_mode=True, goal_max_turns=15)
```
Judge re-checks after each turn against title+body as acceptance criteria.

### Recovering stuck workers
- **Reclaim:** abort worker, reset task to `ready` → `hermes kanban reclaim <id>`
- **Reassign:** switch profile → `hermes kanban reassign <id> <new-profile> --reclaim`
- **Change model:** edit profile model on disk, then Reclaim

### Pitfalls (orchestrator)
- Inventing profile names that don't exist → silent failure
- Bundling independent lanes into one card
- Over-linking because of wording ("finally check X" often parallel)
- Forgetting dependency links → implementer runs before research done
- Reassignment vs new task: reviewer blocks → create NEW task, don't rerun same

---

## Worker — Execution and Handoff

### Workspace handling
| Kind | Behavior |
|------|----------|
| `scratch` | Fresh tmp dir, GC'd on archive. Read/write freely. |
| `dir:<path>` | Shared persistent dir. Other runs read what you write. |
| `worktree` | Git worktree. Commit work here. |

### Task lifecycle
1. **Orient** — `kanban_show` to read task body and prior runs
2. **Work** — use tools, make progress
3. **Heartbeat** — name progress: `"epoch 12/50, loss 0.31"`; skip for sub-2min tasks
4. **Block** — when blocked: `kanban_comment(body="context")` + `kanban_block(reason="specific question")`
5. **Complete** — `kanban_complete(summary="...", metadata={...})`

### Good handoff shapes
```python
# Coding task
kanban_complete(
    summary="shipped rate limiter — token bucket, keys on user_id, 14 tests pass",
    metadata={"changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"], "tests_run": 14, "tests_passed": 14}
)

# Review-required (use BLOCK, not COMPLETE)
kanban_block(reason="review-required: rate limiter shipped, 14/14 pass — needs eyes on key choice")

# Research task
kanban_complete(summary="3 libraries reviewed; vLLM wins on throughput", metadata={"recommendation": "vLLM", "sources_read": 12})

# Review task
kanban_complete(summary="reviewed PR #123; 2 blocking issues", metadata={"pr_number": 123, "findings": [...], "approved": False})
```

### created_cards — claim carefully
Only list ids from successful `kanban_create` return values. The kernel verifies each id exists and was created by your profile. Phantom ids block completion.

### Retry diagnostics
- `outcome: timed_out` → chunk work or shorten
- `outcome: crashed` → OOM/segfault, reduce footprint
- `outcome: spawn_failed` + error → block with details, don't retry blind
- `outcome: blocked` → unblock comment should be in thread

### Pitfalls (worker)
- Task state may have changed between dispatch and startup → always `kanban_show` first
- Do NOT call `clarify` — you're headless with no live user
- Do NOT call `delegate_task` as substitute for `kanban_create`
- Do NOT rely on CLI (`hermes kanban <verb>`) in containerized backends — use tools
- Workspace may have stale artifacts from previous runs
