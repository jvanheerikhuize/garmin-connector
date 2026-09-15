---
id: ui-design
title: UI Design System & Tailwind Configuration
tier: feature
status: implemented
owners: [jerry]
depends_on: [connection-status-shell, gui-course-frontend]
last_updated: 2026-09-15
---

# UI Design System & Tailwind Configuration

`ui/tailwind.config.js` and `ui/src/index.css`

Depends on: [connection-status-shell](../connection-status-shell.md), [gui-course-frontend](gui-course-frontend.md) — this spec defines the styling tokens for the React components.

## Purpose

Migrate the bespoke Cyberpunk CSS theme to Tailwind CSS utility classes, ensuring all React components use a cohesive design system while maintaining the neon-glow, CRT scanline aesthetic.

## Scope

**In scope:** `tailwind.config.js` token palette, typography configurations, global CSS resets (`index.css`), Leaflet overrides, and component class conventions.

## Requirements

### 1. Tailwind Configuration (`tailwind.config.js`)
- Theme extension:
  - **Colors:**
    - `cyber-cyan`: `#00f0ff`
    - `cyber-magenta`: `#ff2a6d`
    - `cyber-green`: `#05ffa1`
    - `cyber-chrome`: `200` (`#d1d4de`), `300` (`#b2b7c7`), `400` (`#939ab0`), `500` (`#747d99`)
    - `app-bg`: `#050608`
    - `app-panel`: `#0a0b12`
    - `app-subpanel`: `#111320`
    - `app-border`: `#1e2238`
  - **Fonts:**
    - `display`: `['Orbitron', 'sans-serif']`
    - `header`: `['Rajdhani', 'sans-serif']`
    - `mono`: `['JetBrains Mono', 'monospace']`
    - `body`: `['Exo 2', 'sans-serif']`
  - **Box Shadows:**
    - `glow-cyan`: `0 0 12px rgba(0, 240, 255, 0.4)`
    - `glow-magenta`: `0 0 12px rgba(255, 42, 109, 0.4)`
    - `glow-green`: `0 0 12px rgba(5, 255, 161, 0.4)`
    - `panel`: `0 8px 32px rgba(0, 0, 0, 0.45)`

### 2. Global CSS (`index.css`)
- `@tailwind base; @tailwind components; @tailwind utilities;`
- `body`: `bg-app-bg text-cyber-chrome-200 font-body min-h-screen overflow-x-hidden`.
- CRT Scanlines: add a fixed pseudo-element overlay with `background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))` and `background-size: 100% 2px, 3px 100%`.
- Leaflet Overrides (global scope):
  - `.leaflet-container { @apply bg-app-bg font-mono !important; }`
  - `.leaflet-bar { @apply border border-cyber-cyan shadow-glow-cyan rounded-sm overflow-hidden !important; }`
  - `.glowing-track { stroke: #00f0ff !important; stroke-width: 4 !important; filter: drop-shadow(0 0 6px rgba(0,240,255,0.8)); }`

### 3. Component Styling Patterns (Tailwind)
- **Buttons (`btn`)**: `@apply inline-flex items-center justify-center h-9 px-4 font-mono text-sm font-semibold uppercase tracking-wider border transition-all duration-150 rounded-sm;`
  - Primary: `border-cyber-cyan text-cyber-cyan bg-[rgba(0,240,255,0.08)] hover:bg-cyber-cyan hover:text-black hover:shadow-glow-cyan disabled:opacity-50 disabled:cursor-not-allowed`
  - Danger: `border-cyber-magenta text-cyber-magenta bg-[rgba(255,42,109,0.08)] hover:bg-cyber-magenta hover:text-white hover:shadow-glow-magenta`
- **Cards (`cyber-card`)**: `@apply bg-app-panel border border-app-border shadow-panel p-4;`
- **Modals**: Fixed inset-0 backdrop `bg-black/60 backdrop-blur-sm`, with a centered `cyber-card` panel.

### 4. Layout
- Desktop: Grid layout `grid-cols-[480px_1fr]` with a `gap-5`.
- Mobile: Falls back to `flex-col` stack at `< 1100px`.

## Non-Goals
- No light theme / theme switching.
- CYBERCORE vendored CSS is fully replaced by this Tailwind configuration. We no longer vendor external CSS blobs.
