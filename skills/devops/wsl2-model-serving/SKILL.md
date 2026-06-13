---
name: wsl2-model-serving
description: Serve local AI models (TTS, LLM, etc.) on Windows via WSL2 with a native Electron/Flask desktop UI. Covers subprocess management across OS boundaries, path translation, health polling, and process lifecycle.
---

# WSL2 Model Serving — Windows Desktop Pattern

## When to use
Building a self-hosted AI application where:
- The ML inference server runs inside WSL2 (Linux-native, CUDA access)
- A Python Flask proxy bridges the Windows Electron app to the WSL2 server
- Voice cloning, file uploads, or other features cross the Windows ↔ WSL boundary

## Architecture
```
Electron (Windows) → Flask proxy :7861 → SGLang-Omni/vLLM/etc :8000 (WSL2)
```

## Subprocess Management

### Spawning WSL2 processes from Electron (Windows)
Use `wsl -d <distro> -- bash -c "..."` in a `.bat` file spawned with `shell: true`:
```javascript
sglangProcess = spawn(bat, [], {
  cwd: ROOT,
  windowsHide: true,
  shell: true,
});
```

**DO NOT** use `detached: true` — it creates orphans that survive Electron exit.

### Killing WSL2 processes on quit
`child_process.kill()` on Windows kills the `.bat`'s `cmd.exe` wrapper but NOT the WSL child processes. Always add a direct WSL kill:
```javascript
app.on('before-quit', () => {
  // Kill the .bat wrapper
  if (sglangProcess) { try { sglangProcess.kill(); } catch {} }
  // Kill the actual server inside WSL
  try { execSync('wsl -d Ubuntu -- bash -c "pkill -f sgl-omni"', { timeout: 3000 }); } catch {}
});
```

### Restart button pattern
Kill old process before spawning new (don't just `return` if process exists):
```javascript
function startServer() {
  if (process) { try { process.kill(); } catch {}; process = null; }
  // ... spawn new
}
```

## Path Translation: Windows ↔ WSL
SGLang-Omni and other WSL2 servers can only read WSL paths (`/mnt/c/...`), not native Windows paths (`C:\...`). For voice clone references, translate in the Flask proxy:

```python
import re
def _wsl_path(windows_path: str) -> str:
    p = windows_path.replace('\\', '/')
    m = re.match(r'^([A-Za-z]):/', p)
    if m:
        p = f'/mnt/{m.group(1).lower()}/{p[3:]}'
    return p
```

## Flask Proxy Pattern
- Flask runs on Windows (not WSL) — direct access to Windows filesystem, nvidia-smi, etc.
- All `/api/*` endpoints talk to the WSL2 server via `http://127.0.0.1:<port>`
- Health endpoint polls both Flask and the WSL2 server
- OpenAI-compatible `/v1/audio/speech` passthrough for direct curl access

## Port Cleanup
**Critical pitfall:** Flask's dev server with `use_reloader=False` can leave orphan listeners on Windows. Before starting, always kill all processes on the port:
```
netstat -ano | grep ":7861" | grep LISTENING | awk '{system("taskkill -PID "$5" -F")}'
```

## GPU VRAM Monitoring
On Windows, call `nvidia-smi` with absolute path (subprocess may not find it from MSYS):
```python
nvsmi = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "nvidia-smi.exe")
out = subprocess.check_output([nvsmi, "--query-gpu=name,memory.used,memory.total,memory.free",
                                "--format=csv,noheader,nounits"], timeout=5, text=True)
```

## Health Polling in the Electron Renderer
**Do NOT rely on Electron IPC for health status.** IPC messages can arrive before the renderer registers listeners. Use direct HTTP:
```javascript
async function pollHealthDirect() {
  const r = await fetch('http://127.0.0.1:7861/api/health');
  const d = await r.json();
  // Update status dots from d.flask_ready, d.sglang_ready, d.gpu
}
setInterval(pollHealthDirect, 8000);
```

## CSS Pitfall: `hidden` attribute vs author `display`
When a CSS rule sets `display: flex` (e.g., `.modal { display: flex }`), JavaScript's `element.hidden = true` does nothing visually — the browser's native `[hidden] { display: none }` user-agent stylesheet has lower specificity than the author rule. Fix:
```css
.modal[hidden],
.modal[style*="display: none"] { display: none !important; }
```
And in JS, always set both:
```javascript
els.modal.hidden = true;
els.modal.style.display = 'none';
```

## WSL2 Install Pitfalls
- `set -euo pipefail` will crash on `nvidia-smi | head` — disable pipefail or use `|| true`
- `sglang[all]` has an enormous dependency tree; install `sglang` core-only, then `sglang-omni` from source
- `huggingface-cli download` can deadlock if two processes download simultaneously — kill all HF CLI processes before retrying
- `--mem-fraction-static` is NOT available in SGLang-Omni pipelines — the Higgs pipeline config rejects extra fields
- Clear stale HF download locks: `find ~/.cache/huggingface -name '*.lock' -delete`

## Known Issue: Higgs TTS Buffer Limit
See `references/higgs-tts-chunking.md` for the 4096-token buffer problem and the chunking + crossfade + gap strategy that solves it.
