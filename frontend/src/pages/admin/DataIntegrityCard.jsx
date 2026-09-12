// Data Integrity Check — admin scanner for orphans, inconsistencies, lost money.
import React, { useState } from "react";
import axios from "axios";
import { Database, CheckCircle2, XCircle, AlertTriangle, ShieldCheck, RefreshCw, ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

const SEVERITY = {
  high:    { label: "CRITIC",  fail: "bg-red-50 border-red-200 dark:bg-red-500/15 dark:border-red-500/40 text-red-700 dark:text-red-300",
             badge: "bg-red-200/60 text-red-700 dark:bg-red-500/20 dark:text-red-300" },
  warning: { label: "WARN",    fail: "bg-amber-50 border-amber-200 dark:bg-amber-500/15 dark:border-amber-500/40 text-amber-700 dark:text-amber-300",
             badge: "bg-amber-200/60 text-amber-800 dark:bg-amber-500/20 dark:text-amber-300" },
  info:    { label: "INFO",    fail: "bg-slate-100 border-slate-200 dark:bg-slate-800 dark:border-slate-700 text-slate-600 dark:text-slate-400",
             badge: "bg-slate-200/60 text-slate-600 dark:bg-slate-700 dark:text-slate-400" },
};

export const DataIntegrityCard = () => {
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [resolving, setResolving] = useState(false);
  const [confirmOrphan, setConfirmOrphan] = useState(false);
  const [resolveMsg, setResolveMsg] = useState(null);

  const run = async () => {
    setRunning(true);
    try {
      const r = await axios.get(`${API}/admin/data-integrity/run`);
      setReport(r.data);
      // Auto-expand failed checks
      const exp = {};
      (r.data.checks || []).forEach((c, i) => { if (!c.ok) exp[i] = true; });
      setExpanded(exp);
    } catch (e) {
      window.alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setRunning(false);
    }
  };

  const toggle = (i) => setExpanded(e => ({ ...e, [i]: !e[i] }));

  const resolveOrphanTwins = async () => {
    setResolving(true); setResolveMsg(null);
    try {
      const r = await axios.post(`${API}/admin/data-integrity/orphan-twins/resolve`, {
        action: "delete_orphan", twin_ids: null, confirm: true,
      });
      setResolveMsg(r.data);
      setConfirmOrphan(false);
      await run(); // re-scan to confirm orphan twins = 0
    } catch (e) {
      setResolveMsg({ error: e?.response?.data?.detail || e.message });
    } finally {
      setResolving(false);
    }
  };

  return (
    <AdminCard
      title={
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-purple-500" />
          <span>Data Integrity Check</span>
          <span className="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300">NEW</span>
        </div>
      }
      action={
        <AdminBtn variant="primary" onClick={run} disabled={running} data-testid="data-integrity-run-btn">
          <RefreshCw className={`w-3.5 h-3.5 ${running ? "animate-spin" : ""}`} />
          {running ? "Scanez..." : "Verifică integritatea"}
        </AdminBtn>
      }
    >
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-3 leading-relaxed">
        Scanează baza de date pentru inconsistențe: twins orfane, proprietăți fără owner valid,
        wallet/tranzacții mismatch, dispute pe cereri închise, emailuri duplicate.
        Read-only — nu modifică nimic, doar raportează.
      </p>

      {report && (
        <>
          {/* Summary banner */}
          <div className={`rounded-xl border p-3 mb-3 ${
            report.ok
              ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30"
              : report.summary.critical_failed > 0
                ? "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30"
                : "bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/30"
          }`} data-testid="data-integrity-summary">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                {report.ok
                  ? <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                  : report.summary.critical_failed > 0
                    ? <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                    : <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                }
                <div>
                  <div className="font-semibold text-sm">
                    {report.ok
                      ? "Toate verificările au trecut"
                      : `${report.summary.total_issues_found} probleme detectate`}
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                    {report.summary.passed}/{report.summary.total_checks} verificări OK ·
                    {" "}{report.summary.critical_failed} critice ·
                    {" "}{report.summary.warnings_failed} warning-uri
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold">{report.total_duration_ms}ms</div>
                <div className="text-[9px] uppercase tracking-wider text-slate-400">durată</div>
              </div>
            </div>
          </div>

          {/* Per-check results */}
          <div className="space-y-2" data-testid="data-integrity-checks">
            {report.checks.map((c, i) => {
              const sev = SEVERITY[c.severity] || SEVERITY.info;
              return (
                <div
                  key={i}
                  className={`rounded-lg border ${
                    c.ok
                      ? "bg-emerald-50/60 dark:bg-emerald-500/5 border-emerald-200/60 dark:border-emerald-500/20"
                      : sev.fail
                  }`}
                  data-testid={`data-integrity-check-${i}`}
                >
                  <button
                    onClick={() => toggle(i)}
                    className="w-full text-left p-3 flex items-start gap-2"
                  >
                    {c.ok
                      ? <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                      : <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    }
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="font-semibold text-sm">{c.name}</span>
                        <span className={`text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded ${sev.badge}`}>{sev.label}</span>
                        {!c.ok && (
                          <span className="text-[10px] font-bold ml-auto bg-white/40 dark:bg-black/20 px-1.5 py-0.5 rounded">
                            {c.issue_count} probleme
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] opacity-80 mt-0.5">{c.description}</div>
                      <div className="text-[10px] opacity-60 mt-1 font-mono">{c.duration_ms}ms</div>
                    </div>
                    {!c.ok && c.samples?.length > 0 && (
                      expanded[i]
                        ? <ChevronUp className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                        : <ChevronDown className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                    )}
                  </button>
                  {!c.ok && expanded[i] && c.samples?.length > 0 && (
                    <div className="px-3 pb-3 space-y-1.5" data-testid={`data-integrity-samples-${i}`}>
                      <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-500 mb-1">
                        Primele {c.samples.length} exemple
                      </div>
                      {c.samples.map((s, j) => (
                        <div key={j} className="bg-white/60 dark:bg-black/20 rounded p-2 text-[11px] font-mono break-all overflow-x-auto">
                          {JSON.stringify(s, null, 2)}
                        </div>
                      ))}
                    </div>
                  )}
                  {!c.ok && c.name === "Twins orfane" && (
                    <div className="px-3 pb-3" data-testid="orphan-twins-actions">
                      {!confirmOrphan ? (
                        <button
                          onClick={() => { setConfirmOrphan(true); setResolveMsg(null); }}
                          disabled={resolving}
                          className="w-full px-3 py-2 rounded-lg text-xs font-semibold bg-red-600 hover:bg-red-700 text-white disabled:opacity-50 inline-flex items-center justify-center gap-2"
                          data-testid="orphan-twins-delete-all-btn"
                        >
                          <Trash2 className="w-3.5 h-3.5" /> Șterge toate Twin-urile orfane ({c.issue_count})
                        </button>
                      ) : (
                        <div className="rounded-lg border border-red-300 dark:border-red-500/40 bg-red-50 dark:bg-red-500/10 p-3 space-y-2" data-testid="orphan-twins-confirm">
                          <div className="text-[11px] text-red-800 dark:text-red-200 leading-relaxed">
                            Aceste {c.issue_count} Twin-uri nu mai au o proprietate validă. Ștergerea elimină (și arhivează, recuperabil din <span className="font-mono">twins_orphan_archive</span>) DOAR recordurile Twin identificate.
                            <strong> Proprietățile, utilizatorii, cererile, tranzacțiile și dispute-urile NU vor fi șterse.</strong>
                          </div>
                          <div className="flex gap-2">
                            <button onClick={resolveOrphanTwins} disabled={resolving}
                              className="flex-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600 hover:bg-red-700 text-white disabled:opacity-50 inline-flex items-center justify-center gap-2"
                              data-testid="orphan-twins-confirm-yes">
                              {resolving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                              Da, șterge (arhivează)
                            </button>
                            <button onClick={() => setConfirmOrphan(false)} disabled={resolving}
                              className="px-3 py-1.5 rounded-lg text-xs bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200"
                              data-testid="orphan-twins-confirm-no">Anulează</button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {resolveMsg && (
            <div className={`mt-3 text-[11px] rounded-lg p-2.5 ${resolveMsg.error ? "bg-red-100 dark:bg-red-500/15 text-red-700 dark:text-red-300" : "bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"}`} data-testid="orphan-twins-result">
              {resolveMsg.error ? `Eroare: ${resolveMsg.error}` : resolveMsg.message}
            </div>
          )}

          <div className="mt-3 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1.5 px-1">
            <ShieldCheck className="w-3 h-3" />
            Scanner cu acțiune de remediere sigură pentru Twins orfane (arhivare + ștergere, recuperabil). Celelalte verificări rămân informative.
          </div>
        </>
      )}

      {!report && (
        <div className="text-center py-6 text-slate-400 italic text-xs" data-testid="data-integrity-empty">
          Apasă "Verifică integritatea" pentru a porni scanarea bazei de date.
        </div>
      )}
    </AdminCard>
  );
};
