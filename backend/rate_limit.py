"""Rate limiting in-memory pentru endpoint-urile publice (TD-07, EO-026 Phase 1)."""
import os
import time
from collections import defaultdict, deque

from fastapi.responses import JSONResponse

PUBLIC_PREFIXES = ("/api/public/", "/api/p/", "/api/track", "/api/go/")
LIMIT = int(os.environ.get("PUBLIC_RATE_LIMIT_PER_MIN", "120"))
WINDOW = 60.0
_hits = defaultdict(deque)
_last_gc = time.time()


async def rate_limit_middleware(request, call_next):
    path = request.url.path
    if path.startswith(PUBLIC_PREFIXES):
        fwd = request.headers.get("x-forwarded-for", "")
        ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")
        now = time.time()
        dq = _hits[ip]
        while dq and now - dq[0] > WINDOW:
            dq.popleft()
        if len(dq) >= LIMIT:
            return JSONResponse(
                {"detail": "Prea multe cereri. Încearcă din nou într-un minut."},
                status_code=429, headers={"Retry-After": "60"})
        dq.append(now)
        global _last_gc
        if now - _last_gc > 300:
            _last_gc = now
            for k in [k for k, v in list(_hits.items()) if not v]:
                _hits.pop(k, None)
    return await call_next(request)
