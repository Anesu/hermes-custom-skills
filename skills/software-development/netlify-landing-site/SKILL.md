---
name: netlify-landing-site
description: Build and ship premium static landing sites on Netlify — Forms-to-email, GA4/Ads conversion wiring, local verification, GitHub push without gh CLI.
version: 1.0.0
metadata:
  hermes:
    tags: [netlify, cloudflare-pages, landing-page, static-site, forms, formspree, analytics, deployment, web-design]
    related_skills: [claude-design, github-repo-management]
---

# Netlify Landing Site — Build & Launch

Use when the user wants a marketing/landing site built and deployed (Netlify, Cloudflare Pages, or similar static host), especially with a lead-capture form and conversion tracking. Also use when migrating a site between static hosts (e.g. Netlify → Cloudflare Pages). Pair with `claude-design` for the design process itself; this skill covers the launch plumbing and verification.

## Workflow

1. **Brand research first.** `web_extract` the existing site (including pricing/sub-pages) and `web_search` socials. Lift real pricing, copy fragments, brand quotes, and CDN image URLs — never invent prices or testimonials.
2. **Build as a single self-contained HTML file** (embedded CSS/JS, CSS variables as design tokens, Google Fonts only). Plus `thanks.html`, `netlify.toml`, `README.md`.
3. **Wire Netlify Forms correctly** (see snippet below — all four parts are required).
4. **Analytics placeholders**: commented GA4 + Google Ads blocks in `<head>` of BOTH pages. The Ads `conversion` event fires ONLY on `thanks.html` (one fire per lead). Form `action="/thanks.html"` guarantees the redirect.
5. **Verify in browser locally** (see Pitfalls — file:// is blocked).
6. **Push to GitHub**, user connects repo in Netlify UI (their preferred flow), or `npx netlify deploy --prod --dir .` if they auth.

When adding subpages (about, terms, FAQ…) or making the site editable by weak LLMs / non-experts, load `references/llm-safe-editing.md` — SAFE-EDIT fences, AGENTS.md recipe structure, shared-subpage CSS architecture, and the `scripts/check_site.py` validator template.

For SEO / structured data / "make the site agent-friendly" requests, load `references/agent-discoverability.md` — JSON-LD @graph (LocalBusiness + Offers + FAQPage), llms.txt, robots/sitemap, og:image link previews, TikTok embed pattern, and the three-place fact-sync rule.

## Netlify Forms — required parts

```html
<form name="booking" method="POST" action="/thanks.html"
      data-netlify="true" netlify-honeypot="bot-field">
  <input type="hidden" name="form-name" value="booking">
  <p hidden><label>Don't fill this out: <input name="bot-field"></label></p>
  ...
</form>
```

- The hidden `form-name` input is mandatory or submissions silently drop.
- Forms only work on the deployed site, never locally — say so in the README.
- Email delivery is configured in the dashboard (Forms → Form notifications → Email), NOT in code. Always include this step in the README and tell the user to do a live test submission.
- Free tier: 100 submissions/month.

## netlify.toml baseline

```toml
[build]
  publish = "."
[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
[[redirects]]
  from = "/thanks"
  to = "/thanks.html"
  status = 200
```

## Local verification

1. `terminal(background=true)`: `python -m http.server 8765` with `workdir` set to the site folder.
2. `browser_navigate` to `http://localhost:8765/index.html`.
3. Check `browser_console` for JS errors, then `browser_vision` on hero, pricing, and form sections. Use `browser_console` expression `window.scrollTo(0, document.querySelector('#section').offsetTop)` to position before each screenshot.
4. Kill the server process when done.

## GitHub push without gh CLI

On hosts where `gh` is absent but git credentials exist in the credential manager:

```bash
CRED=$(printf 'protocol=https\nhost=github.com\n\n' | git credential fill)
GH_USER=$(echo "$CRED" | grep '^username=' | cut -d= -f2)
GH_TOKEN=$(echo "$CRED" | grep '^password=' | cut -d= -f2)
curl -s -X POST -H "Authorization: token $GH_TOKEN" \
  https://api.github.com/user/repos \
  -d '{"name":"REPO","description":"...","private":false}'
git remote add origin https://github.com/$GH_USER/REPO.git
git push -u origin main
```

Never echo the token; pipe through `sed 's/=.\{4\}.*/=****/'` when sanity-checking credentials.

## Pitfalls

- **`browser_navigate` to `file://` URLs fails** (`ERR_BLOCKED_BY_ADMINISTRATOR` on this host). Always serve via local `python -m http.server` instead.
- **Hot-linked images from the client's old CDN will break** if that site is retired. Flag in README; recommend downloading into `images/` before old site shutdown.
- **Ads conversion on the form page = double/false counting.** Conversion tag belongs on the thank-you page only; add `noindex` meta to it.
- `scroll reveals`: gate behind `prefers-reduced-motion` and add an IntersectionObserver fallback that just shows everything, or content is invisible for some users.
- Ask the user how they want to deploy (CLI auth / drag-drop / Git→Netlify) via `clarify` rather than assuming — auth flows need their participation.

## Cloudflare Pages deployment (alternative)

When the user wants Cloudflare Pages instead of Netlify — or needs to migrate an existing Netlify site — follow this mapping:

| Netlify | Cloudflare Pages |
|---|---|
| `netlify.toml` headers | `_headers` file |
| `netlify.toml` redirects | `_redirects` file |
| `data-netlify="true"` form | Formspree (`action="https://formspree.io/f/FORM_ID"`) |
| Hidden `form-name` input | Removed (not needed) |
| Dashboard email config | Formspree dashboard email config |

### `_redirects` format (space-separated, no TOML)

```
/thanks   /thanks.html   200
/about    /about.html    200
/terms    /terms.html    200
/gallery  /gallery.html  200
/*        /404.html      404
```

### `_headers` format

```
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()

/*.html
  Cache-Control: public, max-age=0, must-revalidate
```

### Formspree form (replaces Netlify Forms)

Formspree free tier: 50 submissions/month. **The free tier blocks custom redirect URLs** — use the fetch+redirect bypass below instead of paying for an upgrade.

```html
<form class="book" name="booking" method="POST" action="https://formspree.io/f/FORM_ID">
  <input type="hidden" name="_subject" value="New booking enquiry">
  <p hidden><label>Don't fill this out: <input name="bot-field"></label></p>
  <!-- all visible fields unchanged: name, email, phone, event_date, etc. -->
  <div id="form-status" class="form-status" role="alert" hidden></div>
  <button type="submit">Submit</button>
</form>
```

### Formspree fetch+redirect bypass (free tier — no upgrade needed)

Formspree paywalls the `_next` redirect on the free tier. Use JavaScript `fetch()` to submit the form, then redirect with `window.location.href` on success:

```html
<script>
  (function () {
    var form = document.forms.booking;
    var btn = form.querySelector('button[type="submit"]');
    var status = document.getElementById('form-status');
    var origText = btn.textContent.trim();

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      status.hidden = true;
      btn.disabled = true;
      btn.innerHTML = 'Sending\u2026';

      fetch('https://formspree.io/f/FORM_ID', {
        method: 'POST',
        body: new FormData(form),
        headers: { Accept: 'application/json' }
      })
        .then(function (r) {
          if (r.ok) {
            window.location.href = '/thanks.html';
          } else {
            return r.json().then(function (data) {
              throw new Error(data.error || 'Something went wrong. Try again.');
            });
          }
        })
        .catch(function (err) {
          status.textContent = err.message;
          status.hidden = false;
          btn.disabled = false;
          btn.innerHTML = origText;
        });
    });
  })();
</script>
```

The form also keeps its `action` attribute — this provides a no-JS fallback that submits to Formspree's default success page (acceptable for the <1% of users without JavaScript).

### Validator updates

When switching from Netlify to Cloudflare/Formspree, update `scripts/check.py`:
- Replace `data-netlify="true"` check → `action="https://formspree.io/f/`
- Replace `name="form-name"` check → remove (not needed)
- Keep honeypot check (`name="bot-field"`)

### Pitfall: path resolution on Windows

When writing files to a path like `/c/Users/Anesu/Documents/GitHub/mirror2memory/_redirects`, Hermes may resolve it to `C:\c\Users\...` (doubled drive letter). Always use Windows-style absolute paths (`C:\Users\...`) with `write_file` and `patch` on Windows hosts.

## Support files

- `references/mirror2memory-brand.md` — brand facts, pricing, design tokens, and repo location for the user's own business (Mirror 2 Memory), for future iterations on that site.
- `references/llm-safe-editing.md` — the LLM-safe editing layer: SAFE-EDIT comment fences, AGENTS.md structure for weak-model editors, subpage architecture when index.html is standalone, validator design. Apply whenever the user wants the site maintainable by small models or non-experts.
- `references/agent-discoverability.md` — agent-first SEO layer: JSON-LD @graph with real-price Offers and FAQPage (visible-FAQ parity required), llms.txt fact sheet, robots/sitemap, og:image, official TikTok embed, custom-404 redirect ordering.
- `scripts/check_site.py` — stdlib-only static-site validator (balanced tags, SAFE-EDIT pairing, broken links, required structural strings, nav/footer consistency, JSON-LD parses, TikTok cite/data-video-id agreement). Copy into the target repo as `scripts/check.py`, adjust the PAGES list and required-strings map, then SELF-TEST it by deliberately breaking a tag + image ref and confirming red→green.
