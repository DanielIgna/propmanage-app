import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { PackageOpen, Plus } from "lucide-react";
import { useConfirm } from "../ConfirmDialog";
import { CARD, DSButton, EmptyState } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Input } from "../../../../components/ui/input";
import { asList, errMsg } from "../../api";
import { s7Api } from "../../api_s7";
import { Field, PageHeader, PageSkeleton, SelectField } from "../../shared";

export const NEED_KINDS = [
  { id: "seeds", label: "Semințe", cls: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200" },
  { id: "tools", label: "Unelte", cls: "bg-sky-100 text-sky-800 dark:bg-sky-500/15 dark:text-sky-200" },
  { id: "materials", label: "Materiale", cls: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200" },
  { id: "service", label: "Serviciu", cls: "bg-violet-100 text-violet-800 dark:bg-violet-500/15 dark:text-violet-200" },
];
const kindDef = (k) => NEED_KINDS.find((x) => x.id === k) || { label: k, cls: "bg-slate-100 text-slate-600" };
const num = (v) => Number(v || 0).toLocaleString("ro-RO", { maximumFractionDigits: 2 });

function AddNeedDialog({ open, onOpenChange, projectId, onSaved }) {
  const [form, setForm] = useState({ kind: "", item: "", quantity: "", unit: "" });
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (open) setForm({ kind: "", item: "", quantity: "", unit: "" });
  }, [open]);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const q = Number(form.quantity);
  const valid = !!form.kind && form.item.trim().length >= 2 && q > 0 && !!form.unit.trim();

  const save = async () => {
    if (!valid) return;
    setSaving(true);
    try {
      await s7Api.createNeed(projectId, { kind: form.kind, item: form.item.trim(), quantity: q, unit: form.unit.trim() });
      toast.success("Necesarul a fost adăugat");
      onOpenChange(false);
      onSaved();
    } catch (e) {
      toast.error(errMsg(e, "Necesarul nu a putut fi adăugat"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="radacini-necesar-dialog" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Adaugă necesar</DialogTitle>
          <DialogDescription>Membrii pot promite cantități din ce ai nevoie.</DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Tip" htmlFor="need-kind">
            <SelectField id="need-kind" value={form.kind} onValueChange={set("kind")} options={NEED_KINDS} placeholder="Alege tipul" testid="radacini-necesar-tip" />
          </Field>
          <Field label="Denumire" htmlFor="need-item">
            <Input id="need-item" value={form.item} maxLength={80} onChange={(e) => set("item")(e.target.value)} data-testid="radacini-necesar-denumire" />
          </Field>
          <Field label="Cantitate" htmlFor="need-qty">
            <Input id="need-qty" type="number" min="0" step="any" value={form.quantity} onChange={(e) => set("quantity")(e.target.value)} data-testid="radacini-necesar-cantitate" />
          </Field>
          <Field label="Unitate" htmlFor="need-unit" hint="Ex.: kg, buc, saci">
            <Input id="need-unit" value={form.unit} maxLength={20} onChange={(e) => set("unit")(e.target.value)} data-testid="radacini-necesar-unitate" />
          </Field>
        </div>
        <DialogFooter>
          <DSButton variant="secondary" onClick={() => onOpenChange(false)}>Renunță</DSButton>
          <DSButton variant="primary" disabled={!valid || saving} onClick={save} data-testid="radacini-necesar-salveaza">
            {saving ? "Se salvează…" : "Adaugă"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PledgeDialog({ need, onClose, onSaved }) {
  const [qty, setQty] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => setQty(""), [need?.id]);
  const left = need ? Math.max(0, Number(need.quantity) - (need.pledges || []).reduce((s, p) => s + Number(p.quantity || 0), 0)) : 0;
  const q = Number(qty);
  const valid = q > 0 && q <= left;

  const save = async () => {
    if (!valid) return;
    setSaving(true);
    try {
      await s7Api.pledge(need.id, q);
      toast.success("Promisiunea a fost înregistrată");
      onClose();
      onSaved();
    } catch (e) {
      toast.error(errMsg(e, "Promisiunea nu a putut fi înregistrată"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={!!need} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-promisiune-dialog">
        <DialogHeader>
          <DialogTitle>Promite {need?.item}</DialogTitle>
          <DialogDescription>Mai poți promite cel mult {num(left)} {need?.unit}.</DialogDescription>
        </DialogHeader>
        <Field label={`Cantitate (${need?.unit || ""})`} htmlFor="pledge-qty">
          <Input id="pledge-qty" type="number" min="0" step="any" max={left} value={qty} onChange={(e) => setQty(e.target.value)} data-testid="radacini-promisiune-cantitate" />
        </Field>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton variant="primary" disabled={!valid || saving} onClick={save} data-testid="radacini-promisiune-trimite">
            {saving ? "Se trimite…" : "Promit"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// isMember = poate scrie (membru, proiect activ) · canCoord = coordonator cu drept de scriere.
export default function NeedsTab({ project, isMember, canCoord, me }) {
  const [confirm, confirmDialog] = useConfirm();
  const [data, setData] = useState({ loaded: false, items: [] });
  const [tick, setTick] = useState(0);
  const [addOpen, setAddOpen] = useState(false);
  const [pledgeFor, setPledgeFor] = useState(null);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    let alive = true;
    s7Api
      .needs(project.id)
      .then((d) => alive && setData({ loaded: true, items: asList(d) }))
      .catch((e) => {
        if (!alive) return;
        toast.error(errMsg(e, "Nu am putut încărca necesarul"));
        setData({ loaded: true, items: [] });
      });
    return () => {
      alive = false;
    };
  }, [project.id, tick]);

  const refresh = () => setTick((t) => t + 1);

  const fulfilled = async (need, i) => {
    setBusy(`${need.id}:${i}`);
    try {
      await s7Api.pledgeFulfilled(need.id, i);
      toast.success("Marcat ca adus");
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut marca ca adus"));
    } finally {
      setBusy(null);
    }
  };

  const cancel = async (need) => {
    if (!(await confirm({ title: "Anulezi necesarul?", description: `${need.item} nu va mai fi cerut de la membri.`, confirmLabel: "Anulează necesarul", danger: true }))) return;
    setBusy(need.id);
    try {
      await s7Api.cancelNeed(need.id);
      toast.success("Necesarul a fost anulat");
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Necesarul nu a putut fi anulat"));
    } finally {
      setBusy(null);
    }
  };

  if (!data.loaded) return <PageSkeleton />;

  return (
    <div className="space-y-5" data-testid="radacini-necesar">
      <PageHeader
        title="Necesar"
        subtitle="Semințe, unelte și materiale de care are nevoie proiectul. Membrii promit cantități și apoi le aduc."
        actions={
          canCoord && (
            <DSButton variant="primary" icon={Plus} onClick={() => setAddOpen(true)} data-testid="radacini-necesar-btn-adauga">
              Adaugă necesar
            </DSButton>
          )
        }
      />

      {data.items.length === 0 ? (
        <EmptyState icon={PackageOpen} title="Niciun necesar înregistrat" hint="Coordonatorul poate adăuga ce are nevoie proiectul." testid="radacini-necesar-empty" />
      ) : (
        <ul className="space-y-3" data-testid="radacini-necesar-lista">
          {data.items.map((n) => {
            const pledges = n.pledges || [];
            const total = Number(n.quantity || 0);
            const pledged = pledges.reduce((s, p) => s + Number(p.quantity || 0), 0);
            const done = pledges.filter((p) => p.fulfilled).reduce((s, p) => s + Number(p.quantity || 0), 0);
            const pPct = total > 0 ? Math.min(100, Math.round((pledged / total) * 100)) : 0;
            const fPct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
            const k = kindDef(n.kind);
            const active = n.status === "needed";
            const canPledge = isMember && active && pledged < total;
            return (
              <li key={n.id} className={`${CARD} p-4 space-y-3`} data-testid={`radacini-necesar-${n.id}`}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0 space-y-1">
                    <p className="font-bold text-slate-900 dark:text-white break-words">{n.item}</p>
                    <div className="flex flex-wrap gap-1.5">
                      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-bold ${k.cls}`} data-testid={`radacini-necesar-tip-${n.id}`}>{k.label}</span>
                      {n.status === "covered" && <span className="inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200">Acoperit</span>}
                      {n.status === "cancelled" && <span className="inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-bold bg-slate-200 text-slate-700 dark:bg-white/15 dark:text-slate-200">Anulat</span>}
                    </div>
                  </div>
                  <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{num(total)} {n.unit}</p>
                </div>

                <div className="space-y-1.5">
                  <div className="flex flex-wrap justify-between gap-2 text-xs font-semibold text-slate-600 dark:text-slate-300">
                    <span data-testid={`radacini-necesar-promis-${n.id}`}>Promis: {num(pledged)} din {num(total)} {n.unit}</span>
                    <span data-testid={`radacini-necesar-adus-${n.id}`}>Adus: {num(done)} {n.unit}</span>
                  </div>
                  <div className="relative h-2 w-full rounded-full bg-slate-200 dark:bg-white/10 overflow-hidden">
                    <div className="absolute inset-y-0 left-0 bg-emerald-300 dark:bg-emerald-700 transition-all" style={{ width: `${pPct}%` }} />
                    <div className="absolute inset-y-0 left-0 bg-emerald-500 transition-all" style={{ width: `${fPct}%` }} />
                  </div>
                </div>

                {pledges.length > 0 && (
                  <ul className="divide-y divide-slate-200 dark:divide-white/10">
                    {pledges.map((p, i) => {
                      const mine = !!me && p.user_id === me;
                      return (
                        <li key={i} className="py-2 flex flex-wrap items-center justify-between gap-2 text-sm" data-testid={`radacini-promisiune-${n.id}-${i}`}>
                          <span className="text-slate-700 dark:text-slate-200">
                            {p.name} · {num(p.quantity)} {n.unit}
                            {p.fulfilled && <span className="ml-2 text-xs font-bold text-emerald-700 dark:text-emerald-300">adus</span>}
                          </span>
                          {mine && isMember && !p.fulfilled && n.status !== "cancelled" && (
                            <DSButton variant="success" disabled={busy === `${n.id}:${i}`} onClick={() => fulfilled(n, i)} data-testid={`radacini-promisiune-adus-${n.id}-${i}`}>
                              Am adus
                            </DSButton>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}

                {(canPledge || (canCoord && active)) && (
                  <div className="flex flex-wrap gap-2">
                    {canPledge && (
                      <DSButton variant="secondary" onClick={() => setPledgeFor(n)} data-testid={`radacini-necesar-promite-${n.id}`}>
                        Promit
                      </DSButton>
                    )}
                    {canCoord && active && (
                      <DSButton variant="danger" disabled={busy === n.id} onClick={() => cancel(n)} data-testid={`radacini-necesar-anuleaza-${n.id}`}>
                        Anulează
                      </DSButton>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <AddNeedDialog open={addOpen} onOpenChange={setAddOpen} projectId={project.id} onSaved={refresh} />
      <PledgeDialog need={pledgeFor} onClose={() => setPledgeFor(null)} onSaved={refresh} />
      {confirmDialog}
    </div>
  );
}
