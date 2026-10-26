import React, { useCallback, useEffect, useState } from "react";
import { EmptyState } from "../../../../design-system";
import { errMsg } from "../../api";
import { s9Api } from "../../api_s9";

const ROLE = { manager: "Manager", operator: "Operator", president: "Președinte", vice_president: "Vicepreședinte", secretary: "Secretar", cashier: "Casier", forest_pasture: "Responsabil pădure/pășune", censor: "Cenzor", council: "Consiliu", admin: "Administrator" };
const ACTION = {
  "assoc.create": "Asociație creată", "assoc.update": "Datele asociației modificate",
  "member.add": "Membru adăugat în registru", "member.import": "Registru importat", "member.update": "Rând din registru modificat",
  "claim.approve_self": "Revendicare aprobată (titular)", "claim.approve_heir": "Revendicare aprobată (moștenitor)", "claim.reject": "Revendicare respinsă",
  "document.upload": "Document publicat", "meeting.create": "Ședință programată", "meeting.convene": "Convocare trimisă",
  "meeting.registered_mail": "Convocare prin poștă (dovadă)", "meeting.attendance": "Prezență consemnată", "meeting.decisions": "Hotărâri consemnate",
  "petition.respond": "Răspuns la petiție", "request.answer": "Răspuns la cerere de informații",
  obligation_evidence: "Dovadă pentru o obligație statutară", finance_year_create: "An financiar adăugat",
  finance_distribute: "Profit repartizat pe membri", distribution_paid: "Sumă plătită unui membru",
};
const TARGET = { association: "asociație", member: "membru", claim: "revendicare", document: "document", meeting: "ședință", petition: "petiție", request: "cerere", obligation: "obligație", finance_year: "an financiar", distribution: "distribuire" };
const fmtDT = (d) => (d ? new Date(d).toLocaleString("ro-RO") : "—");
const asArr = (d) => (Array.isArray(d) ? d : d?.items || d?.entries || []);
const pretty = (v) => {
  try { return JSON.stringify(v, null, 2); } catch { return String(v); }
};

function Entry({ e, full }) {
  const [open, setOpen] = useState(false);
  const hasDiff = full && (e.before != null || e.after != null);
  return (
    <li className="rounded-xl border border-slate-200 bg-white p-3" data-testid={`audit-entry-${e.id || e._id || e.at}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-1">
        <span className="font-semibold break-words">{e.action_label || ACTION[e.action] || e.action}</span>
        <span className="text-xs text-slate-500">{fmtDT(e.at)}</span>
      </div>
      <p className="text-xs text-slate-600">
        {ROLE[e.actor_role] || e.actor_role || "—"}
        {full && e.actor_name ? ` · ${e.actor_name}` : ""}
        {full && e.target_type ? ` · ${TARGET[e.target_type] || e.target_type}` : ""}
      </p>
      {hasDiff && (
        <>
          <button type="button" className="mt-1 text-xs font-bold text-emerald-700 underline" onClick={() => setOpen(!open)} aria-expanded={open}>
            {open ? "Ascunde modificarea" : "Arată înainte / după"}
          </button>
          {open && (
            <div className="mt-2 grid gap-2 md:grid-cols-2">
              {[["Înainte", e.before], ["După", e.after]].map(([t, v]) => (
                <div key={t}>
                  <p className="text-xs font-bold">{t}</p>
                  <pre className="max-h-64 overflow-auto rounded-lg bg-slate-50 p-2 text-xs">{v == null ? "—" : pretty(v)}</pre>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </li>
  );
}

export default function AuditTab({ assoc, access }) {
  const id = assoc?.id;
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  const full = ["censor", "manager", "operator"].includes(access?.role);

  const load = useCallback(() => {
    setItems(null);
    setError(null);
    s9Api
      .audit(id, { limit: 200 })
      .then((d) => setItems(asArr(d)))
      .catch((e) => setError(errMsg(e, "Nu am putut încărca jurnalul")));
  }, [id]);

  useEffect(() => {
    if (id) load();
  }, [id, load]);

  return (
    <div className="space-y-4" data-testid="audit-tab">
      <div className="rounded-xl bg-slate-50 p-4">
        <h2 className="text-lg font-bold">Jurnal de răspundere</h2>
        <p className="text-sm text-slate-700">Jurnal care nu poate fi șters: fiecare acțiune a conducerii rămâne vizibilă.</p>
        {!full && <p className="mt-1 text-xs text-slate-500">Membrii văd un rezumat; modificările detaliate sunt vizibile cenzorilor și managerului.</p>}
      </div>
      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert" data-testid="audit-error">
          {error} <button className="ml-2 underline" onClick={load}>Reîncearcă</button>
        </div>
      ) : items === null ? (
        <div className="space-y-2" data-testid="audit-loading">
          {[0, 1, 2].map((i) => <div key={i} className="h-14 animate-pulse rounded-xl bg-slate-100" />)}
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="Nu există acțiuni înregistrate." testid="audit-empty" />
      ) : (
        <ul className="space-y-2" data-testid="audit-list">
          {items.map((e, i) => <Entry key={e.id || e._id || i} e={e} full={full} />)}
        </ul>
      )}
    </div>
  );
}
