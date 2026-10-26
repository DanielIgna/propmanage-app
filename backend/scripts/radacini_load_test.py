"""Test de încărcare Rădăcini, doar citiri (nu scrie nimic în bază).

    ./venv/bin/python -m scripts.radacini_load_test --base http://localhost:8001 --levels 5,20,50 --per-user 8

Simulează `N` utilizatori concurenți (pentru fiecare nivel din --levels). Fiecare parcurge de `--per-user` ori un
traseu tipic: panou, terenuri, piață, comunități, proiecte, composesorate. Contul de test e cel din seed
(`client@propmanage.io`), iar adminul doar pentru indicatori. Afișează p50/p95/max și erorile pe rută.

Atenție: baza e comună cu producția (egress Supabase). Un rulaj implicit face ~2.000 de cereri mici.
"""
import argparse
import statistics
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests

ROUTE = [
    "/radacini/members/me",
    "/radacini/parcels",
    "/radacini/listings",
    "/radacini/communities",
    "/radacini/projects",
    "/radacini/assoc",
    "/radacini/meta",
]
ADMIN_ROUTE = ["/radacini/admin/kpis", "/radacini/admin/system"]


def _login(api: str, email: str, password: str) -> dict:
    s = requests.Session()
    r = s.post(f"{api}/auth/login", json={"email": email, "password": password}, timeout=30)
    r.raise_for_status()
    return s.cookies.get_dict()


def run_level(api: str, users: int, per_user: int, cookies: dict, admin_cookies: dict) -> dict:
    stats = defaultdict(list)
    errors = defaultdict(int)
    lock = threading.Lock()

    def user(i: int):
        s = requests.Session()
        s.cookies.update(admin_cookies if i == 0 else cookies)
        route = ROUTE + (ADMIN_ROUTE if i == 0 else [])
        for _ in range(per_user):
            for path in route:
                t = time.perf_counter()
                try:
                    r = s.get(api + path, timeout=60)
                    ok = r.status_code < 400
                except requests.RequestException:
                    ok = False
                ms = (time.perf_counter() - t) * 1000
                with lock:
                    stats[path].append(ms)
                    if not ok:
                        errors[path] += 1

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=users) as ex:
        list(ex.map(user, range(users)))
    wall = time.perf_counter() - t0
    total = sum(len(v) for v in stats.values())
    return {"users": users, "requests": total, "wall_s": wall, "rps": total / wall if wall else 0,
            "stats": stats, "errors": errors}


def _pct(values: list, p: float) -> float:
    v = sorted(values)
    return v[min(len(v) - 1, int(round(p * (len(v) - 1))))]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://localhost:8001")
    ap.add_argument("--levels", default="5,20,50")
    ap.add_argument("--per-user", type=int, default=8)
    ap.add_argument("--email", default="client@propmanage.io")
    ap.add_argument("--password", default="Client123!")
    ap.add_argument("--admin-email", default="admin@propmanage.io")
    ap.add_argument("--admin-password", default="Admin123!")
    args = ap.parse_args()
    api = args.base.rstrip("/") + "/api"
    cookies = _login(api, args.email, args.password)
    admin_cookies = _login(api, args.admin_email, args.admin_password)
    for lvl in [int(x) for x in args.levels.split(",") if x.strip()]:
        res = run_level(api, lvl, args.per_user, cookies, admin_cookies)
        print(f"\n== {lvl} utilizatori concurenți: {res['requests']} cereri în {res['wall_s']:.1f}s "
              f"({res['rps']:.1f} cereri/s)")
        print(f"{'rută':32} {'n':>5} {'p50 ms':>8} {'p95 ms':>8} {'max ms':>8} {'erori':>6}")
        for path, vals in sorted(res["stats"].items(), key=lambda kv: -statistics.median(kv[1])):
            print(f"{path:32} {len(vals):>5} {statistics.median(vals):>8.0f} {_pct(vals, 0.95):>8.0f} "
                  f"{max(vals):>8.0f} {res['errors'].get(path, 0):>6}")


if __name__ == "__main__":
    main()
