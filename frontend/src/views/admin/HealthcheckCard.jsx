// Healthcheck card — pings all external integrations (MongoDB, LLM, Email,
// Stripe, OAuth, Push) and shows a per-integration status grid.
import React, { useState } from "react";
import axios from "axios";
import { Activity, CheckCircle2, XCircle, AlertTriangle, Info, RefreshCw } from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

const SEVERITY_META = {
  high:    { label: "CRITIC",  icon: XCircle,       fail: "text-red-600 bg-red-50 border-red-200 dark:bg-red-500/15 dark:border-red-500/40 dark:text-red-300" },
  warning: { label: "WARN",    icon: AlertTriangle, fail: "text-amber-700 bg-amber-50 border-amber-200 dark:bg-amber-500/15 dark:border-amber-500/40 dark:text-amber-300" },
  info:    { label: "INFO",    icon: Info,          fail: "text-slate-600 bg-slate-100 border-slate-200 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-400" },
};

export const HealthcheckCard = () => {
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState(null);

  const run = async () => {
    setRunning(true);
    try {
      const r = await axios.get(`${API}/admin/healthcheck/run`);
      setReport(r.data);
    } catch (e) {
      window.alert(`Healthcheck eșuat: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <AdminCard
      title={
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-500" />
          <span>Healthcheck Servicii Externe</span>
          <span className="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300">NEW</span>
        </div>
      }
      action={
        <AdminBtn variant="primary" onClick={run} disabled={running} data-testid="healthcheck-run-btn">
          <RefreshCw className={`w-3.5 h-3.5 ${running ? "animate-spin" : ""}`} />
          {running ? "Verific..." : "Verifică integrările"}
        </AdminBtn>
      }
    >
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-3 leading-relaxed">
        Verifică în paralel: MongoDB, Emergent LLM Key, provider email (Resend/SendGrid),
        Stripe, Google OAuth, VAPID push și destinatari alerte admin.
        <strong> CRITIC</strong> = app nu funcționează fără el · <strong>WARN</strong> = funcționalitate degradată · <strong>INFO</strong> = opțional.
      </p>

      {report && (
        <>
          <div className={`rounded-xl p-3 mb-3 border ${
            report.ok
              ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30"
              : "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30"
          }`} data-testid="healthcheck-summary">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                {report.ok
                  ? <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                  : <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                }
                <div>
                  <div className={`font-semibold text-sm ${report.ok ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300"}`}>
                    {report.ok ? "Toate integrările critice funcționează" : `${report.summary.critical_failed} integrare(i) critice picate`}
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                    {report.summary.passed}/{report.summary.total} OK · {report.summary.warnings_failed} warning · {report.summary.info_failed} info
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold text-slate-700 dark:text-slate-200">{report.total_duration_ms}ms</div>
                <div className="text-[9px] uppercase tracking-wider text-slate-400">durată</div>
              </div>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-2" data-testid="healthcheck-grid">
            {report.checks.map((c, i) => {
              const meta = SEVERITY_META[c.severity] || SEVERITY_META.info;
              const Icon = c.ok ? CheckCircle2 : meta.icon;
              return (
                <div
                  key={i}
                  className={`flex items-start gap-2 p-3 rounded-lg border text-xs ${
                    c.ok
                      ? "bg-emerald-50/60 dark:bg-emerald-500/5 border-emerald-200/60 dark:border-emerald-500/20"
                      : meta.fail
                  }`}
                  data-testid={`healthcheck-${c.name.toLowerCase().replace(/\s+/g, "-")}`}
                >
                  <Icon className={`w-4 h-4 shrink-0 mt-0.5 ${c.ok ? "text-emerald-500" : ""}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="font-semibold">{c.name}</span>
                      <span className={`text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded ${
                        c.severity === "high"    ? "bg-red-200/60 text-red-700 dark:bg-red-500/20 dark:text-red-300"
                        : c.severity === "warning" ? "bg-amber-200/60 text-amber-800 dark:bg-amber-500/20 dark:text-amber-300"
                        : "bg-slate-200/60 text-slate-600 dark:bg-slate-700 dark:text-slate-400"
                      }`}>{meta.label}</span>
                    </div>
                    <div className="text-[11px] opacity-80 mt-0.5 leading-snug">{c.detail}</div>
                    <div className="text-[10px] opacity-60 mt-1 font-mono">
                      status: {c.status} · {c.duration_ms}ms
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {!report && (
        <div className="text-center py-6 text-slate-400 italic text-xs" data-testid="healthcheck-empty">
          Apasă "Verifică integrările" pentru a porni diagnosticul.
        </div>
      )}
    </AdminCard>
  );
};
