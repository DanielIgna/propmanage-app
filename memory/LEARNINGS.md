# Learnings & Gotchas (PropManage)

## Screenshot tool auto-dark quirk (Iul 2026)
- The screenshot_tool Chromium instance appears to force auto-dark/prefers-dark rendering.
- A page with `data-theme="light"` renders LIGHT in real browsers (verified via computed styles:
  body rgb(250,250,249), cards #fff), but the tool's raster shows it dark/inverted.
- DO NOT "fix" light theme based on screenshots alone — verify with getComputedStyle.

## Theme system
- Dark is default (no data-theme attr). Light = html[data-theme="light"] + ThemeContext
  (localStorage key: propmanage_theme). Tailwind darkMode: ["class"] — .dark class toggled too.
- Client V2 + /incepe use `.cv2-scope` overrides in index.css (light-first slate classes,
  remapped in dark via `html:not([data-theme="light"]) .cv2-scope ...`).
- pm-* CSS vars (specialist/pm design system) live in index.css :root — crisp obsidian since
  XOS redesign: bg #050505, surface #111, accent #ccff00.

## XOS Redesign (Faza A, Iul 2026)
- Fonts: Outfit (xos-display, xos-num) + Plus Jakarta Sans added to Google Fonts import.
- Accent migrated #d4ff3a → #ccff00. Ink accent light-mode: #166534 (maps to #ccff00 in dark).
- Floating collisions solved: CookieBanner is now a slim TOP strip; WhatsAppFloat removed from
  App.js and replaced by AssistantDock (single FAB, popover with AI + WhatsApp).
  AIConciergeBubble no longer renders its own launcher; opens via "pm-open-ai" event and
  broadcasts "pm-ai-state" so the dock hides while the panel is open.
- design-system CARD token: dark:bg-[#111213] (no more slate-800 navy).
