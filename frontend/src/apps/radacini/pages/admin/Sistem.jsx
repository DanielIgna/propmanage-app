import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, HeartPulse, RefreshCw } from "lucide-react";
import { CARD, DSButton, EmptyState } from "../../../../design-system";
import { errMsg } from "../../api";
import { betaApi } from "../../api_beta";
import { fmtDateTime, PageSkeleton } from "../../shared";

const EMAIL = { resend: "Resend", sendgrid: "SendGrid", console: "Neconfigurat (nu se trimit)" };
const QUEUES = [
  ["reports_open", "Raportări de analizat"],
  ["disputes_open", "Dispute deschise"],
  ["parcels_pending", "Terenuri de verificat"],
  ["deletion_pending", "Cereri de ștergere (GDPR)"],
];

const Row = ({ label, value, ok }) => (
  <div className="flex items-center justify-between gap-3 py-1.5 text-sm">
    <span className="text-slate-600 dark:text-slate-300">{label}</span>
    <span className={`font-semibold ${ok === false ? "text-red-700 dark:text-red-300" : "text-slate-900 dark:text-white"}`}>{value}</span>
  </div>
);

export default function Sistem() {
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const load = useCallback(() => {
    setState((s) => ({ ...s, loading: true }));
    betaApi.system().then(
      (data) => setState({ loading: false, data, error: null }),
      (error) => setState({ loading: false, data: null, error })
    );
  }, []);
  useEffect(() => { load(); }, [load]);

  if (state.loading && !state.data) return <PageSkeleton />;
  if (state.error) return <EmptyState icon={HeartPulse} title="Nu am putut încărca starea sistemului" hint={errMsg(state.error)} />;
  const d = state.data;
  const c = d.config;

  return (
    <div className="space-y-4" data-testid="radacini-admin-sistem">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-500">Verificat la {fmtDateTime(d.checked_at)}</p>
        <DSButton variant="secondary" icon={RefreshCw} onClick={load} disabled={state.loading}>Reîmprospătează</DSButton>
      </div>

      {d.warnings.length ? (
        <ul className="rounded-xl border border-amber-300 bg-amber-50 dark:border-amber-500/40 dark:bg-amber-500/10 p-3 space-y-1" data-testid="radacini-sistem-warnings">
          {d.warnings.map((w) => (
            <li key={w} className="flex items-start gap-2 text-sm text-amber-900 dark:text-amber-100">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" aria-hidden /> {w}
            </li>
          ))}
        </ul>
      ) : (
        <p className="flex items-center gap-2 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 p-3 text-sm text-emerald-800 dark:text-emerald-200">
          <CheckCircle2 className="h-4 w-4" aria-hidden /> Totul arată bine.
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <section className={`${CARD} p-4`}>
          <h3 className="font-bold mb-2 text-slate-900 dark:text-white">Configurare</h3>
          <Row label="Baza de date" value={d.db.ok ? `răspunde (${d.db.latency_ms} ms)` : "nu răspunde"} ok={d.db.ok} />
          <Row label="Modul pornit" value={c.enabled ? "da" : "nu"} ok={c.enabled} />
          <Row label="Acces" value={c.closed_beta ? `beta închis (${c.allowed_count} invitați)` : "deschis tuturor"} />
          <Row label="Emailuri" value={EMAIL[c.email_provider] || c.email_provider} ok={c.email_provider !== "console"} />
          <Row label="Marcare date demo" value={c.mark_demo ? "pornită" : "oprită"} ok={!c.mark_demo} />
        </section>
        <section className={`${CARD} p-4`}>
          <h3 className="font-bold mb-2 text-slate-900 dark:text-white">Cozi pentru personal</h3>
          {QUEUES.map(([k, label]) => <Row key={k} label={label} value={d.queues[k] ?? 0} />)}
        </section>
      </div>

      <section className={`${CARD} p-4 space-y-2`}>
        <h3 className="font-bold text-slate-900 dark:text-white">Erori neprevăzute (ultimele 24 de ore): {d.errors_24h}</h3>
        <p className="text-xs text-slate-500">Se păstrează {d.error_retention_days} zile. Se salvează doar ruta și tipul erorii, fără date personale.</p>
        {d.errors_by_route.length > 0 && (
          <ul className="text-sm space-y-1">
            {d.errors_by_route.map((e) => (
              <li key={e.route} className="flex justify-between gap-2"><code className="break-all">{e.route}</code><b>{e.count}</b></li>
            ))}
          </ul>
        )}
        {d.recent_errors.length > 0 && (
          <details className="text-xs">
            <summary className="cursor-pointer font-semibold">Ultimele {d.recent_errors.length} erori</summary>
            <ul className="mt-2 space-y-1">
              {d.recent_errors.map((e, i) => (
                <li key={`${e.at}-${i}`} className="break-words">
                  {fmtDateTime(e.at)} · <code>{e.method} {e.route}</code> · {e.error_type}: {e.message}
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>
    </div>
  );
}
