---
name: landing-page-launch
description: Build, verify, and ship premium small-business landing pages — static HTML, Netlify Forms, GA4/Ads conversion tracking, social embeds, GitHub→Netlify deploy.
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [landing-page, netlify, static-site, forms, analytics, instagram, deploy]
    related_skills: [claude-design, popular-web-designs, github-repo-management]
---

# Landing Page Launch

End-to-end playbook for building and shipping a premium landing site for a small business (used for Mirror 2 Memory, mirror2memory.au). Pair with `claude-design` for visual taste/process; this skill carries the launch mechanics and the user's known preferences.

## Trigger
"Build a landing page / website for X", "deploy to Netlify", "add a booking/contact form", "make our site", redesigns of small-business marketing sites.

For Cloudflare Pages deployments or Netlify-to-Cloudflare migrations: load `netlify-landing-site` — it has the `_redirects`/`_headers` format, Formspree form replacement, and the fetch+redirect bypass pattern for Formspree's free tier.

## Workflow

1. **Brand research first.** `web_extract` the existing site (including pricing pages — lift real package names, prices, form fields verbatim). `web_search` socials for voice and post URLs. Never invent prices or claims.
2. **Single self-contained HTML file** (embedded CSS/JS, Google Fonts only, zero build step). Design tokens as CSS variables at top of `<style>`.
3. **Netlify Forms pattern** (form → email):
   - `<form name="booking" method="POST" action="/thanks.html" data-netlify="true" netlify-honeypot="bot-field">`
   - Hidden `<input type="hidden" name="form-name" value="booking">` is REQUIRED.
   - Email delivery is configured in dashboard (Forms → Notifications), not code — say so in README.
   - Forms only work on the deployed site, never locally.
4. **Conversion tracking pattern:** GA4 + Google Ads base tags (commented placeholders) in `<head>` of BOTH pages; the Ads `conversion` event and GA4 `generate_lead` fire ONLY on `thanks.html` — the form's `action` redirect guarantees one fire per lead.
5. **netlify.toml:** `publish = "."`, security headers, `/thanks → /thanks.html` redirect.
6. **README** with deploy options (Git import / drop / CLI), form-notification steps, tag-replacement steps.
7. **Verify locally** before claiming done — see Verification.
8. **Ship via GitHub repo** → user connects in Netlify (ask deployment preference via clarify; this user chose GitHub-first).

## User preferences (Anesu — learned by correction; apply on FIRST pass)
- **Lean copy.** First draft was called "slightly text heavy". Headlines carry the page; body bullets ≤ ~8 words; section intros 1 sentence. Cut ~40% of what feels natural.
- **Real mobile menu.** Hiding nav links below a breakpoint is not acceptable — build an accessible hamburger (aria-expanded, closes on tap) from the start.
- **Use the real logo and real photos** as soon as available; hot-linked CDN images are a temporary measure — flag them and prefer committing assets to `images/`.
- Warm/premium aesthetic, no SaaS slop: serif display (Fraunces) + sans body (Outfit), cream/ink/brass palette worked well.

## Instagram embeds (official, no API)
```html
<blockquote class="instagram-media" data-instgrm-permalink="https://www.instagram.com/reel/XXXX/" data-instgrm-version="14"><a href="...">View on Instagram</a></blockquote>
```
Lazy-load `https://www.instagram.com/embed.js` with an IntersectionObserver (`rootMargin:'600px 0px'`) on the section — zero initial-load cost. Find post URLs via `web_search site:instagram.com <handle>`. Note: some browsers' tracking protection only renders full media on the live domain, not localhost.

## Verification (mandatory)
- Browser blocks `file://` (ERR_BLOCKED_BY_ADMINISTRATOR) → run `python -m http.server 8765` as `terminal(background=true, workdir=<site dir>)`, then `browser_navigate http://localhost:8765/`. Kill the process when done.
- Check `browser_console` for zero errors; `browser_vision` the hero, pricing, and form sections; scroll via `browser_console` `window.scrollTo(0, document.querySelector('#id').offsetTop)`.
- Full-bleed photos: set `object-position` to keep the subject in frame at the section's aspect ratio.

## GitHub push without gh CLI (this Windows box)
`gh` is not installed, but Git Credential Manager holds a usable token:
```bash
CRED=$(printf 'protocol=https\nhost=github.com\n\n' | git credential fill)
# username= / password= lines; password is a PAT usable as
# Authorization: token $TOKEN against api.github.com (e.g. POST /user/repos)
```
Never echo the token. Create repo via API, `git remote add`, push.

## Pitfalls
- Empty `action` on a Netlify form = generic success page and no conversion fire; always redirect to a thanks page.
- `terminal` rejects trailing `&` backgrounding — use `background=true`.
- `noindex` the thanks page.
- Respect `prefers-reduced-motion` for reveals/marquees; mobile hit targets ≥44px.
