---
name: safe-js-editing
description: Pitfalls and safe patterns for editing JavaScript/TypeScript files with Hermes tools (write_file, execute_code, patch). Covers comment hazards, backslash escaping, and verification workflow.
---

## Trigger
Use when editing `.js`, `.mjs`, `.ts`, `.jsx`, or `.tsx` files via `write_file`, `execute_code`, or `patch` — especially when the edit involves regex literals, `//` comments, or backslash-heavy patterns.

## Core Pitfalls

### 1. Inline `//` comments eat subsequent code
When `write_file` writes a single line containing `//`, everything after the `//` on that line is a comment. Multi-statement lines with inline comments lose all trailing code.

**WRONG** (everything after `//` is commented out):
```js
function foo(){ doA(); doB(); // explanation doC(); doD(); }
```
Only `doA(); doB();` executes. `doC(); doD();` is lost.

**RIGHT** — break `//` onto its own line:
```js
function foo(){ doA(); doB(); doC(); doD(); }
// explanation
```

### 2. Backslash doubling in `write_file` content
The `write_file` tool may double backslashes in the `content` parameter. `\\s` becomes `\\\\s` in the written file. After writing, always verify with `node --check` or `read_file` + `od -c`.

**Remedy**: Use `execute_code` with Python for precise byte-level control when backslashes are critical (regex literals, escape sequences). Write via Python's `open(file, 'wb')` with raw bytes.

### 3. `*/` inside regex literals
JavaScript regex literals containing `*/` (e.g., `/\s*/`) can be misparsed as closing a block comment by Node.js `--check` and some parsers. Replace `*` with `{0,}` or escape the `/` as `\/` to avoid the collision.

**WRONG**: `/^[\s]*pattern\s*/` — the `*/` at the end looks like a comment close.
**RIGHT**: `/^[\s]{0,}pattern\s{0,}/` or `/^[\s]*pattern\s*\//`

### 4. Single-line regex split across physical lines
Regex literals cannot span multiple lines. A regex like `[\\r\\n]+` split across two lines (with actual CR/LF characters) is a syntax error. Use `[\\r\\n]+` on a single line.

### 5. Incomplete object property propagation
When adding a new array property to a shared object (like a `meshes` collection), you must update THREE locations: the object declaration, the cleanup/destruction loop, and the reset/re-initialization block. Forgetting any one causes `TypeError: X is not iterable` at runtime — a silent per-frame error flood in animation loops.

```js
// BAD — added foliage to animate() but forgot declaration + cleanup
const meshes = { branches:[], labels:[] };
function resetMeshes(){
  meshes.branches.forEach(m=>scene.remove(m));
  meshes.labels.forEach(m=>scene.remove(m));
  meshes.branches=[]; meshes.labels=[];
}
function animate(){
  for(var fg of meshes.foliage){ ... }  // CRASH: foliage is undefined
}
```

**Fix checklist** when adding a new `meshes.X` array:
1. Add `X:[]` to the `const meshes = {...}` declaration
2. Add `meshes.X.forEach(m=>scene.remove(m))` to the cleanup block
3. Add `meshes.X=[]` to the reset block

## Safe Edit Workflow

1. **Write the edit** via `execute_code` (Python) for control over escaping, not `write_file` for backslash-heavy JS
2. **Verify syntax** immediately: `node --check <file>` (use `.mjs` extension for ESM)
3. **Test in browser** if it's a client-side module — browsers catch different errors than Node
4. **If syntax fails**, binary-search with `node --check` on progressively truncated versions to isolate the offending line

## Binary-Search Syntax Debugging
When `node --check` reports "Unexpected end of input" or "Unexpected token" without a useful line number:

```python
# Write progressively longer prefixes to isolate the failing line
for off in range(min_line, max_line):
    test = '\n'.join(lines[:off])
    # write to temp .mjs file, run node --check
```

The first `off` that flips from OK→ERROR pinpoints the problematic function/block.
