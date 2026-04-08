# LandReserve — Bug Fixes & Changes

This document lists every bug found and fixed in this revision.

---

## Bug Fixes

### BUG #1 — Tailwind `tailwind.config` before CDN script (Critical)
**File:** `templates/base.html`  
**Problem:** The `<script>` block setting `tailwind.config = {...}` appeared at line 16, but the Tailwind CDN `<script src="https://cdn.tailwindcss.com">` was at line 41. The config must be defined **after** Tailwind loads — otherwise custom colours (`primary`, `primary-dark`, etc.) are silently ignored and all Tailwind colour utilities using those names produce nothing.  
**Fix:** Moved `<script src="https://cdn.tailwindcss.com">` before the `tailwind.config` block.

---

### BUG #2 — `order_by()` called on a Python list (Critical / 500 error)
**File:** `lands/views.py` — `land_list()` and `search_lands()`  
**Problem:** When the `availability` filter (`?availability=available` or `?availability=reserved`) was applied, the `lands` QuerySet was converted to a plain Python list via a list comprehension. The sort block came **after** this conversion and called `lands.order_by(...)` — but lists don't have `.order_by()`, causing an `AttributeError` / 500 error.  
**Fix:** Reordered to: sort → build map_pins → apply availability filter. Sort now always operates on the QuerySet.

---

### BUG #3 — Map pins built before availability filter (Wrong data on map)
**File:** `lands/views.py` — `land_list()` and `search_lands()`  
**Problem:** `map_pins` JSON was built from the QuerySet **before** the availability filter was applied, so the map always showed all pins regardless of the selected availability filter. Filtering the list view had no effect on the map.  
**Fix:** `map_pins` is now built after sorting but respects the same availability filter logic before serialising to JSON.

---

### BUG #4 — `django-csp` version mismatch (Silent security regression)
**File:** `requirements.txt`  
**Problem:** `requirements.txt` specified `django-csp>=3.7`, but `settings.py` uses the **4.x API** (`CONTENT_SECURITY_POLICY = {"DIRECTIVES": {...}}`). In django-csp 3.x, this dict is silently ignored and no CSP headers are sent, leaving the app without Content Security Policy protection.  
**Fix:** Changed to `django-csp>=4.0`.

---

### BUG #5 — `{% url 'google_login' %}` raises `NoReverseMatch` (500 on login page)
**Files:** `templates/base.html`, `accounts/templates/registration/login.html`  
**Problem:** `{% url 'google_login' %}` is not a valid URL name in django-allauth ≥ 65. The correct URL path is `/accounts/google/login/` (routed through `allauth.urls`).  
**Fix:** Replaced the broken template tag with a hardcoded `/accounts/google/login/` href that is always valid as long as allauth is in `INSTALLED_APPS`.

---

### BUG #6 — Login template used dead CSS class variables (Broken styling)
**File:** `accounts/templates/registration/login.html`  
**Problem:** The template relied on CSS classes and variables (`var(--forest)`, `.btn-google`, `.card-header-bar`, `.modal-tab`, `.flash-error`, `.pwd-wrap`, etc.) that no longer exist in the current Tailwind-based stylesheet. The page rendered unstyled.  
**Fix:** Rewrote the login template using Tailwind utility classes that are consistent with the rest of the app.

---

## New: Bun Frontend Pipeline

Bun (https://bun.sh) has been added as the frontend package manager and build runner.

### Why Bun?
- Significantly faster than npm/pnpm for install and script execution
- Drop-in replacement — uses the same `package.json` format
- Bundles, transpiles, and runs TypeScript/JS natively
- Replaces the need for a separate `node_modules` install step in CI

### Files added
| File | Purpose |
|---|---|
| `package.json` | npm-compatible manifest with Bun scripts |
| `tailwind.config.js` | Tailwind config for the build pipeline |
| `postcss.config.js` | PostCSS config (autoprefixer) |
| `bunfig.toml` | Bun-specific settings |
| `static/css/src/main.css` | Source CSS with `@tailwind` directives |

### Usage

```bash
# Install Bun (once — Linux/macOS):
curl -fsSL https://bun.sh/install | bash

# Install frontend dependencies:
bun install

# Build CSS once (production):
bun run build

# Watch mode during development:
bun run dev
```

The compiled CSS is output to `static/css/styles.css` which Django's `{% static %}` tag serves.

> **Note:** The Tailwind CDN script in `base.html` is kept for development convenience (hot-reload without running Bun). For production, run `bun run build` and remove the CDN `<script>` tag to serve the minified CSS instead.

---

## Styling improvements (Template Sample alignment)

The Template Sample (`Templates Sample/`) uses:
- CSS custom properties (`--primary`, `--border`, `--muted`, etc.)
- shadcn/ui component patterns
- Tailwind v4 `@import` syntax

This Django app uses Tailwind CDN v3. The following alignments were made:

1. **CSS variables** defined in `<style>` in `base.html` and in `static/css/src/main.css` match the Template Sample variable names.
2. **Pill filter bar** component (`.pill`, `.pill-active`, `.pill-inactive`) matches the Template Sample `FilterBar` component pattern.
3. **Listing card** hover behaviour and shadow match the Template Sample `ListingCard` component.
4. **Auth modal** rebuilt with rounded-2xl, cleaner tab behaviour, fixed backdrop click-to-close.
5. **Nav dropdown menu** added for authenticated users (profile, bookings, wishlist, logout).
6. **Flash messages** moved to top-right toast pattern with auto-dismiss.
7. **Google button** uses the official Google colour SVG logo, consistent with Template Sample.
