import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Tractor } from "lucide-react";
import { useConfirm } from "../ConfirmDialog";
import { CARD, DSButton, EmptyState } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";
import { asList, errMsg } from "../../api";
import { s7Api } from "../../api_s7";
import { Field, PageHeader, PageSkeleton, SelectField, fmtArea, fmtPeriod, todayIso } from "../../shared";

export const REQUEST_STATUS = {
  open: { label: "Deschisă", cls: "bg-sky-100 text-sky-800 dark:bg-sky-500/15 dark:text-sky-200" },
  assigned: { label: "Atribuită", cls: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200" },
  done: { label: "Finalizată", cls: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200" },
  cancelled: { label: "Anulată", cls: "bg-slate-200 text-slate-700 dark:bg-white/15 dark:text-slate-200" },
};
export const PRICE_NOTE = "Plata se face direct; prețul e orientativ.";

export function useServiceTypes() {
  const [types, setTypes] = useState([]);
  useEffect(() => {
    let alive = true;
    s7Api
      .serviceTypes()
      .then((d) => alive && setTypes(asList(d)))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);
  return types;
}
export const typeLabel = (types, id) => types.find((t) => t.id === id)?.label ?? id;

function NewRequestDialog({ open, onOpenChange, project, types, onSaved }) {
  const empty = { service_type: "", window_from: "", window_to: "", area_m2: "", description: "" };
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (open) setForm({ ...empty, area_m2: project.area_m2 ? String(project.area_m2) : "" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const area = Number(form.area_m2);
  const valid = !!form.service_type && !!form.window_from && !!form.window_to && form.window_to >= form.window_from && area > 0 && form.description.trim().length >= 5;

  const save = async () => {
    if (!valid) return;
    setSaving(true);
    try {
      await s7Api.createServiceRequest(project.id, {
        service_type: form.service_type,
        window_from: form.window_from,
        window_to: form.window_to,
        area_m2: area,
        description: form.description.trim(),
        locality: project.locality,
      });
      toast.success("Cererea a fost trimisă prestatorilor");
      onOpenChange(false);
      onSaved();
    } catch (e) {
      toast.error(errMsg(e, "Cererea nu a putut fi creată"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="radacini-lucrare-dialog" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Cerere de lucrare</DialogTitle>
          <DialogDescription>Prestatorii potriviți din {project.locality || "zonă"} vor fi notificați și îți pot trimite oferte. {PRICE_NOTE}</DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Serviciu" htmlFor="sr-type">
            <SelectField id="sr-type" value={form.service_type} onValueChange={set("service_type")} options={types} placeholder="Alege serviciul" testid="radacini-lucrare-tip" />
          </Field>
          <Field label="Suprafață (m²)" htmlFor="sr-area">
            <Input id="sr-area" type="number" min="0" step="any" value={form.area_m2} onChange={(e) => set("area_m2")(e.target.value)} data-testid="radacini-lucrare-suprafata" />
          </Field>
          <Field label="De la" htmlFor="sr-from">
            <Input id="sr-from" type="date" min={todayIso()} value={form.window_from} onChange={(e) => set("window_from")(e.target.value)} data-testid="radacini-lucrare-de-la" />
          </Field>
          <Field label="Până la" htmlFor="sr-to">
            <Input id="sr-to" type="date" min={form.window_from || todayIso()} value={form.window_to} onChange={(e) => set("window_to")(e.target.value)} data-testid="radacini-lucrare-pana-la" />
          </Field>
          <div className="sm:col-span-2">
            <Field label="Descriere" htmlFor="sr-desc">
              <Textarea id="sr-desc" rows={3} maxLength={1000} value={form.description} onChange={(e) => set("description")(e.target.value)} data-testid="radacini-lucrare-descriere" />
            </Field>
          </div>
        </div>
        <DialogFooter>
          <DSButton variant="secondary" onClick={() => onOpenChange(false)}>Renunță</DSButton>
          <DSButton variant="primary" disabled={!valid || saving} onClick={save} data-testid="radacini-lucrare-salveaza">
            {saving ? "Se trimite…" : "Trimite cererea"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RatingDialog({ request, onClose, onSaved }) {
  const [rating, setRating] = useState(0);
  const [saving, setSaving] = useState(false);
  useEffect(() => setRating(0), [request?.id]);
  const save = async () => {
    if (!rating) return;
    setSaving(true);
    try {
      await s7Api.done(request.id, rating);
      toast.success("Lucrarea a fost marcată ca finalizată");
      onClose();
      onSaved();
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut finaliza lucrarea"));
    } finally {
      setSaving(false);
    }
  };
  return (
    <Dialog open={!!request} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-evaluare-dialog">
        <DialogHeader>
          <DialogTitle>Lucrare finalizată</DialogTitle>
          <DialogDescription>Evaluează prestatorul de la 1 la 5 stele.</DialogDescription>
        </DialogHeader>
        <div className="flex gap-1" role="radiogroup" aria-label="Evaluare">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={rating === n}
              aria-label={`${n} stele`}
              onClick={() => setRating(n)}
              className={`text-3xl leading-none px-1 ${n <= rating ? "text-amber-500" : "text-slate-300 dark:text-slate-600"}`}
              data-testid={`radacini-evaluare-stea-${n}`}
            >
              ★
            </button>
          ))}
        </div>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton variant="success" disabled={!rating || saving} onClick={save} data-testid="radacini-evaluare-trimite">
            {saving ? "Se salvează…" : "Finalizează"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// canCoord = coordonator cu drept de scriere. Ceilalți membri doar văd cererile.
export default function ServiceTab({ project, canCoord }) {
  const [confirm, confirmDialog] = useConfirm();
  const types = useServiceTypes();
  const [data, setData] = useState({ loaded: false, items: [] });
  const [tick, setTick] = useState(0);
  const [newOpen, setNewOpen] = useState(false);
  const [rateFor, setRateFor] = useState(null);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    let alive = true;
    s7Api
      .serviceRequests(project.id)
      .then((d) => alive && setData({ loaded: true, items: asList(d) }))
      .catch((e) => {
        if (!alive) return;
        toast.error(errMsg(e, "Nu am putut încărca lucrările"));
        setData({ loaded: true, items: [] });
      });
    return () => {
      alive = false;
    };
  }, [project.id, tick]);

  const refresh = () => setTick((t) => t + 1);

  const assign = async (r, o) => {
    if (!(await confirm({ title: "Alegi această ofertă?", description: `${o.name} va fi prestatorul pentru această lucrare.`, confirmLabel: "Alege" }))) return;
    setBusy(r.id);
    try {
      await s7Api.assign(r.id, o.provider_user_id);
      toast.success("Prestatorul a fost ales");
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Prestatorul nu a putut fi ales"));
    } finally {
      setBusy(null);
    }
  };

  const cancel = async (r) => {
    if (!(await confirm({ title: "Anulezi cererea?", description: "Prestatorii nu vor mai putea trimite oferte.", confirmLabel: "Anulează cererea", danger: true }))) return;
    setBusy(r.id);
    try {
      await s7Api.cancelRequest(r.id);
      toast.success("Cererea a fost anulată");
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Cererea nu a putut fi anulată"));
    } finally {
      setBusy(null);
    }
  };

  if (!data.loaded) return <PageSkeleton />;

  return (
    <div className="space-y-5" data-testid="radacini-lucrari">
      <PageHeader
        title="Lucrări"
        subtitle={`Lucrări mecanizate făcute de prestatori. ${PRICE_NOTE}`}
        actions={
          canCoord && (
            <DSButton variant="primary" icon={Plus} onClick={() => setNewOpen(true)} data-testid="radacini-lucrari-btn-cere">
              Cere o lucrare
            </DSButton>
          )
        }
      />

      {data.items.length === 0 ? (
        <EmptyState icon={Tractor} title="Nicio cerere de lucrare" hint="Coordonatorul poate cere arat, semănat, irigații și alte lucrări." testid="radacini-lucrari-empty" />
      ) : (
        <ul className="space-y-3" data-testid="radacini-lucrari-lista">
          {data.items.map((r) => {
            const st = REQUEST_STATUS[r.status] || { label: r.status, cls: "bg-slate-100 text-slate-600" };
            const offers = r.offers || [];
            return (
              <li key={r.id} className={`${CARD} p-4 space-y-3`} data-testid={`radacini-lucrare-${r.id}`}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-bold text-slate-900 dark:text-white">{typeLabel(types, r.service_type)}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      {fmtPeriod(r.window_from, r.window_to)}
                      {r.area_m2 ? ` · ${fmtArea(r.area_m2)}` : ""}
                      {r.locality ? ` · ${r.locality}` : ""}
                    </p>
                  </div>
                  <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-bold whitespace-nowrap ${st.cls}`} data-testid={`radacini-lucrare-status-${r.id}`}>{st.label}</span>
                </div>
                {r.description && <p className="text-sm text-slate-600 dark:text-slate-300 break-words">{r.description}</p>}

                <div className="space-y-1">
                  <p className="text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Oferte ({offers.length})</p>
                  {offers.length === 0 ? (
                    <p className="text-sm text-slate-500 dark:text-slate-400">Nicio ofertă încă.</p>
                  ) : (
                    <ul className="divide-y divide-slate-200 dark:divide-white/10" data-testid={`radacini-lucrare-oferte-${r.id}`}>
                      {offers.map((o) => {
                        const chosen = r.assigned_provider_user_id === o.provider_user_id;
                        return (
                          <li key={o.provider_user_id} className="py-2 flex flex-wrap items-start justify-between gap-2" data-testid={`radacini-oferta-${r.id}-${o.provider_user_id}`}>
                            <div className="min-w-0 text-sm">
                              <p className="font-semibold text-slate-900 dark:text-white">
                                {o.name}
                                {o.price_ron_indicative != null && <span className="ml-2 font-normal text-slate-600 dark:text-slate-300">~{Number(o.price_ron_indicative).toLocaleString("ro-RO")} RON (orientativ)</span>}
                                {chosen && <span className="ml-2 text-xs font-bold text-emerald-700 dark:text-emerald-300">ales</span>}
                              </p>
                              {o.message && <p className="text-slate-600 dark:text-slate-300 break-words">{o.message}</p>}
                            </div>
                            {canCoord && r.status === "open" && (
                              <DSButton variant="secondary" disabled={busy === r.id} onClick={() => assign(r, o)} data-testid={`radacini-oferta-alege-${r.id}-${o.provider_user_id}`}>
                                Alege
                              </DSButton>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>

                {r.status === "done" && r.rating != null && (
                  <p className="text-sm text-slate-600 dark:text-slate-300">Evaluare: <span className="text-amber-500">{"★".repeat(Number(r.rating))}</span></p>
                )}

                {canCoord && (r.status === "open" || r.status === "assigned") && (
                  <div className="flex flex-wrap gap-2">
                    {r.status === "assigned" && (
                      <DSButton variant="success" disabled={busy === r.id} onClick={() => setRateFor(r)} data-testid={`radacini-lucrare-finalizata-${r.id}`}>
                        Marchează finalizată
                      </DSButton>
                    )}
                    <DSButton variant="danger" disabled={busy === r.id} onClick={() => cancel(r)} data-testid={`radacini-lucrare-anuleaza-${r.id}`}>
                      Anulează
                    </DSButton>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <NewRequestDialog open={newOpen} onOpenChange={setNewOpen} project={project} types={types} onSaved={refresh} />
      <RatingDialog request={rateFor} onClose={() => setRateFor(null)} onSaved={refresh} />
      {confirmDialog}
    </div>
  );
}
