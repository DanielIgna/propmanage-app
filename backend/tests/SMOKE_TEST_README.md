# Pre-Deploy Dashboard Smoke Test

A fast (~90s) Playwright-based health check that prevents broken deploys.
Tests all **12 demo profiles** by impersonating each from admin and verifying:

- ✅ Dashboard loads without 500/404
- ✅ No ErrorBoundary fingerprint (`"Ceva nu a mers cum trebuie"`, `"is not defined"`, `"ReferenceError"`)
- ✅ Required `data-testid` is present (e.g. `client-tab-request`, `spec-tab-opportunities`)

## Quick run

There is no preview or production default. The process fails closed unless the
test contract from `TEST_ENVIRONMENT.md` is already exported
(`http://localhost:8002`, database `propmanage_test`).

```bash
cd backend && python -m pytest tests/test_dashboards_smoke.py -v -s
```

## Output

```
🔥 Pre-Deploy Dashboard Smoke Test
   Base URL: http://localhost:8002
   Profiles: 12

  → client@propmanage.io (base)... ✅ PASS
  → specialist@propmanage.io (base)... ✅ PASS
  → operator@propmanage.io (base)... ✅ PASS
  → client.junior@propmanage.io (JUNIOR)... ✅ PASS
  ... (all 12 profiles)

📊 Result: 12 passed · 0 failed · 12 total
✅ All dashboards healthy. Safe to deploy.
```

**Exit code 0** = safe to deploy. **Exit code 1** = STOP, fix the failures first.

## Catches bugs like

The exact scenario from iter66 (TierProgressWidget import lipsă):
- Specialist worked → smoke test PASS for specialist
- Client crashed with `ReferenceError: TierProgressWidget is not defined`
- Smoke test would have caught: `❌ FAIL: ErrorBoundary fingerprint detected: 'is not defined'`

Time saved: 30 seconds vs hours of debugging after a broken deploy.

## How to extend

Add new profiles to `PROFILES` in `test_dashboards_smoke.py`:

```python
{"email": "newrole@propmanage.io", "role": "newrole", "tier": "X", "must_have_testid": "key-testid"},
```

Add error fingerprints to `ERROR_FINGERPRINTS` if you encounter new failure modes.
