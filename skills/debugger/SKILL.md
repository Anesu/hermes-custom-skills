---
name: debugger
description: Programmatic debugging for Python (pdb/debugpy) and Node.js (node inspect/CDP) via terminal CLI — breakpoints, stepping, state inspection, remote attach.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, python, nodejs, pdb, debugpy, node-inspect, cdp, breakpoints, post-mortem]
---

# Debugger — Python & Node.js

Programmatic debugging for both languages. Start simple; escalate to remote/deep tools only when needed.

---

## Python: pdb

### When to use
- Test fails and traceback doesn't reveal why a value is wrong
- Need to step through a function and watch state mutate
- Post-mortem: inspect locals at crash site

**Don't use for:** things `print()` / `pytest -vv --tb=long --showlocals` already reveals.

### Local breakpoint (simplest)
```python
breakpoint()    # drops into (Pdb) here
```
Run normally. Remove before committing: `rg -n 'breakpoint\(\)' --type py`

### Launch script under pdb
```bash
python -m pdb script.py arg1
(Pdb) b path/to/file.py:42
(Pdb) c
```

### Debug a pytest test
```bash
# Must disable xdist — pdb doesn't work under xdist
pytest tests/file.py::test_name --pdb -p no:xdist
pytest tests/file.py::test_name --trace           # pause at test start
pytest tests/file.py --showlocals --tb=long       # just show locals without pdb
```

### pdb quick reference
| Command | Action |
|---------|--------|
| `n` | next line (step over) |
| `s` | step into |
| `r` | return from current function |
| `c` | continue |
| `w` | where (stack trace) |
| `u` / `d` | move up/down stack |
| `a` | print function args |
| `p expr` / `pp expr` | print / pretty-print |
| `b file:line` | set breakpoint |
| `b file:line, cond` | conditional breakpoint |
| `!stmt` | execute Python |
| `interact` | full REPL in current scope (Ctrl+D to exit) |
| `q` | quit |

### Post-mortem
```python
import pdb, sys
try: run_the_thing()
except Exception: pdb.post_mortem(sys.exc_info()[2])
```

---

## Python: debugpy (remote / headless)

### Setup
```bash
pip install debugpy
```

### Pattern A: Source-edit wait
```python
import debugpy
debugpy.listen(("127.0.0.1", 5678))
debugpy.wait_for_client()
debugpy.breakpoint()  # optional: pause immediately
```

### Pattern B: Launch with debugpy
```bash
python -m debugpy --listen 127.0.0.1:5678 --wait-for-client your_script.py
```

### Pattern C: Attach to running process
```bash
python -m debugpy --listen 127.0.0.1:5678 --pid <pid>
```

### remote-pdb (lighter alternative to debugpy)
```bash
pip install remote-pdb
```
```python
from remote_pdb import set_trace
set_trace(host="127.0.0.1", port=4444)  # blocks until nc connection
```
```bash
nc 127.0.0.1 4444   # get (Pdb) prompt
```

### Pitfalls (Python)
- **pdb + pytest-xdist = hangs** → always use `-p no:xdist` or `-n 0`
- **`breakpoint()` in CI** hangs → never commit; add pre-commit grep
- **`PYTHONBREAKPOINT=0`** disables all breakpoints
- **`scripts/run_tests.sh`** strips credentials and sets HOME=<tmpdir> — debug with raw pytest first
- **forking/multiprocessing** → pdb doesn't follow forks; each child needs own breakpoint

---

## Node.js: node inspect

### When to use
- Node test fails and you need intermediate state
- ui-tui crashes, want to inspect React/Ink state
- Need to see closure values `console.log` can't reach

### Quick reference (debug> prompt)
| Command | Action |
|---------|--------|
| `c` / `cont` | continue |
| `n` / `next` | step over |
| `s` / `step` | step into |
| `o` / `out` | step out |
| `sb('file.js', 42)` | set breakpoint |
| `sb('fnName')` | break on function call |
| `bt` | backtrace |
| `list(5)` | show 5 lines around current position |
| `repl` | drop into REPL in current scope (Ctrl+C to exit) |
| `exec expr` | evaluate expression |
| `restart` | restart script |
| `.exit` | quit |

### Launch
```bash
node inspect script.js                          # pause on first line
node --inspect-brk script.js                    # listen + pause on first line
node --inspect-brk $(which tsx) script.ts       # TypeScript via tsx
```

### Attach to running process
```bash
kill -SIGUSR1 <pid>       # enable inspector
node inspect -p <pid>      # attach
```

### Debug Vitest tests
```bash
node --inspect-brk ./node_modules/vitest/vitest.mjs run --no-file-parallelism src/app/foo.test.tsx
```

### Programmatic CDP (scripting)
For automated multi-breakpoint inspection, use `chrome-remote-interface`:
```bash
npm i -g chrome-remote-interface
```
Driver scripts set breakpoints by URL regex, evaluate expressions in paused frames, capture scope state — useful for headless/CI debugging.

### Pitfalls (Node.js)
- **Wrong line numbers in TS**: breakpoints hit emitted JS; use `--enable-source-maps` or break on `dist/*.js`
- **`--inspect` vs `--inspect-brk`**: `--inspect` doesn't pause; script may finish before attach
- **Port collisions**: default 9229; use `--inspect=0` (random port), read from `curl http://127.0.0.1:9229/json/list`
- **Child processes**: `--inspect` on parent doesn't inspect children; use `NODE_OPTIONS='--inspect-brk'`
- **Background kills**: if you Ctrl+C out while target is paused, target stays paused
- **`node inspect` needs pty in Hermes**: use `terminal(pty=true)` for interactive stepping

---

## Verification Checklist
- [ ] First breakpoint actually hits (not racing past or PYTHONBREAKPOINT=0)
- [ ] Source listing at pause shows right file
- [ ] Post-debug cleanup: no stray `breakpoint()` / `set_trace()` left in committed code
