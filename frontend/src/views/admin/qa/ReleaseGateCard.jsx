// Extracted from AdminQAPlaybook.jsx for maintainability.
import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { CheckCircle2, Clock, Loader2, Mail, MinusCircle, Play, Rocket, RotateCw, Sparkles, Wrench, XCircle } from "lucide-react";
import { AdminCard, AdminBtn } from "../AdminLayoutMetronic";
import { API, PRIO_BADGE } from "./shared";

export const ReleaseGateCard = () => {
  const [running, setRunning] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [last, setLast] = useState(null);
  const [history, setHistory] = useState([]);
  const [autoFixing, setAutoFixing] = useState(false);

  const loadHistory = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/admin/qa/automation/release-gates`);
      setHistory(data.gates || []);
      // Preserve the rich `last` (with full `results`) if it matches the latest gate;
      // otherwise lazy-fetch the full detail so the per-test accordion stays available.
      if ((data.gates || []).length > 0) {
        const topId = data.gates[0].gate_id;
        setLast((prev) => (prev?.gate_id === topId && Array.isArray(prev?.results) ? prev : data.gates[0]));
        // If we have no rich payload for the top gate, fetch it once
        try {
          const cur = await axios.get(`${API}/admin/qa/automation/release-gates/${topId}`);
          setLast((prev) => (prev?.gate_id === topId && Array.isArray(prev?.results) ? prev : cur.data));
        } catch { /* silent */ }
      }
    } catch { /* silent */ }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  const runGate = async () => {
    setConfirming(false);
    setRunning(true);
    try {
      const { data } = await axios.post(`${API}/admin/qa/automation/release-gate`, { email_admins: emailEnabled });
      setLast(data);
      if (data.summary.blocked) {
        toast.error(`🚫 RELEASE BLOCKED — ${data.summary.p0_fail} P0 fail. Email ${data.email.sent ? "trimis" : "neexpediat"}.`);
      } else {
        toast.success(`✅ Release ready — ${data.summary.pass}/${data.summary.total} pass. Email ${data.email.sent ? "trimis la " + data.email.recipients.length + " admini" : "neexpediat"}.`);
      }
      loadHistory();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la rularea gate-ului");
    } finally {
      setRunning(false);
    }
  };

  const autoFix = async () => {
    if (!window.confirm("Auto-fix va: 1) șterge toate doc_overrides și term_inconsistencies vechi din DB · 2) re-scanează terminologia · 3) rulează release gate-ul. Continuați?")) {
      return;
    }
    setAutoFixing(true);
    try {
      const { data } = await axios.post(`${API}/admin/qa/maintenance/auto-fix-release-gate`);
      const c = data.cleanup || {};
      const g = data.gate || {};
      toast.success(
        `🧹 Curățat ${c.deleted_overrides} overrides + ${c.deleted_inconsistencies} inc. · Gate: ${g.verdict} ${g.pass}/${g.total}`,
        { duration: 8000 }
      );
      loadHistory();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Auto-fix a eșuat");
    } finally {
      setAutoFixing(false);
    }
  };

  const verdict = last?.summary?.blocked ? "blocked" : (last ? "ready" : "none");
  const verdictColor = verdict === "blocked" ? "from-red-500 to-orange-500" : verdict === "ready" ? "from-emerald-500 to-lime-500" : "from-slate-500 to-slate-600";
  const verdictLabel = verdict === "blocked" ? "RELEASE BLOCKED" : verdict === "ready" ? "RELEASE READY" : "Niciun gate rulat încă";

  return (
    <AdminCard
      title={<span className="inline-flex items-center gap-2"><Rocket className="w-4 h-4" /> Release Gate · rulează TOATE testele înainte de deploy</span>}
      testid="qa-release-gate-card"
      action={
        <button onClick={loadHistory} className="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-white inline-flex items-center gap-1" data-testid="qa-gate-refresh">
          <RotateCw className="w-3.5 h-3.5" /> Refresh
        </button>
      }
    >
      <div className={`rounded-xl p-4 bg-gradient-to-br ${verdictColor} text-white relative overflow-hidden`}>
        <div className="text-[10px] uppercase tracking-wider opacity-80">Ultimul verdict</div>
        <div className="font-serif text-2xl font-bold" data-testid="qa-gate-verdict">{verdictLabel}</div>
        {last && (
          <div className="text-xs mt-1 opacity-90">
            <span data-testid="qa-gate-last-summary">{last.summary.pass}/{last.summary.total} pass · {last.summary.fail} fail{last.summary.skip ? ` · ${last.summary.skip} skip` : ""} · {last.summary.p0_fail} P0 fail</span>
            {" · "}
            <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" /> {new Date(last.started_at).toLocaleString("ro-RO")}</span>
            {last.email?.sent && (
              <span className="ml-2 inline-flex items-center gap-1"><Mail className="w-3 h-3" /> {last.email.recipients.length} admini</span>
            )}
          </div>
        )}
      </div>

      <p className="text-xs text-slate-500 mt-3 mb-2">
        Rulează toate testele automate (HTTP + Playwright) și trimite raportul detaliat pe email la admini.
        Folosește-l <strong>înainte de fiecare deploy în producție</strong> ca să prinzi regresii înainte ca utilizatorii să le vadă.
        Testele de browser (Playwright) sunt marcate <strong>SKIPPED</strong> automat dacă mediul nu are Chromium instalat — nu sunt eșecuri.
      </p>

      <label className="inline-flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 mb-3 cursor-pointer">
        <input type="checkbox" checked={emailEnabled} onChange={(e) => setEmailEnabled(e.target.checked)} data-testid="qa-gate-email-toggle" />
        <Mail className="w-3.5 h-3.5" /> Trimite raport pe email la admini
      </label>

      <div className="flex gap-2 flex-wrap">
        {!confirming ? (
          <AdminBtn variant="danger" onClick={() => setConfirming(true)} disabled={running || autoFixing} data-testid="qa-gate-run-btn">
            {running ? <><Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> Rulează gate (≈ 6s)...</> : <><Rocket className="w-3.5 h-3.5 inline mr-1" /> Rulează gate-ul de release</>}
          </AdminBtn>
        ) : (
          <>
            <AdminBtn variant="danger" onClick={runGate} data-testid="qa-gate-confirm-btn">
              <Rocket className="w-3.5 h-3.5 inline mr-1" /> Confirm · pornește gate-ul
            </AdminBtn>
            <AdminBtn variant="ghost" onClick={() => setConfirming(false)} data-testid="qa-gate-cancel-btn">Anulează</AdminBtn>
          </>
        )}
        <AdminBtn variant="ghost" onClick={autoFix} disabled={running || autoFixing} data-testid="qa-gate-autofix-btn">
          {autoFixing
            ? <><Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> Auto-fix în curs...</>
            : <><Wrench className="w-3.5 h-3.5 inline mr-1" /> Auto-fix · curăță & rerulează</>}
        </AdminBtn>
      </div>
      <p className="text-[11px] text-slate-500 mt-2">
        <Sparkles className="w-3 h-3 inline mr-1 text-amber-500" />
        <strong>Auto-fix</strong> e util mai ales post-deploy când vezi RELEASE BLOCKED din cauza unor override-uri vechi. Șterge stale DB rows, re-scanează și re-rulează gate-ul într-un click.
      </p>

      {/* History list */}
      {history.length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-2">Istoric ultimele {history.length} gate-uri</div>
          <ul className="space-y-1.5 max-h-[240px] overflow-y-auto pr-1" data-testid="qa-gate-history">
            {history.map((g) => {
              const blocked = g.summary?.blocked;
              return (
                <li key={g.gate_id} className={`text-xs p-2 rounded-lg border ${blocked ? "border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-800" : "border-emerald-200 bg-emerald-50 dark:bg-emerald-900/20 dark:border-emerald-800"}`}>
                  <div className="flex items-center justify-between flex-wrap gap-1">
                    <span className="font-mono">{g.gate_id}</span>
                    <span className={blocked ? "text-red-700 dark:text-red-300 font-semibold" : "text-emerald-700 dark:text-emerald-300 font-semibold"}>
                      {blocked ? "BLOCKED" : "READY"} · {g.summary.pass}/{g.summary.total}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    {new Date(g.started_at).toLocaleString("ro-RO")} · by {g.triggered_by} · {g.duration_ms}ms
                    {g.email?.sent && <span className="ml-1"> · 📧 sent</span>}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Last gate detail (per-test breakdown) */}
      {last?.results && (
        <details className="mt-4">
          <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-900 dark:hover:text-white" data-testid="qa-gate-details-toggle">
            Vezi rezultatele detaliate ({last.results.length} teste)
          </summary>
          <div className="mt-2 space-y-1 max-h-[300px] overflow-y-auto pr-1">
            {last.results.map((r) => {
              const isPass = r.status === "pass";
              const isSkip = r.status === "skip";
              const borderBg = isPass
                ? "border-emerald-200 bg-emerald-50 dark:bg-emerald-900/15 dark:border-emerald-800"
                : isSkip
                  ? "border-slate-300 bg-slate-50 dark:bg-slate-800/40 dark:border-slate-700"
                  : "border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-800";
              const icon = isPass
                ? <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                : isSkip
                  ? <MinusCircle className="w-3 h-3 text-slate-400" />
                  : <XCircle className="w-3 h-3 text-red-600" />;
              return (
                <div key={r.code} className={`text-[11px] p-1.5 rounded border ${borderBg}`} data-testid={`qa-gate-result-${r.code}`}>
                  <div className="flex items-center gap-2">
                    {icon}
                    <code className="font-mono">{r.code}</code>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${PRIO_BADGE[r.priority]}`}>{r.priority}</span>
                    {isSkip && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300">SKIPPED</span>}
                    <span className="text-slate-500 ml-auto">{r.duration_ms}ms</span>
                  </div>
                  <div className="text-slate-700 dark:text-slate-200 mt-0.5">{r.title}</div>
                  <div className="text-slate-500 italic mt-0.5">📋 {r.note?.slice(0, 200)}</div>
                </div>
              );
            })}
          </div>
        </details>
      )}
    </AdminCard>
  );
};



// ----------------------------------------------------------------------------
// Main page
// ----------------------------------------------------------------------------


// ----------------------------------------------------------------------------
// Content Audit — detected doc conflicts (audience mismatch) + AI auto-fix
// ----------------------------------------------------------------------------
