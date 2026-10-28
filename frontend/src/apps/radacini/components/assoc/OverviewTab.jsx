import React, { useEffect, useState } from "react";
import { CARD } from "../../../../design-system";
import { COUNCIL_ROLE, assocMembers, canSeeRegistry, fmtShare, meetingsList, transparency } from "../../api_s9";
import { fmtDate } from "../../shared";
import TransparencyBadge from "./TransparencyBadge";

const asArr = (d) => (Array.isArray(d) ? d : d?.items || []);

export default function OverviewTab({ assoc, access }) {
  const id = assoc?.id;
  const [organs, setOrgans] = useState(assoc?.organs || null);
  const [meeting, setMeeting] = useState(undefined);
  const [tr, setTr] = useState(null);

  useEffect(() => {
    if (!id) return;
    if (canSeeRegistry(access)) {
      assocMembers(id).then((d) => setOrgans(asArr(d).filter((r) => r.council_role).map((r) => ({ name: r.name, role: r.council_role })))).catch(() => {});
    }
    meetingsList(id)
      .then((d) => {
        const now = Date.now();
        const next = asArr(d).filter((m) => new Date(m.date).getTime() >= now - 86400000).sort((a, b) => new Date(a.date) - new Date(b.date))[0];
        setMeeting(next || null);
      })
      .catch(() => setMeeting(null));
    if (assoc?.score_visible !== false) transparency(id).then(setTr).catch(() => {});
  }, [id, access?.role, assoc?.score_visible]);

  const patrimony = assoc?.patrimony || [];
  const alerts = access?.alerts || assoc?.alerts || [];
  const comps = tr?.components ? (Array.isArray(tr.components) ? tr.components : Object.entries(tr.components).map(([k, v]) => ({ key: k, ...(typeof v === "object" ? v : { score: v }) }))).map((c) => ({ ...c, score: c.score ?? (c.value != null ? c.value * 100 : null) })) : [];

  return (
    <div className="space-y-4" data-testid="assoc-overview">
      {assoc?.description && <p className="text-sm text-slate-700 dark:text-slate-200">{assoc.description}</p>}

      <div className={`${CARD} p-5 space-y-3`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-bold text-slate-900 dark:text-white">Scor de transparență</h3>
          {assoc?.score_visible === false ? (
            <span className="text-xs text-slate-500 dark:text-slate-400">Vizibil doar membrilor asociației</span>
          ) : (
            <TransparencyBadge assocId={id} />
          )}
        </div>
        {comps.length > 0 && (
          <div className="space-y-2">
            {comps.map((c) => (
              <div key={c.key}>
                <div className="flex justify-between text-xs text-slate-600 dark:text-slate-300"><span title={c.explanation || undefined}>{c.label || c.key}</span><span>{Math.round(c.score ?? 0)}%</span></div>
                <div className="h-2 rounded-full bg-slate-200 dark:bg-white/10"><div className="h-2 rounded-full bg-emerald-500" style={{ width: `${Math.min(100, Math.max(0, c.score ?? 0))}%` }} /></div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className={`${CARD} p-5`}>
        <h3 className="font-bold text-slate-900 dark:text-white mb-2">Următoarea ședință</h3>
        {meeting === undefined ? <p className="text-sm text-slate-500">Se încarcă…</p> : meeting ? (
          <p className="text-sm text-slate-700 dark:text-slate-200">{fmtDate(meeting.date)} · {meeting.place || "loc nestabilit"} · {meeting.kind === "council" ? "Ședință CA" : "AGA"}</p>
        ) : <p className="text-sm text-slate-500">Nicio ședință programată.</p>}
      </div>

      {alerts.length > 0 && (
        <div className={`${CARD} p-5 space-y-1`} data-testid="assoc-overview-alerts">
          <h3 className="font-bold text-slate-900 dark:text-white">Alerte</h3>
          {alerts.map((a, i) => <p key={i} className="text-sm text-amber-700 dark:text-amber-300">{a.message || a.title || String(a)}</p>)}
        </div>
      )}

      <div className={`${CARD} p-5`}>
        <h3 className="font-bold text-slate-900 dark:text-white mb-2">Organe de conducere</h3>
        {!organs || organs.length === 0 ? <p className="text-sm text-slate-500">Date indisponibile.</p> : (
          <ul className="text-sm space-y-1">
            {organs.map((o, i) => <li key={i}><span className="font-semibold">{COUNCIL_ROLE[o.role] || o.role}:</span> {o.name}</li>)}
          </ul>
        )}
      </div>

      <div className={`${CARD} p-5 overflow-x-auto`}>
        <h3 className="font-bold text-slate-900 dark:text-white mb-2">Patrimoniu</h3>
        {patrimony.length === 0 ? <p className="text-sm text-slate-500">Nu este înregistrat patrimoniu.</p> : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-slate-500"><th className="py-1">CF</th><th>Topo</th><th>Toponim</th><th>Categorie</th><th className="text-right">Ha</th></tr></thead>
            <tbody>
              {patrimony.map((p, i) => (
                <tr key={i} className="border-t border-slate-100 dark:border-white/10">
                  <td className="py-1">{p.cf}</td><td>{p.topo}</td><td>{p.toponym}</td><td>{p.category}</td><td className="text-right">{fmtShare(p.area_ha)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
