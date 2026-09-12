#!/usr/bin/env python3
"""UI Nav Integrity Audit — detectează link-uri moarte în navigația admin.

Verifică deterministic (fără LLM):
  1. Fiecare `href` din NAV_SECTIONS (AdminLayoutMetronic) are rută în App.js.
  2. Fiecare item FĂRĂ href are mapare în TITLES din AdminConsole (altfel tabul e mort).

Rulare: python3 /app/scripts/ui_nav_audit.py  → exit 0 = curat, exit 1 = probleme.
"""
import re
import sys

NAV = "/app/frontend/src/pages/admin/AdminLayoutMetronic.jsx"
APP = "/app/frontend/src/App.js"
CONSOLE = "/app/frontend/src/pages/admin/AdminConsole.jsx"


def main() -> int:
    nav = open(NAV).read()
    app = open(APP).read()
    console = open(CONSOLE).read()

    routes = set(re.findall(r'path="([^"]+)"', app))
    titles = set(re.findall(r'^\s{2}([a-z_0-9]+): \{ title:', console, re.M))
    items = re.findall(r'\{ id: "([a-z_0-9]+)", label: "([^"]+)"(.*?)\},', nav)

    problems = []
    for item_id, label, rest in items:
        m = re.search(r'href: "([^"?]+)', rest)
        if m:
            if m.group(1) not in routes:
                problems.append(f"[HREF MORT] '{label}' ({item_id}) → {m.group(1)} nu are rută în App.js")
        elif item_id not in titles:
            problems.append(f"[TAB MORT] '{label}' ({item_id}) fără href și fără mapare în AdminConsole.TITLES")

    print(f"Items audit: {len(items)} · rute App.js: {len(routes)} · taburi consolă: {len(titles)}")
    if problems:
        print("\n".join(problems))
        return 1
    print("✅ Navigația admin e integră — zero link-uri sau taburi moarte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
