#!/usr/bin/env python3
"""PM-CTO-002 — Autonomous Repair Engine: audit global UI.

1. Toate <Link to="..."> și navigate("...") din întregul frontend vs rutele din App.js.
2. Butoane fără onClick/type=submit (multiline-aware).
3. .then( fără .catch în următoarele 6 linii.
"""
import os
import re
import sys

SRC = "/app/frontend/src"
APP = os.path.join(SRC, "App.js")


def collect_routes():
    app = open(APP).read()
    routes = set(re.findall(r'path="([^"]+)"', app))
    patterns = []
    for r in routes:
        rx = re.sub(r":[^/]+", "[^/]+", r).rstrip("/*")
        patterns.append(re.compile("^" + rx + "/?$"))
    return routes, patterns


def route_exists(target, routes, patterns):
    t = target.split("?")[0].split("#")[0]
    if not t or not t.startswith("/"):
        return True  # relative/anchor/external — nu e verificabil static
    if t in routes:
        return True
    return any(p.match(t) for p in patterns)


def main():
    routes, patterns = collect_routes()
    dead_links, dead_buttons, unhandled = [], [], []

    for root, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for f in files:
            if not f.endswith((".jsx", ".js")):
                continue
            path = os.path.join(root, f)
            rel = path.replace(SRC + "/", "")
            text = open(path).read()
            lines = text.split("\n")

            for m in re.finditer(r'\bto=\{?"([^"]+)"', text):
                if not route_exists(m.group(1), routes, patterns):
                    ln = text[:m.start()].count("\n") + 1
                    dead_links.append(f"{rel}:{ln} → to=\"{m.group(1)}\"")
            for m in re.finditer(r'navigate\(\s*[`"\']([/][^`"\'$]*)[`"\']', text):
                if not route_exists(m.group(1), routes, patterns):
                    ln = text[:m.start()].count("\n") + 1
                    dead_links.append(f"{rel}:{ln} → navigate(\"{m.group(1)}\")")

            for m in re.finditer(r"<button\b", text):
                seg = text[m.start():m.start() + 600]
                tag_end = seg.find(">")
                tag = seg[:tag_end if tag_end != -1 else 600]
                if "onClick" in tag or "type=" in tag or "onMouseDown" in tag or "{..." in tag:
                    continue
                ln = text[:m.start()].count("\n") + 1
                dead_buttons.append(f"{rel}:{ln}")

            for i, line in enumerate(lines):
                if ".then(" in line and ".catch" not in line:
                    ctx = "\n".join(lines[i:i + 7])
                    if ".catch" not in ctx and "await" not in line:
                        unhandled.append(f"{rel}:{i+1}")

    print(f"── Link-uri/navigate către rute inexistente: {len(dead_links)}")
    for x in dead_links:
        print("  " + x)
    print(f"── Butoane fără handler (candidați): {len(dead_buttons)}")
    for x in dead_buttons:
        print("  " + x)
    print(f"── .then fără .catch (candidați): {len(unhandled)}")
    for x in unhandled[:40]:
        print("  " + x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
