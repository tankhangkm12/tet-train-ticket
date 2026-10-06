<!-- Condensed for the owner from https://github.com/vercel-labs/web-interface-guidelines (command.md) at commit
     e3d624baaf29dc1fc645aff3e38f03e564d2d6b1 (2026-08-17), MIT licence below. Rules regrouped one line per
     topic; the English-only copy and punctuation rules were dropped. -->

# Web interface checklist

A checklist for changed UI files, fixed at the commit above — never fetched at run time. Priority: The owner's
decisions → the approved UI design (`<app>-ui.md`, `design-tokens.json`, exports) → the repo's design system →
this list; a disagreement is reported as "differs from guideline X — kept per <source>", not changed. Library
names are examples; a new dependency is still A3. Copy and punctuation follow the project's language.

## Rules

- **Accessibility:** semantic HTML before ARIA (`<button>` for actions, `<a>`/`<Link>` for navigation, never
  `<div onClick>`) · icon-only buttons and form controls have a label · `alt` on images (`""` if decorative),
  `aria-hidden` on decorative icons · `aria-live="polite"` for toasts and async validation · headings in order,
  skip link, `scroll-margin-top` on anchors · media has captions/transcripts and keyboard controls.
- **Focus:** visible `:focus-visible` ring; never `outline: none` without a replacement; `:focus-within` for
  compound controls; sticky bars and overlays never cover the focused element.
- **Forms:** `autocomplete`, meaningful `name`, correct `type`/`inputmode` · never block paste · clickable labels,
  one hit target for checkbox + label · no spellcheck on emails/codes/usernames · submit enabled until the request
  starts, spinner during it · errors inline, focus the first one · warn before leaving with unsaved changes.
- **Motion:** honour `prefers-reduced-motion` · animate `transform`/`opacity` only · never `transition: all` ·
  correct `transform-origin` (SVG: on a `<g>` with `transform-box: fill-box`) · interruptible · autoplay > 5 s
  needs pause/stop/hide.
- **Content:** containers survive long, short and empty content (`truncate`, `line-clamp`, `break-words`,
  `min-w-0` on flex children) · `tabular-nums` for number columns · empty states never render broken UI.
- **Images & performance:** explicit `width`/`height` · `loading="lazy"` below the fold, `fetchpriority="high"`
  above · virtualise lists > 50 items · no layout reads in render, batch DOM reads/writes · cheap controlled
  inputs · `preconnect` asset domains, preload critical fonts with `font-display: swap` · video over GIF.
- **Navigation & state:** URL holds filters, tabs, pagination, open panels; deep links work · destructive actions
  confirm or offer undo.
- **Touch & layout:** `touch-action: manipulation` · `overscroll-behavior: contain` in modals/drawers · gestures
  have tap and keyboard alternatives · `autoFocus` only for a single desktop input · `env(safe-area-inset-*)` on
  full-bleed layouts · CSS layout over JS measurement · no stray horizontal scrollbars.
- **Theming:** `color-scheme` on `<html>` for dark themes · `theme-color` meta matches the background · native
  `<select>` gets explicit colours · hover/active/focus raise contrast.
- **Locale & hydration:** `Intl.DateTimeFormat` / `Intl.NumberFormat`, never hard-coded formats · language from
  `Accept-Language`, not IP · `translate="no"` on brand names and code · inputs with `value` have `onChange` ·
  dates rendered without server/client mismatch · `suppressHydrationWarning` only where truly needed.

## Output

Group by file, `file:line - issue`, terse, plus a count (`guidelines: 3 findings in 2 files, 11 files pass`):

```text
src/Button.tsx:42 - icon button missing aria-label
src/Modal.tsx:12 - missing overscroll-behavior: contain
```

---

<details><summary>Licence (MIT) — web-interface-guidelines</summary>

```text
MIT License

Copyright (c) 2025 Vercel Labs

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

</details>
