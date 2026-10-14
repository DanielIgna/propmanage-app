import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CARD, EmptyState } from "../../../../design-system";
import { Landmark } from "lucide-react";
import { MEMBER_STATUS, fmtShare } from "../../api_s9";
import { financeGet } from "../../api_s9";
import { fmtDate } from "../../shared";

const CLAIM_ST = { pending: "În analiză", approved: "Aprobată", rejected: "Respinsă" };

export default function MyShareTab({ assoc, access }) {
  const m = access?.member;
  const claims = access?.claims || [];
  const [fin, setFin] = useState(null);
  useEffect(() => {
    if (!m || !assoc?.id) return;
    financeGet(assoc.id).then(setFin).catch(() => setFin(null));
  }, [m, assoc?.id]);

  const mine = fin?.my_distributions || fin?.mine || [];
  const st = m ? MEMBER_STATUS[m.status] : null;
  return (
    <div className="space-y-4" data-testid="assoc-myshare">
      {!m ? (
        <EmptyState icon={Landmark} title="Nu ești legat de un rând din registru" hint="Dacă ești membru sau moștenitor, trimite o revendicare." action={<Link to={`/radacini/composesorate/revendica?assoc=${assoc?.id}`} className="underline font-semibold">Revendică</Link>} />
      ) : (
        <div className={`${CARD} p-5 space-y-3`}>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">{m.name}</h3>
            <span className="text-xs text-slate-500">Cod {m.code}</span>
            {st && <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${st.cls}`}>{st.label}</span>}
          </div>
          <p className="text-3xl font-extrabold text-slate-900 dark:text-white" data-testid="assoc-myshare-shares">
            {fmtShare(m.shares)} <span className="text-base font-semibold text-slate-500">cote</span>
          </p>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Cota ta se compune din sursele de mai jos (de exemplu „Nr 372 = 0,20” înseamnă poziția 372 din tabelul de membri, cu cota 0,20).
          </p>
          <ul className="space-y-1 text-sm">
            {(m.sources || []).length === 0 && <li className="text-slate-500">Nu sunt surse înregistrate.</li>}
            {(m.sources || []).map((s, i) => (
              <li key={i} className="rounded-lg bg-slate-50 dark:bg-white/5 px-3 py-1.5">{typeof s === "string" ? s : `${s.ref || s.label} = ${fmtShare(s.share)}`}</li>
            ))}
          </ul>
        </div>
      )}

      {m && (
        <div className={`${CARD} p-5 space-y-2`}>
          <h3 className="font-bold text-slate-900 dark:text-white">Sumele cuvenite</h3>
          {mine.length === 0 ? (
            <p className="text-sm text-slate-500">Nu ai sume înregistrate.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {mine.map((d, i) => (
                <li key={d.id || i} className="flex flex-wrap justify-between gap-2">
                  <span>{d.year}: {Number(d.amount).toLocaleString("ro-RO")} RON {d.paid ? "(plătit)" : "(neridicat)"}</span>
                  {!d.paid && d.prescribes_at && <span className="text-amber-700 dark:text-amber-300">se prescrie la {fmtDate(d.prescribes_at)}</span>}
                </li>
              ))}
            </ul>
          )}
          <Link to="?tab=finante" className="text-sm underline font-semibold">Vezi finanțele</Link>
        </div>
      )}

      <div className={`${CARD} p-5 space-y-2`}>
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-bold text-slate-900 dark:text-white">Revendicările mele</h3>
          <Link to={`/radacini/composesorate/revendica?assoc=${assoc?.id}`} className="text-sm underline font-semibold">Revendică</Link>
        </div>
        {claims.length === 0 ? (
          <p className="text-sm text-slate-500">Nu ai trimis nicio revendicare.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {claims.map((c) => (
              <li key={c.id}>
                {c.kind === "heir" ? "Moștenitor" : "Sunt eu"} · {CLAIM_ST[c.status] || c.status} · {fmtDate(c.created_at)}
                {c.decision_note ? ` · ${c.decision_note}` : ""}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
