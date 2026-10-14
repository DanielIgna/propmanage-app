import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { DSButton, EmptyState } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { errMsg } from "../../api";
import { s9Api } from "../../api_s9";
import { useConfirm } from "../ConfirmDialog";

const MAXIMA = { council: 0.1, reserve: 0.2, charity: 0.2, investment: 0.2 };
const SPLIT_LABEL = { council: "Consiliu de administrație", reserve: "Rezervă", charity: "Sponsorizări", investment: "Investiții", members: "Membri (restul)" };
const SPLIT_LIMIT = { council: "max 10%", reserve: "max 20%", charity: "max 20%", investment: "max 20%", members: "restul" };
const REV_CATS = ["Vânzare lemn", "Închirieri pășuni", "Subvenții", "Alte venituri"];
const EXP_CATS = ["Administrare", "Pază și întreținere", "Impozite", "Alte cheltuieli"];
const NEAR_DAYS = 365;

const ron = (v) => `${Number(v || 0).toLocaleString("ro-RO", { maximumFractionDigits: 2 })} RON`;
const fmt = (d) => (d ? new Date(d).toLocaleDateString("ro-RO") : "—");
const sum = (o) => Object.values(o || {}).reduce((a, b) => a + Number(b || 0), 0);
const todayStr = () => new Date().toISOString().slice(0, 10);

const Breakdown = ({ title, obj }) => (
  <div>
    <p className="text-xs font-bold text-slate-600">{title}</p>
    {Object.keys(obj || {}).length === 0 ? <p className="text-xs text-slate-500">—</p> : (
      <ul className="text-sm">
        {Object.entries(obj).map(([k, v]) => (
          <li key={k} className="flex justify-between gap-2"><span className="min-w-0 break-words">{k}</span><span>{ron(v)}</span></li>
        ))}
      </ul>
    )}
  </div>
);

function SplitBars({ year }) {
  const profit = Number(year.net_profit || 0);
  return (
    <div className="space-y-2" data-testid={`finance-split-${year.year}`}>
      {Object.keys(SPLIT_LABEL).map((k) => {
        const amt = Number(year.split?.[k] || 0);
        const pct = profit > 0 ? (amt / profit) * 100 : 0;
        const over = MAXIMA[k] != null && profit > 0 && amt / profit > MAXIMA[k] + 1e-6;
        return (
          <div key={k}>
            <div className="flex justify-between gap-2 text-xs">
              <span>{SPLIT_LABEL[k]} <span className="text-slate-500">({SPLIT_LIMIT[k]})</span></span>
              <span className={over ? "font-bold text-red-700" : ""}>{ron(amt)} · {pct.toFixed(1)}%</span>
            </div>
            <div className="relative h-2.5 rounded-full bg-slate-100">
              <div className={`h-full rounded-full ${over ? "bg-red-500" : "bg-emerald-500"}`} style={{ width: `${Math.min(100, pct)}%` }} />
              {MAXIMA[k] != null && <div className="absolute top-[-2px] h-[14px] w-0.5 bg-slate-700" style={{ left: `${MAXIMA[k] * 100}%` }} title="Maxim statutar" />}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function FinanceTab({ assoc, access, reload }) {
  const id = assoc?.id;
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [create, setCreate] = useState(false);
  const [distFor, setDistFor] = useState(null);
  const [agaDate, setAgaDate] = useState(todayStr());
  const [busy, setBusy] = useState(false);
  const [confirm, confirmDialog] = useConfirm();

  const staff = ["manager", "operator"].includes(access?.role) || (access?.role === "council" && ["president", "vice_president", "secretary", "cashier"].includes(access?.council_role));
  const canWrite = ["manager", "operator"].includes(access?.role) || (access?.role === "council" && ["president", "cashier"].includes(access?.council_role));
  const canPay = ["manager", "operator"].includes(access?.role) || (access?.role === "council" && access?.council_role === "cashier");
  const seesAll = staff || access?.role === "censor";

  const load = useCallback(() => {
    setData(null);
    setError(null);
    s9Api.financeGet(id).then(setData).catch((e) => setError(errMsg(e, "Nu am putut încărca finanțele")));
  }, [id]);
  useEffect(() => { if (id) load(); }, [id, load]);

  const refresh = () => { load(); reload?.(); };

  const distribute = async () => {
    setBusy(true);
    try {
      await s9Api.financeDistribute(id, distFor, { aga_date: agaDate });
      toast.success("Sumele au fost calculate pe membri");
      setDistFor(null);
      refresh();
    } catch (e) {
      toast.error(e?.response?.status === 409 ? "Distribuirea există deja pentru acest an" : errMsg(e, "Nu am putut distribui"));
    } finally { setBusy(false); }
  };

  const markPaid = async (d) => {
    if (!(await confirm({ title: "Marchezi suma ca plătită?", description: `${ron(d.amount)} pentru ${d.member_name || "membru"}, anul ${d.year}. Acțiunea se înregistrează în jurnal.`, confirmLabel: "Marchează plătit" }))) return;
    try {
      await s9Api.distributionPaid(d.id);
      toast.success("Marcat ca plătit");
      refresh();
    } catch (e) { toast.error(errMsg(e, "Nu am putut marca plata")); }
  };

  if (error) return <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert" data-testid="finance-error">{error} <button className="ml-2 underline" onClick={load}>Reîncearcă</button></div>;
  if (!data) return <div className="space-y-2" data-testid="finance-loading">{[0, 1].map((i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-100" />)}</div>;

  const years = data.years || [];
  const mine = data.my_distributions || [];
  const all = data.distributions || [];
  const totals = data.totals || {};
  const hasDist = (y) => all.some((d) => d.year === y);

  return (
    <div className="space-y-6" data-testid="finance-tab">
      {confirmDialog}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-bold">Finanțe</h2>
        {canWrite && <DSButton onClick={() => setCreate(true)} data-testid="finance-create-year">Adaugă an financiar</DSButton>}
      </div>

      {mine.length > 0 && (
        <section data-testid="finance-mine">
          <h3 className="mb-2 font-semibold">Sumele mele</h3>
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs"><tr><th className="p-2">An</th><th className="p-2">Sumă</th><th className="p-2">Stare</th><th className="p-2">Prescriere</th></tr></thead>
              <tbody>
                {mine.map((d) => {
                  const days = d.days_to_prescription;
                  const near = !d.paid_at && days != null && days < NEAR_DAYS;
                  return (
                    <tr key={d.id} className={`border-t ${near ? "bg-red-50" : ""}`} data-testid={`finance-mine-${d.id}`}>
                      <td className="p-2">{d.year}</td>
                      <td className="p-2 font-semibold">{ron(d.amount)}</td>
                      <td className="p-2">{d.paid_at ? `Plătit ${fmt(d.paid_at)}` : "Neridicat"}</td>
                      <td className="p-2">
                        {d.paid_at ? "—" : (
                          <>
                            {fmt(d.prescribes_at)} <span className={near ? "font-bold text-red-700" : "text-slate-600"}>({days != null ? `${days} zile` : ""})</span>
                            {near && <p className="text-xs text-red-700" data-testid={`finance-warning-${d.id}`}>Atenție: art. 34(2): suma neridicată în 5 ani se prescrie în favoarea asociației. Ridic-o cât mai repede.</p>}
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {seesAll && (
        <div className="grid grid-cols-2 gap-3" data-testid="finance-totals">
          <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-600">Total neridicat</p><p className="text-lg font-bold">{ron(totals.unpaid)}</p></div>
          <div className="rounded-xl bg-red-50 p-3"><p className="text-xs text-slate-600">Aproape de prescriere (&lt; 12 luni)</p><p className="text-lg font-bold text-red-700">{ron(totals.near_prescription)}</p></div>
        </div>
      )}

      <section className="space-y-4" data-testid="finance-years">
        <h3 className="font-semibold">Ani financiari</h3>
        {years.length === 0 ? <EmptyState title="Niciun an financiar înregistrat." testid="finance-empty" /> : years.map((y) => (
          <article key={y.year} className="space-y-3 rounded-xl border border-slate-200 bg-white p-4" data-testid={`finance-year-${y.year}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="font-bold">{y.year} · profit net {ron(y.net_profit)}</h4>
              {canWrite && seesAll && !hasDist(y.year) && (
                <DSButton variant="secondary" onClick={() => { setDistFor(y.year); setAgaDate(todayStr()); }} data-testid={`finance-distribute-${y.year}`}>Distribuie membrilor</DSButton>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Breakdown title={`Venituri (${ron(sum(y.revenues))})`} obj={y.revenues} />
              <Breakdown title={`Cheltuieli (${ron(sum(y.expenses))})`} obj={y.expenses} />
            </div>
            <SplitBars year={y} />
          </article>
        ))}
      </section>

      {seesAll && all.length > 0 && (
        <section data-testid="finance-distributions">
          <h3 className="mb-2 font-semibold">Distribuiri pe membri</h3>
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs"><tr><th className="p-2">An</th><th className="p-2">Membru</th><th className="p-2">Sumă</th><th className="p-2">Stare</th><th className="p-2">Prescriere</th><th className="p-2" /></tr></thead>
              <tbody>
                {all.map((d) => {
                  const near = !d.paid_at && d.days_to_prescription != null && d.days_to_prescription < NEAR_DAYS;
                  return (
                    <tr key={d.id} className={`border-t ${near ? "bg-red-50" : ""}`} data-testid={`finance-dist-${d.id}`}>
                      <td className="p-2">{d.year}</td>
                      <td className="p-2">{d.member_name || d.member_code || d.member_id}</td>
                      <td className="p-2">{ron(d.amount)}</td>
                      <td className="p-2">{d.paid_at ? `Plătit ${fmt(d.paid_at)}` : "Neridicat"}</td>
                      <td className="p-2">{d.paid_at ? "—" : `${fmt(d.prescribes_at)} (${d.days_to_prescription ?? "?"} zile)`}</td>
                      <td className="p-2">{canPay && !d.paid_at && <DSButton variant="secondary" onClick={() => markPaid(d)} data-testid={`finance-paid-${d.id}`}>Plătit</DSButton>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <CreateYearDialog open={create} onClose={() => setCreate(false)} assocId={id} onDone={refresh} />

      <Dialog open={distFor != null} onOpenChange={(o) => !o && setDistFor(null)}>
        <DialogContent data-testid="finance-distribute-dialog">
          <DialogHeader>
            <DialogTitle>Distribuie profitul {distFor}</DialogTitle>
            <DialogDescription>Sumele se împart proporțional cu cotele. Prescrierea curge 5 ani de la data AGA (art. 34(2)).</DialogDescription>
          </DialogHeader>
          <label className="text-sm">Data AGA care a aprobat
            <input type="date" value={agaDate} onChange={(e) => setAgaDate(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 p-2" data-testid="finance-aga-date" />
          </label>
          <DialogFooter>
            <DSButton variant="secondary" onClick={() => setDistFor(null)}>Renunță</DSButton>
            <DSButton onClick={distribute} disabled={busy || !agaDate} data-testid="finance-distribute-ok">{busy ? "Se calculează…" : "Distribuie"}</DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CreateYearDialog({ open, onClose, assocId, onDone }) {
  const [year, setYear] = useState(new Date().getFullYear() - 1);
  const [rev, setRev] = useState({});
  const [exp, setExp] = useState({});
  const [split, setSplit] = useState({ council: "", reserve: "", charity: "", investment: "" });
  const [busy, setBusy] = useState(false);

  const profit = sum(rev) - sum(exp);
  const fixed = ["council", "reserve", "charity", "investment"].reduce((a, k) => a + Number(split[k] || 0), 0);
  const membersAmt = profit - fixed;
  const violations = Object.keys(MAXIMA).filter((k) => profit > 0 && Number(split[k] || 0) > profit * MAXIMA[k] + 0.005);
  const invalid = profit <= 0 || membersAmt < -0.005 || violations.length > 0;

  const num = (setter) => (k) => (e) => setter((p) => ({ ...p, [k]: e.target.value }));
  const clean = (o) => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== "" && Number(v) > 0).map(([k, v]) => [k, Number(v)]));

  const submit = async () => {
    setBusy(true);
    try {
      await s9Api.financeYearCreate(assocId, {
        year: Number(year), revenues: clean(rev), expenses: clean(exp), net_profit: Math.round(profit * 100) / 100,
        split: { ...Object.fromEntries(Object.keys(MAXIMA).map((k) => [k, Number(split[k] || 0)])), members: Math.round(membersAmt * 100) / 100 },
      });
      toast.success("Anul financiar a fost salvat");
      onClose();
      onDone();
    } catch (e) { toast.error(errMsg(e, "Nu am putut salva anul financiar")); }
    finally { setBusy(false); }
  };

  const Field = ({ label, value, onChange, tid }) => (
    <label className="flex items-center justify-between gap-2 text-sm">
      <span className="min-w-0 break-words">{label}</span>
      <input type="number" min="0" step="0.01" inputMode="decimal" value={value ?? ""} onChange={onChange} className="w-28 rounded-lg border border-slate-300 p-1.5 text-right" data-testid={tid} />
    </label>
  );

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto" data-testid="finance-year-dialog">
        <DialogHeader>
          <DialogTitle>An financiar nou</DialogTitle>
          <DialogDescription>Introdu veniturile și cheltuielile; profitul net se calculează automat.</DialogDescription>
        </DialogHeader>
        <label className="text-sm">An
          <input type="number" value={year} onChange={(e) => setYear(e.target.value)} className="ml-2 w-24 rounded-lg border border-slate-300 p-1.5" data-testid="finance-year-input" />
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2"><p className="text-xs font-bold">Venituri</p>{REV_CATS.map((c) => <Field key={c} label={c} value={rev[c]} onChange={num(setRev)(c)} tid={`finance-rev-${c}`} />)}</div>
          <div className="space-y-2"><p className="text-xs font-bold">Cheltuieli</p>{EXP_CATS.map((c) => <Field key={c} label={c} value={exp[c]} onChange={num(setExp)(c)} tid={`finance-exp-${c}`} />)}</div>
        </div>
        <p className="font-semibold" data-testid="finance-net-profit">Profit net: {ron(profit)}</p>
        <div className="space-y-2">
          <p className="text-xs font-bold">Împărțirea profitului (maxime statutare)</p>
          {Object.keys(MAXIMA).map((k) => (
            <div key={k}>
              <Field label={`${SPLIT_LABEL[k]} (${SPLIT_LIMIT[k]})`} value={split[k]} onChange={num(setSplit)(k)} tid={`finance-split-${k}`} />
              {violations.includes(k) && <p className="text-xs text-red-700">Depășește maximul de {MAXIMA[k] * 100}% din profit ({ron(profit * MAXIMA[k])}).</p>}
            </div>
          ))}
          <p className={`text-sm ${membersAmt < 0 ? "text-red-700" : ""}`}>Rest membrilor: <strong>{ron(membersAmt)}</strong></p>
        </div>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton onClick={submit} disabled={busy || invalid} data-testid="finance-year-save">{busy ? "Se salvează…" : "Salvează"}</DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
