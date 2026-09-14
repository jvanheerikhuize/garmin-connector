---
id: ui-design
title: UI Design System & Markup Contract
tier: feature
status: implemented
owners: [jerry]
depends_on: [connection-status-shell, gui-course-frontend]
last_updated: 2026-09-14
---

# UI Design System & Markup Contract

`src/garmin_connector/gui/static/{styles.css,index.html}` (+ the vendored, never-edited `cybercore.min.css`)

Depends on: [connection-status-shell](../connection-status-shell.md), [gui-course-frontend](gui-course-frontend.md) — this spec *styles* the elements those two define; they do not depend on it (the app must function unstyled).

## Purpose

Make the visual design regenerable. Everything a fresh implementer needs to produce a `styles.css` and `index.html` that render the same Cyberpunk-Terminal UI: the token palette, typography, layout, every component's exact treatment, which vendored CYBERCORE classes are used where, and the element → id → class contract that ties markup to CSS and JS.

## Scope

**In scope:** `styles.css` in full; the structural markup of `index.html` (elements, ids, classes, external asset links); Leaflet visual overrides.

**Out of scope:** behavior (see the two specs above); the contents of `cybercore.min.css` (vendored third-party asset from https://sebyx07.github.io/cybercore-css/, copied verbatim, never regenerated or edited).

## Requirements

### 1. Vendored base & external assets
- `cybercore.min.css` MUST be loaded first, then `styles.css`. `styles.css` overrides and extends it; it never duplicates its rules.
- Tokens consumed from CYBERCORE (with the fallback hex `styles.css` MUST repeat inline as `var(--x, #hex)` so the UI survives a missing vendor file):
  ```
  --cyber-cyan-500     #00f0ff      --cyber-chrome-200  #d1d4de
  --cyber-magenta-500  #ff2a6d      --cyber-chrome-300  #b2b7c7
  --cyber-green-500    #05ffa1      --cyber-chrome-400  #939ab0
  --font-body          "Exo 2"      --cyber-chrome-500  #747d99
  ```
- `<head>` MUST include, in order: `<meta charset="UTF-8">`, viewport meta, `<title>Garmin Course Uploader</title>`, preconnects to `https://fonts.googleapis.com` and `https://fonts.gstatic.com` (crossorigin), the Google Fonts stylesheet for **Exo 2 (400;600;700), JetBrains Mono (400;500;700), Orbitron (600;700;800), Rajdhani (500;600;700)** with `display=swap`, Leaflet 1.9.4 CSS from `https://unpkg.com/leaflet@1.9.4/dist/leaflet.css`, `/static/cybercore.min.css`, `/static/styles.css`.
- End of `<body>`: Leaflet 1.9.4 JS from `https://unpkg.com/leaflet@1.9.4/dist/leaflet.js`, then `/static/app.js`.

### 2. Local tokens (`:root` in `styles.css`)
```
--app-bg           #050608
--app-panel        #0a0b12
--app-subpanel     #111320
--app-border       #1e2238
--app-border-glow  rgba(0, 240, 255, 0.4)
--font-display     'Orbitron', sans-serif        # overrides CYBERCORE's
--font-header      'Rajdhani', sans-serif
--font-mono        'JetBrains Mono', monospace
```

### 3. Global
- `* { box-sizing: border-box }`.
- `body`: background `--app-bg`; color `--cyber-chrome-200`; font `var(--font-header), var(--font-body), sans-serif`; `min-height: 100vh`; no margin/padding; `overflow-x: hidden`; two decorative radial gradients layered over the background: `radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0,240,255,0.08), transparent)` and `radial-gradient(ellipse 60% 40% at 90% 80%, rgba(255,42,109,0.05), transparent)`.
- `body` carries CYBERCORE classes `cyber-scanlines cyber-scanlines--fine` (CRT scanline overlay).
- `.app-container`: `max-width: 1440px; margin: 0 auto; padding: 16px 24px 32px; display: flex; flex-direction: column; gap: 20px; position: relative; z-index: 1`.

### 4. Header
- `.cyber-nav-header` (defined locally, not by CYBERCORE): background `--app-panel`; `border: 1px solid --app-border`; `border-left: 4px solid --cyber-cyan-500`; `padding: 12px 20px`; flex, `justify-content: space-between; align-items: center; gap: 16px`; `box-shadow: 0 4px 24px rgba(0,0,0,0.5)`.
- `.brand-wrapper`: flex, center, `gap: 12px`.
- `.brand-icon-box`: `36×36px`; background `rgba(0,240,255,0.08)`; `border: 1px solid --cyber-cyan-500`; flex-centered; color `--cyber-cyan-500`; `border-radius: 4px`. Contains an inline 20×20 SVG watch glyph (stroke `currentColor`, width 2, round caps/joins, no fill): `rect x=6 y=5 w=12 h=14 rx=3`, `path M10 2h4`, `path M10 22h4`, `circle cx=12 cy=12 r=3`.
- `.brand-title` (`<h1>`): `--font-display`; `1.2rem`; weight 700; `letter-spacing: 0.08em`; `#ffffff`; uppercase; no margin. Text: `Garmin Course Uploader`.
- `.status-container`: flex, center, `gap: 8px`; `padding: 6px 14px`; background `--app-subpanel`; `border: 1px solid --app-border`; `--font-mono`; `0.8rem`; color `--cyber-chrome-300`; `border-radius: 3px`.
- `.status-dot`: `8×8px`, `border-radius: 50%`, `flex-shrink: 0`. State modifiers (exhaustive, class-driven — see [connection-status-shell](../connection-status-shell.md)):
  - `.connected` → background `--cyber-green-500`, `box-shadow: 0 0 6px rgba(5,255,161,0.5)`
  - `.mounting` → background `orange`
  - `.disconnected` → background `--cyber-chrome-500`

### 5. Layout
- `.main-grid`: `display: grid; grid-template-columns: 480px 1fr; gap: 20px; align-items: stretch`. At `max-width: 1100px` → `grid-template-columns: 1fr`.
- `.sidebar-col`: flex column, `gap: 20px`.

### 6. Cards
- `.cyber-card` (local override of the CYBERCORE class): background `--app-panel`; `border: 1px solid --app-border`; `box-shadow: 0 8px 32px rgba(0,0,0,0.45)`. The map card additionally carries CYBERCORE's `cyber-card--green` modifier.
- `.card-header-clean`: flex space-between/center; `padding-bottom: 12px`; `border-bottom: 1px solid --app-border`; `margin-bottom: 14px`.
- `.card-title` (`<h2>`): `--font-display`; `1.05rem`; 700; `letter-spacing: 0.08em`; `#ffffff`; no margin.
- `.storage-card`: flex column, `flex: 1`, `min-height: 600px`.
- `.map-card-wrapper`: flex column, `min-height: 600px`.

### 7. Buttons
- `.btn`: `inline-flex` centered; `height: 36px`; `padding: 0 16px`; `--font-mono`; `0.82rem`; weight 600; uppercase; `letter-spacing: 0.04em`; `border: 1px solid --app-border`; background `--app-subpanel`; color `--cyber-chrome-200`; pointer; `transition: all 0.15s ease`; `border-radius: 2px`.
  - `:hover:not(:disabled)` → border `--cyber-cyan-500`, color `#fff`, background `rgba(0,240,255,0.12)`.
  - `:disabled` → `opacity: 0.45`, `cursor: not-allowed`, border `--app-border`, color `--cyber-chrome-500`.
- `.btn-primary`: border/color `--cyber-cyan-500`, background `rgba(0,240,255,0.08)`; hover → background `--cyber-cyan-500`, color `#000`, `box-shadow: 0 0 12px rgba(0,240,255,0.4)`.
- `.btn-secondary`: border `--app-border`, color `--cyber-chrome-300`, background `--app-subpanel`.
- `.btn-danger`: border/color `--cyber-magenta-500`, background `rgba(255,42,109,0.08)`; hover → background `--cyber-magenta-500`, color `#fff`, `box-shadow: 0 0 12px rgba(255,42,109,0.4)`.
- `.btn-sm`: `height: 28px; padding: 0 12px; font-size: 0.75rem`.
- `.storage-toolbar`: flex center `gap: 10px; margin-bottom: 14px`; its `.btn` children `flex: 1` (equal widths).

### 8. Course list
- `.course-list-container`: flex column `gap: 8px`; `flex: 1`; `min-height: 480px`; `max-height: calc(100vh - 280px)`; `overflow-y: auto`; `padding-right: 4px`. WebKit scrollbar: `width: 6px`, track `--app-subpanel`, thumb `--cyber-cyan-500`.
- `.course-row`: flex space-between/center; `padding: 10px 12px`; background `--app-subpanel`; `border: 1px solid --app-border`; `transition: all 0.15s ease`; `gap: 12px`; `border-radius: 2px`. Hover → border `--cyber-cyan-500`, background `#151829`.
- `.course-row-left`: flex center `gap: 10px; min-width: 0; flex: 1`.
- `.course-format-badge`: `--font-mono`; `0.68rem`; 700; `padding: 3px 6px`; `letter-spacing: 0.05em`; `border-radius: 2px`; uppercase; `flex-shrink: 0`.
  - `.course-format-fit` → background `rgba(0,240,255,0.15)`, border/color `--cyber-cyan-500`.
  - `.course-format-gpx` → background `rgba(255,42,109,0.15)`, border/color `--cyber-magenta-500`.
- `.course-details`: flex column `min-width: 0; flex: 1; gap: 2px`.
- `.course-path`: `--font-mono`; `0.82rem`; 500; `#ffffff`; single line with ellipsis (`white-space: nowrap; overflow: hidden; text-overflow: ellipsis`).
- `.course-meta`: `--font-mono`; `0.72rem`; `--cyber-chrome-400`.
- `.course-actions`: flex center `gap: 8px; flex-shrink: 0`.
- `.empty-courses`: `padding: 36px 16px`; centered; `--font-mono`; `0.85rem`; `--cyber-chrome-500`; uppercase; `border: 1px dashed --app-border`.

### 9. Ingest modal internals
- Modals use CYBERCORE `cyber-modal` / `cyber-modal__dialog` / `__header` / `__title` / `__close` / `__body` / `__footer`, opened by adding `cyber-modal--open`. The delete-confirm modal carries `cyber-modal--magenta`; the ingest modal has no color modifier (default styling) and its dialog has inline `max-width: 500px`.
- `.sideload-section`: flex column `gap: 14px`.
- `.sport-selector-group`: flex center `gap: 8px`; background `--app-subpanel`; `padding: 6px`; `border: 1px solid --app-border`.
- `.sport-label`: `--font-mono`; `0.75rem`; uppercase; `--cyber-chrome-400`; `padding: 0 8px`.
- `.sport-pills`: flex `gap: 6px; flex: 1`.
- `.sport-btn`: `flex: 1`; transparent background; `border: 1px solid transparent`; `--cyber-chrome-300`; `--font-mono`; `0.78rem`; 600; uppercase; `padding: 6px 10px`; pointer; `transition: all 0.2s ease`; `border-radius: 2px`. Hover → background `rgba(0,240,255,0.08)`, `#fff`. `.active` → background `rgba(0,240,255,0.15)`, border/color `--cyber-cyan-500`.
- `.dropzone-cyber`: `border: 1px dashed --cyber-cyan-500`; background `--app-subpanel`; `padding: 32px 16px`; centered flex column `gap: 10px`; pointer; `transition: all 0.2s ease`; `border-radius: 2px`. `:hover` and `.drag-over` → background `#14172a`, `box-shadow: 0 0 20px rgba(0,240,255,0.2)`.
- `.dropzone-primary-text`: `--font-display`; `0.95rem`; 700; `letter-spacing: 0.05em`; `#fff`; uppercase. `.dropzone-subtext`: `--font-mono`; `0.78rem`; `--cyber-chrome-400`.
- Hint line under the dropzone: inline-styled `--font-mono`, `0.75rem`, `--cyber-chrome-400`, centered.

### 10. Map viewport, overlay, HUD
- `.map-viewport-container`: `flex: 1; min-height: 480px; position: relative`; background `#06070a`; `border: 1px solid --app-border`; `overflow: hidden`.
- `#map`: `100%` × `100%`, `min-height: 480px`, background `#07090e !important`.
- `.map-empty-overlay`: absolute `inset: 0`; flex-centered; background `rgba(7,9,14,0.65)`; `pointer-events: none`; `z-index: 500`; `transition: opacity 0.2s ease`. Shown/hidden by JS via `style.display` (`flex` / `none`).
- Disabled state — `.map-viewport-container.map-disabled`: `#map` → `opacity: 0.35; filter: grayscale(0.85); pointer-events: none`; `.leaflet-control-container` hidden; overlay background darkens to `rgba(7,9,14,0.85)`.
- `.empty-overlay-content`: `--font-mono`; `0.88rem`; `--cyber-chrome-400`; `padding: 10px 18px`; background `rgba(13,14,20,0.85)`; `border: 1px solid --app-border`; `letter-spacing: 0.04em`; `border-radius: 2px`.
- `.map-hud-bar`: flex space-between/center; background `--app-subpanel`; `border-top: 1px solid --app-border`; `padding: 10px 16px`; `--font-mono`; `0.8rem`; `--cyber-chrome-300`. `.hud-track-info`: flex center `gap: 8px`; color `--cyber-green-500`.

### 11. Leaflet overrides (all `!important` where noted)
- `.leaflet-container`: background `#07090e` !, font `--font-mono` !.
- `.leaflet-bar`: `border: 1px solid --cyber-cyan-500` !, `border-radius: 2px` !, `box-shadow: 0 0 10px rgba(0,240,255,0.2)` !, `overflow: hidden`. `.leaflet-bar a`: background `--app-panel` !, color `--cyber-cyan-500` !, `border-bottom: 1px solid --app-border` !, `border-radius: 0` !, `transition: all 0.15s ease`; hover → background `--cyber-cyan-500` !, color `#000` !.
- `.leaflet-tile-pane`: `filter: saturate(0.85) brightness(0.9)`.
- `.leaflet-control-attribution`: background `rgba(7,9,14,0.8)` !, color `--cyber-chrome-500` !, `0.65rem` !; its links `--cyber-cyan-500` !.
- `.glowing-track` (the route polyline): `stroke: --cyber-cyan-500` !, `stroke-width: 4` !, `filter: drop-shadow(0 0 6px rgba(0,240,255,0.8))`.

### 12. Toasts
- `.cyber-toast-stack` (local): `position: fixed; bottom: 24px; right: 24px`; flex column `gap: 10px`; `z-index: 10000`; `pointer-events: none`.
- `.cyber-toast` (local): `pointer-events: auto; min-width: 280px; max-width: 420px`; `box-shadow: 0 8px 30px rgba(0,0,0,0.6)`; `animation: toastSlideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards`. Each toast also carries CYBERCORE `cyber-alert` + one of `cyber-alert--success | --error | --warning`, with a `cyber-alert__title` child and a message `<div>` (inline `font-size: 0.85rem; font-family: var(--font-mono)`).
- `@keyframes toastSlideIn`: from `opacity 0; transform: translateX(40px) scale(0.95)` → to `opacity 1; transform: translateX(0) scale(1)`.
- `@keyframes toastSlideOut`: from `opacity 1; translateX(0)` → to `opacity 0; translateX(40px)`. Applied by JS (`0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards`) before removal.

## Data Shapes / Interfaces — markup contract

Every element JS or CSS addresses, with its required id and classes. Ids are referenced by [connection-status-shell](../connection-status-shell.md) and [gui-course-frontend](gui-course-frontend.md); a regenerated `index.html` MUST use exactly these.

| Element | id | classes | notes |
|---|---|---|---|
| `<body>` | — | `cyber-scanlines cyber-scanlines--fine` | |
| wrapper `<div>` | — | `app-container` | |
| `<header>` | — | `cyber-nav-header` | |
| brand `<div>` › icon `<div>` › `<h1>` | — | `brand-wrapper` › `brand-icon-box` › `brand-title` | SVG glyph inside icon box |
| status `<div>` › `<span>` + `<span>` | — › `statusDot` + `deviceStatus` | `status-container` › `status-dot disconnected` + — | initial text `No watch connected` |
| `<main>` | — | `main-grid` | |
| `<section>` (left) › card `<div>` | — | `sidebar-col` › `cyber-card storage-card` | |
| card header › `<h2>` | — | `card-header-clean` › `card-title` | `Watch Storage` |
| toolbar › buttons | `btnOpenIngestModal`, `btnRefresh` | `storage-toolbar` › `btn btn-primary`, `btn btn-secondary` | both `disabled` initially; labels `Ingest Route`, `Refresh` |
| course list `<div>` | `courseTableBody` | `course-list-container` | initial child `.empty-courses` "Awaiting device connection..." |
| course row (JS-rendered) | — | `course-row` › `course-row-left` › `course-format-badge course-format-fit\|gpx` + `course-details` › `course-path`, `course-meta`; `course-actions` › `btn btn-sm btn-primary` (Map), `btn btn-sm btn-danger` (Delete) | |
| `<section>` (right) › card | — | `maparea` › `cyber-card cyber-card--green map-card-wrapper` | `maparea` has no CSS rule; it is a structural hook only |
| card header › `<h2>` | — | `card-header-clean` › `card-title` | `Route Preview` |
| viewport › map + overlay › content | `map`, `mapEmptyOverlay` › — | `map-viewport-container` › —, `map-empty-overlay` › `empty-overlay-content` | JS toggles `map-disabled` on the viewport |
| HUD bar › info | `mapInfo` | `map-hud-bar` › `hud-track-info` | initial `No route selected` |
| ingest modal | `ingestModal` | `cyber-modal` | dialog `cyber-modal__dialog` (inline `max-width: 500px`); close btn `ingestModalClose` (`cyber-modal__close`, text `✕`); body › `sideload-section` › `sport-selector-group` (`sport-label` "Activity:", `sport-pills` › 3× `sport-btn` with `data-sport` = `cycling` (initially `active`) / `hiking` / `running`), `dropZone` (`dropzone-cyber`, children `dropzone-primary-text` "Drop GPX File Here", `dropzone-subtext` "or click to browse local files", hidden `<input type="file" id="fileInput" accept=".gpx">`), hint line; footer › `btnCancelIngest` (`btn btn-secondary`, "Close") |
| confirm modal | `confirmModal` | `cyber-modal cyber-modal--magenta` | title `Confirm Delete`; close `confirmModalClose`; body `<p id="confirmModalText">`; footer `btnConfirmCancel` (`btn btn-secondary`, "Cancel"), `btnConfirmDelete` (`btn btn-danger`, "Delete") |
| toast container | `toastContainer` | `cyber-toast-stack` | |
| toast (JS-rendered) | — | `cyber-alert cyber-alert--<type> cyber-toast` › `cyber-alert__title` + message div | |

## Non-Goals
- No light theme / theme switching — the palette is dark-only by design.
- No responsive treatment beyond the single breakpoint (grid collapses to one column at `max-width: 1100px`); this is a desktop tool.
- No editing of `cybercore.min.css` — if a vendored rule is wrong for this app, override it in `styles.css`.
- No CSS preprocessing, bundling, or minification of `styles.css`.
