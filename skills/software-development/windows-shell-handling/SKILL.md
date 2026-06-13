---
name: windows-shell-handling
description: Operate the agent correctly on Windows hosts where the user works in PowerShell but the agent's terminal tool runs in git-bash / MSYS. Covers path translation (tilde expansion, separator handling, $HOME), the bash-vs-PowerShell syntax split, the PTY-vs-user-interactive-input pitfall, and the right way to hand long commands to the user. Use whenever the user is on a Windows host and asks the agent to run a command, write a script, or hand them an instruction to run.
---

# Windows Shell Handling

Operating principles for an agent on a Windows host where the agent's `terminal` tool runs through **git-bash / MSYS** but the **user themselves works in PowerShell** (the default Windows terminal). The two shells disagree on path expansion, separators, and quoting — the agent must produce commands and instructions that survive both.

## 1. The path translation matrix

| Form | Bash / MSYS (agent's terminal) | PowerShell (user's terminal) | Verdict |
|---|---|---|---|
| `~/.hermes/scripts/foo.py` | Works (tilde expands to `/c/Users/<user>/`) | **FAILS** — `~` is literal, `\` in path becomes `\`+`\` literal | Never use this form in user-facing instructions |
| `$HOME/.hermes/scripts/foo.py` | Works | Works (PowerShell recognises `$HOME`) | Safe in both |
| `/c/Users/Anesu/.hermes/scripts/foo.py` | Works (MSYS POSIX form) | **FAILS** | Bash-only |
| `C:\Users\Anesu\.hermes\scripts\foo.py` | Works (MSYS rewrites) | Works | **Safest for user-facing instructions** |
| `"$HOME/.hermes/scripts/foo.py"` (quoted) | Works | Works | Safe in both |
| `python -c "import os; print(os.environ['HOME'])"` | Works | Works | Diagnostic, not command |

**Default rule for user-facing copy-pasteable commands:** use the **absolute Windows path with backslashes** (`C:\Users\Anesu\.hermes\scripts\foo.py`) or the **`$HOME/...` form with forward slashes**. Never lead with `~/...` when the instruction is going to the user.

**Default rule for commands the agent runs via `terminal`:** bash/MSYS syntax is fine. The agent's terminal is git-bash, not PowerShell.

**Default rule for the agent's FILE tools (`write_file`, `patch`, `read_file`):** use the **native Windows absolute path with backslashes** (`C:\Users\Anesu\project\game.js`), NOT the MSYS POSIX form. The file tools do NOT run through MSYS path translation the way `terminal` does.

### 1a. The `/c/...` file-tool mangling trap (high-frequency, silent)

Passing an MSYS path like `/c/Users/Anesu/project/game.js` to `write_file` or `patch` does **not** resolve to the C: drive. The leading `/c/` is treated as a **literal top-level directory**, so the file lands at `C:\c\Users\Anesu\project\game.js` — a real, wrong location, with no error. The tool returns success and a `_warning` that the path resolved OUTSIDE the workspace; READ THAT WARNING.

| Path passed to a file tool | Where it actually lands | Verdict |
|---|---|---|
| `/c/Users/Anesu/project/game.js` | `C:\c\Users\Anesu\project\game.js` (literal `c` dir) | **WRONG — silent misfile** |
| `C:\Users\Anesu\project\game.js` | `C:\Users\Anesu\project\game.js` | **Correct** |
| `~/project/game.js` | depends on tool; unreliable for file tools | Avoid |

**Rule:** the `terminal` tool understands `/c/Users/...` (MSYS rewrites it); the **file tools do not**. Use `C:\Users\<user>\...` with backslashes for every `write_file`/`patch`/`read_file` call on a Windows host. If you already misfiled, recover by `cp`-ing inside `terminal` (where `/c/...` works) to the correct native path, then delete the stray `C:\c\` tree.

## 2. The bash-vs-PowerShell syntax split

Things the user has to type in PowerShell that are NOT bash:

- **Environment variables:** `$env:FOO` (PowerShell) vs `$FOO` (bash). Use `$env:FOO` in user-facing copy.
- **Process listing:** `Get-Process` vs `ps`. PowerShell aliases (`ps`, `ls`, `cat`) exist but behave differently — `cat` in PowerShell is an alias for `Get-Content` with byte semantics, not stream concat.
- **File listing:** `Get-ChildItem` or `ls`/`dir` — but in PowerShell `ls` returns `FileInfo` objects, not text streams. Don't pipe `ls` output to a text-processing pipeline without first converting.
- **String quoting:** PowerShell prefers double quotes; backtick is escape char. Bash prefers single quotes; backslash is escape char.
- **Path separators inside string literals:** in PowerShell, `\` inside double-quoted strings IS an escape char. Use forward slashes or single-quote the path.

When the agent is asked to write a script that the user will run directly, **prefer Python or cross-shell syntax** over shell-specific tricks. When the user pastes back an error trace, identify the source shell by the path style (forward-slash = bash, backslash = PowerShell) before diagnosing.

## 3. The PTY-vs-user-interactive-input pitfall

**The most common mistake:** the agent starts an interactive CLI tool (drill, REPL, prompt-based installer) via its own `terminal(pty=true)` call, expecting the user to drive it. The user cannot drive it — the PTY is bound to the agent's process, not the user's. The agent's tool returns "aborted" or hangs on the first prompt.

**Right pattern:** if a tool needs the user to type responses:

1. **Hand the user the command as a copy-pasteable line.** Do not execute it via `terminal`.
2. **Explain in one line what the tool does and how to stop it** (Ctrl-C, `:q`, etc.).
3. **Tell the user what to do next** (paste output back, check a file, run a follow-up command).
4. **Optionally script the post-mortem** — write a tiny verification script the agent can run after the user finishes, so progress / state can be inspected.

**Wrong pattern:** starting a quiz, drill, REPL, or any stdin-driven tool from agent context. Even with `pty=true`, the input never reaches the user.

**Diagnostic:** if the user reports "the command just printed the first question and exited" or "I never got to type anything", the agent is in the PTY trap. Apologise briefly, hand them the command, and move on. Do not retry the same approach.

## 4. Handing long commands to the user

When the user needs to run something themselves:

- **Wrap multi-line in a code block with shell hint** (```` ```powershell ```` or ```` ```bash ````). The hint matters because copy-paste targets the right language.
- **For long command lines, prefer a one-liner** the user can paste in one go. If it has to span lines, use the shell's continuation character explicitly (`^` in PowerShell, `\` in bash) and number each line in the explanation.
- **Prefer a one-line absolute path or `$HOME/...` form** for paths in user-facing copy. See §1.
- **If the command will be re-run frequently, suggest a shim** — a `.bat` (Windows) or `.ps1` (PowerShell) file in a stable location that wraps the longer command. This is the long-term fix for "I have to remember the path" friction.

## 5. Choosing the agent's own shell

The agent's `terminal` tool defaults to git-bash on Windows (POSIX syntax, MSYS path translation, `$HOME` expansion). Use it freely. Things to know:

- **POSIX paths work:** `ls $HOME/.hermes/`, `cat ~/.bashrc`.
- **Windows tools are callable:** `python`, `npx`, `git`, `gh` all resolve via PATH.
- **PowerShell cmdlets are NOT first-class:** `Get-ChildItem` may work, but `Select-String -Path ...` won't — the agent's shell is bash, not PowerShell. If you need a PowerShell-specific feature, run it via `powershell -Command "..."` explicitly.
- **`which`/`where` confusion:** `which python` works in bash. `where.exe python` is the PowerShell equivalent. The agent's `which` is reliable.
- **Background processes:** use `background=true` on the agent's `terminal` tool, not `nohup &` / `disown` / `setsid`. The agent's process tracker is the source of truth.

## 6. When to escalate to a reference

The `references/` directory has worked examples and edge cases:

- `references/path-handling.md` — concrete path-translation examples for the most common traps (hermes scripts, uv python, git repos).
- `references/powershell-vs-git-bash.md` — when to write code that runs in either shell, with a worked example.
- `references/child-process-windows-pitfalls.md` — three real Windows subprocess bugs (EINVAL on .bat spawn, `process.execPath` semantics, PowerShell encoding corruption) with transcripts and fixes. See §8 of this file.
- `references/reliable-js-file-editing.md` — the `write_file` backslash-doubling bug, the `//` comment corruption pattern, and the sequential-verify-after-each deployment workflow for JavaScript files on Windows. See §12.

## 7. Quick diagnostic checklist

When a command fails on a Windows host, check in this order:

1. **Path style** — forward or back slash? `$HOME` or `~`? Absolute or relative?
2. **Shell syntax** — `$FOO` or `$env:FOO`? `which` or `where`? Single or double quotes?
3. **PTY / interactive** — was the agent trying to drive a tool that needs the user?
4. **Permissions / execution policy** — PowerShell `Set-ExecutionPolicy`, blocked `npm` scripts, missing `--yes`.
5. **PATH / venv** — `which python` and `python --version` should agree; if not, the venv is detached.

Most Windows-host failures are #1, #2, or #3. The rest are real bugs.

## 8. `child_process.spawn` on Windows — three real bugs

When the agent spawns subprocesses from Node.js (or any runtime that uses libuv) on Windows, three patterns break silently. All three are non-obvious and only show up at runtime.

### 8.1 Spawning a `.bat` / `.cmd` file: `shell: true` is required

```javascript
// WRONG — throws EINVAL at runtime on Windows
spawn('scripts/start-server.bat', [], { shell: false });

// RIGHT — required to invoke through cmd.exe
spawn('scripts/start-server.bat', [], { shell: true });
```

Without `shell: true`, Node tries to exec the `.bat` directly as a binary. Windows requires `cmd.exe` to interpret batch files. The error is `EINVAL` (invalid argument) with no useful message. **Always set `shell: true` for `.bat` / `.cmd` on Windows.** The same applies to `child_process.exec` if you forget `shell: true` for a batch file path.

If you need `shell: false` for security (no shell injection), invoke the binary inside the .bat (e.g. `cmd /c python server.py`) and pass arguments via the .bat's own parameter handling, or use `node`'s `process.execPath` directly.

### 8.2 `process.execPath` is wrong in dev, right in production

In a packaged Electron app, `process.execPath` points to the Electron binary — useful for "relaunch myself" patterns. In **dev mode** (`electron .` or `npm start`), `process.execPath` points to **node.exe**. Any code that uses `process.execPath` as a "relaunch the app" target is silently broken in dev.

**Symptom:** a desktop shortcut points to `node.exe`; the user double-clicks it, Node opens, no GUI. Or `process.execPath` is used as a `targetPath` in a Windows shortcut, embedding the wrong icon.

**Fix:** when you need the "this app's binary" path:
- In dev: `path.join(__dirname, '..', 'node_modules', 'electron', 'dist', 'electron.exe')` (Electron only)
- In prod: `process.execPath` works
- Or: have your shortcut point at an **intermediate launcher** (a `.vbs` or `.bat` shim) that handles both cases. The `.vbs`/`wscript.exe` pattern is the cleanest — wscript.exe exists on every Windows install, takes the shim as a single argument, and works identically in dev and prod.

### 8.3 PowerShell scripts: encoding corruption on non-ASCII characters

PowerShell on Windows uses the **system codepage (cp1252) by default**, not UTF-8. Any non-ASCII character in a `.ps1` script (em-dash `—`, smart quotes, accented letters, emoji) gets **silently mangled** when the script runs — the file looks correct in the editor, but PowerShell sees `?` (or worse, a different wrong character) and the parser fails with a cryptic `Unexpected token` error pointing at the wrong place.

**Symptom:** the .ps1 parses fine in ISE/VS Code, but `powershell -File script.ps1` fails with `Unexpected token 'desktop'` immediately after a string literal that contains an em-dash.

**Three fixes, in order of preference:**

1. **Avoid non-ASCII in .ps1 files.** Replace em-dash with `-` or `--`, smart quotes with straight quotes. Cheapest fix; zero runtime cost.
2. **Save the .ps1 as UTF-8 with BOM.** Editors usually have this option. PowerShell 5+ reads the BOM and decodes correctly.
3. **Add `chcp 65001 > nul` at the top of the .ps1** to switch the active codepage to UTF-8 for the script's duration. Fragile (depends on terminal codepage), but works when you can't control the file encoding.

Option 1 is right 95% of the time. Use option 2 if you need to preserve non-ASCII in user-facing strings the script prints.

## 9. WSL2 invocation from the agent's terminal

When the agent needs to run commands inside WSL2 (e.g. to start a model server, install packages, or run a health check), the invocation form matters. WSL2 has three distinct entry points and they DO NOT all work the same way after a distro reinstall or crash recovery.

### 9.1 The reliable form: `wsl -d <distro> -- bash -c "..."`

```bash
wsl -d Ubuntu -- bash -c "echo alive; whoami; uptime"
```

This is the **only form that reliably works** across fresh installs, crash recoveries, and non-interactive agent sessions. It explicitly names the distribution (`-d Ubuntu`) and the shell (`-- bash`), avoiding the default-shell resolution that breaks when the user account isn't fully initialised.

### 9.2 The forms that break

| Form | Why it fails |
|---|---|
| `wsl bash -c "..."` | Depends on a default distro and user shell — breaks after `wsl --unregister` + reinstall when user isn't yet logged in |
| `wsl -e bash -c "..."` | `-e` bypasses the user's login shell; after a distro crash, the user may not exist in the NSS database (`getpwnam fails`) — returns `User not found` / `WSL_E_USER_NOT_FOUND` |
| `wsl` (interactive) | Agent cannot drive interactive sessions — this is for the user only |

**Rule:** always use `wsl -d <distro> -- bash -c "..."` when the agent invokes WSL. It survives distro reinstallation and non-interactive contexts.

### 9.3 MSYS/git-bash curl cannot reach WSL2 localhost

**Symptom:** `curl http://127.0.0.1:8000/v1/models` from the agent's MSYS terminal returns `Connection refused` or `HTTP 000`, but the server IS listening (confirmed by `netstat` and by the server logs showing successful requests from a browser).

**Root cause:** MSYS/git-bash uses its own socket layer that does not reliably bridge to WSL2's virtual network adapter. WSL2's `localhost` is forwarded to Windows by the WSL2 virtual switch, but the MSYS runtime routes through a different path.

**Fix:** Use Python's `urllib` from the Windows-side Python binary to reach WSL2 ports:
```python
import urllib.request, json
r = urllib.request.urlopen('http://127.0.0.1:8000/v1/models')
d = json.loads(r.read())
```
Or invoke curl **inside WSL** via the reliable form:
```bash
wsl -d Ubuntu -- bash -c "curl -s http://127.0.0.1:8000/v1/models"
```

**Don't bother troubleshooting** MSYS curl → WSL2 networking. It's a known limitation. Use the Windows Python urllib path or invoke the tool inside WSL.

### 9.4 WSL crash recovery sequence

When WSL becomes unresponsive after an I/O crash (dual process writes, SIGPIPE cascade, etc.), test with the reliable form first. If that also fails:

1. `wsl --shutdown` — kills the WSL service
2. `wsl -d Ubuntu -- bash -c "echo alive"` — test recovery
3. If "Catastrophic failure" / `E_UNEXPECTED`: `wsl --unregister Ubuntu && wsl --install -d Ubuntu`
4. Full unregister is **destructive** — all data in the WSL virtual disk is lost

Prevention: never run two concurrent processes that write to the same file on the WSL virtual disk (e.g. two `huggingface-cli download` commands for the same model). Always `pkill -f <process>` and clean stale lock files before retrying a failed download.

## 10. Quick reference: what to do in a desktop-app launcher

When wrapping a Python/ML backend in an Electron (or Tauri, or any GUI) shell on Windows, the working pattern is:

```
app.exe (Electron, packaged)
  └─> spawn .bat (shell: true) to start backend
  └─> health-poll backend HTTP endpoint
  └─> show window once backend is up

Desktop .lnk shortcut
  └─> wscript.exe "app\scripts\launch.vbs"   ← .vbs is a silent wrapper
        └─> runs the .bat that starts the .exe
```

The `.vbs` shim avoids the console-window flash that a `.bat` shortcut would produce, and `wscript.exe` exists on every Windows install so the shortcut works regardless of how the user installed the app. See the `desktop-app-shell-windows` skill for the full template.

## 11. Port lifecycle on Windows: finding, freeing, and restarting

When a server (Node, Python, any backend) dies but the port is still held, or when you need to restart a server and the old process is still bound, use this workflow. It works from both the agent's terminal (git-bash) and the user's PowerShell.

### 11.1 Find what's on a port

```bash
# Works in git-bash (agent's terminal)
netstat -ano | grep ':8130' | grep LISTENING | awk '{print $5}' | sort -u
```

The `$5` column is the PID on Windows (verified against `netstat -ano` output format). Each PID is one process holding that port.

### 11.2 Kill everything on a port (one-liner)

```bash
for pid in $(netstat -ano | grep ':8130' | grep LISTENING | awk '{print $5}' | sort -u); do
  taskkill //F //PID $pid
done
```

Key details:
- `taskkill //F //PID` (double forward slash) because bash eats single slashes. In PowerShell the user would type `taskkill /F /PID`.
- If nothing is on the port, the loop is a no-op — no error.
- Always follow with `sleep 1` and a check before restarting.

### 11.3 Confirm port is free

```bash
netstat -ano | grep ':8130' | grep LISTENING || echo "PORT FREE"
```

If you skip this and the port isn't free, the next server start fails with `EADDRINUSE`. On Windows, `EADDRINUSE` does NOT mean the port will free itself soon — it stays held until the process is killed.

### 11.4 Restart a server (the reliable sequence)

```bash
# 1. Kill old
for pid in $(netstat -ano | grep ':8130' | grep LISTENING | awk '{print $5}' | sort -u); do
  taskkill //F //PID $pid 2>/dev/null
done
sleep 1

# 2. Verify port free (or fail early with a clear message)
netstat -ano | grep ':8130' | grep LISTENING && echo "PORT STILL HELD" && exit 1

# 3. Start the new server
cd /c/Users/Anesu/project && node server.js
```

Add `sleep 3` after starting and verify with `curl` before continuing.

### 11.5 Background servers with the agent's terminal tool

The agent's own `terminal` tool has a `background=true` parameter. Use this for long-lived servers. Do NOT use shell-level background operators (`&`, `nohup`, `disown`, `setsid`) in the agent's terminal — the tool manages process lifecycle itself.

```javascript
// Agent uses this:
terminal(command="node server.js", background=true)

// NOT this:
terminal(command="node server.js &")
```

After starting in background, ALWAYS verify with a health check:

```bash
# Wait for startup, then probe
sleep 3 && curl -s -m 5 -o /dev/null -w "HTTP %{http_code}" http://localhost:8130/api/health
```

Use `process(action='poll', session_id='...')` to check on background processes, and `process(action='wait', session_id='...', timeout=...)` to block until they exit.

### 11.6 The foreground `&` rejection

On Windows, `terminal` rejects commands that contain `&` in foreground mode — this is a safety guard against backgrounding via shell syntax. Use `terminal(background=true)` for any command that needs to keep running. This is the correct pattern, not a workaround.

## 12. Reliable JavaScript file editing — `write_file` backslash bug and `//` comment corruption

See `references/reliable-js-file-editing.md` for the full reference. Quick summary:

- **`write_file` doubles backslashes** in regex patterns (`\s` → `\\s`). Use `execute_code` (Python) or `patch` for files containing regex literals.
- **`//` comments in replacement strings eat subsequent code** when the replacement lands mid-line. Never include `//` comments in string replacements for JS files.
- **Verify after every change**: `node --check` → browser load → check console. Sequential deployment prevents cascading failures.
