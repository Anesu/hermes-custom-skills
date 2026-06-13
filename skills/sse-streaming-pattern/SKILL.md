---
name: sse-streaming-pattern
description: Implement Server-Sent Events for progressive streaming from Flask/Python backends to browser clients. Use when building streaming progress, real-time batch processing feedback, or replacing polling with push. Covers Flask SSE endpoints, ReadableStream consumers, AbortController cancellation, and common gotchas (CSP, CORS, proxy buffering).
---

# SSE Streaming Pattern

Push real-time progress from a long-running backend operation to the browser. Each unit of work completes → an event lands in the client. No polling, no websocket overhead.

## When to use

- Batch processing where the user needs per-item progress (TTS sentence-by-sentence, file processing, data export)
- Replacing "spinner for 90 seconds while server crunches" UX
- Any sequential pipeline where intermediate results are independently useful

## Server: Flask SSE endpoint

```python
import json
from flask import Response, stream_with_context

@app.route("/api/batch/stream", methods=["POST"])
def api_batch_stream():
    data = request.get_json(force=True)
    items = get_items(data)  # your item extraction logic

    def generate():
        # 1. Initial event: total count so client can pre-allocate
        yield f"data: {json.dumps({'type': 'start', 'total': len(items)})}\n\n"

        for i, item in enumerate(items):
            try:
                result = process_item(item)  # your work
                event = {"type": "item_done", "index": i, "result": result}
                yield f"data: {json.dumps(event)}\n\n"
            except GeneratorExit:
                # Client disconnected / cancelled
                logger.info("Stream cancelled at item %d/%d", i + 1, len(items))
                return
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'index': i, 'error': str(e)})}\n\n"

        # Final event
        yield f"data: {json.dumps({'type': 'done', 'total': len(items)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # critical for nginx proxies
        },
    )
```

**Key points:**
- `stream_with_context()` keeps Flask's request context alive inside the generator
- `GeneratorExit` catch handles client disconnect (AbortController on the browser side)
- `X-Accel-Buffering: no` prevents nginx from buffering the entire response
- SSE format is strict: `data: <json>\n\n` — double newline is the frame delimiter

## Client: ReadableStream SSE consumer

`EventSource` only supports GET requests. For POST-based streaming, use `fetch()` with a `ReadableStream` reader:

```javascript
async function streamBatch(body) {
  const controller = new AbortController();

  const res = await fetch('/api/batch/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: controller.signal,
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';  // keep incomplete line

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const event = JSON.parse(line.slice(6));

      switch (event.type) {
        case 'start':
          // Pre-allocate UI: event.total items
          break;
        case 'item_done':
          // Update item event.index in the UI
          break;
        case 'error':
          // Mark item event.index as failed
          break;
        case 'done':
          // All items processed
          break;
      }
    }
  }

  return controller;  // caller can controller.abort() to cancel
}
```

**Key points:**
- `ReadableStream` is available in all modern browsers and Electron
- The `buffer` pattern handles SSE frames that span chunk boundaries
- `decoder.decode(value, { stream: true })` — the `stream: true` flag prevents multi-byte character corruption across chunks
- Return the `AbortController` so the caller can cancel

## Cancel button pattern

```javascript
let abortController = null;

function startBatch() {
  abortController = new AbortController();
  button.textContent = 'Cancel';
  button.classList.add('btn-danger');
  // ... start the stream ...

  // In the finally block:
  abortController = null;
  button.textContent = 'Synthesise All';
  button.classList.remove('btn-danger');
}

button.addEventListener('click', () => {
  if (abortController) {
    abortController.abort();  // triggers AbortError in fetch
    abortController = null;
  } else {
    startBatch();
  }
});
```

## Gotchas

### Flask output is empty → 404/500 but works in test client
**Cause:** Stale `.pyc` bytecode cache. Flask's reloader doesn't always catch file changes when started via a parent process (Electron, systemd, etc.).
**Fix:** `find . -name '__pycache__' -exec rm -rf {} +` and restart Flask.

### SSE works in curl but not in browser
**Cause:** Nginx or reverse proxy buffering the response. Add `X-Accel-Buffering: no` header.
Also check: `proxy_buffering off;` in nginx config.

### Events arrive all at once instead of progressively
**Cause:** The server isn't flushing. Flask/Werkzeug flushes automatically on each `yield`, but other WSGI servers may buffer. For gunicorn: ensure `--worker-class sync` or use `gevent`.

### CSP blocks EventSource/fetch to different port
**Cause:** Content-Security-Policy `connect-src` or `media-src` doesn't include the backend origin.
**Fix:** Add the backend URL to the relevant CSP directive. For Electron apps loading from `file://`, the backend is always a different origin.

### Audio/media files served from different port
**Cause:** In Electron, `loadFile()` sets origin to `file://`. Relative URLs like `/audio/foo.wav` resolve against `file:///audio/foo.wav` — which doesn't exist.
**Fix:** Always use absolute URLs: `${flaskUrl}/audio/foo.wav`. Also ensure CSP `media-src` includes the backend origin.

## References

- [references/higgs-tts-implementation.md](references/higgs-tts-implementation.md) — Concrete SSE implementation from Rungano (Higgs-TTS) with Flask + Electron
