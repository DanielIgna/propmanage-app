import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { DSButton } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Input } from "../../../../components/ui/input";
import { radaciniApi, asList, errMsg } from "../../api";
import { Field, SelectField, fmtArea, todayIso } from "../../shared";

const OTHER = "__other__";
const EMPTY = { planId: "", cropText: "", quantity_kg: "", date: "", note: "" };

// Înregistrarea unei recolte: cultură din planul proiectului sau text liber.
export default function RecordHarvestDialog({ open, onOpenChange, projectId, onSaved }) {
  const [form, setForm] = useState(EMPTY);
  const [plans, setPlans] = useState({ loaded: false, items: [] });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return undefined;
    setForm({ ...EMPTY, date: todayIso() });
    setPlans({ loaded: false, items: [] });
    let alive = true;
    radaciniApi
      .projectCrops(projectId)
      .then((d) => alive && setPlans({ loaded: true, items: asList(d) }))
      .catch(() => alive && setPlans({ loaded: true, items: [] }));
    return () => {
      alive = false;
    };
  }, [open, projectId]);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const planOptions = [
    ...plans.items.map((p) => ({ id: p.id, label: `${p.crop} · ${fmtArea(p.area_m2)}` })),
    { id: OTHER, label: "Altă cultură (text liber)" },
  ];
  const kg = Number(form.quantity_kg);
  const cropOk = form.planId === OTHER ? !!form.cropText.trim() : !!form.planId;
  const valid = cropOk && kg > 0 && kg <= 1000000 && !!form.date && form.date <= todayIso();

  const save = async () => {
    if (!valid) return;
    setSaving(true);
    try {
      const body = { quantity_kg: kg, date: form.date };
      if (form.planId === OTHER) body.crop = form.cropText.trim();
      else body.crop_plan_id = form.planId;
      if (form.note.trim()) body.note = form.note.trim();
      await radaciniApi.createHarvest(projectId, body);
      toast.success("Recolta a fost înregistrată");
      onOpenChange(false);
      onSaved();
    } catch (e) {
      toast.error(errMsg(e, "Recolta nu a putut fi înregistrată"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="radacini-recolta-dialog" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Înregistrează recolta</DialogTitle>
          <DialogDescription>Recolta se confirmă de proprietar. Alocarea pe membri se face după confirmare.</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Cultură" htmlFor="harvest-plan">
            <SelectField
              id="harvest-plan"
              value={form.planId}
              onValueChange={set("planId")}
              options={planOptions}
              placeholder={plans.loaded ? "Alege cultura" : "Se încarcă…"}
              testid="radacini-recolta-plan"
            />
          </Field>
          {form.planId === OTHER && (
            <Field label="Numele culturii" htmlFor="harvest-crop-text">
              <Input id="harvest-crop-text" value={form.cropText} maxLength={60} onChange={(e) => set("cropText")(e.target.value)} data-testid="radacini-recolta-cultura-text" />
            </Field>
          )}
          <Field label="Cantitate (kg)" htmlFor="harvest-kg">
            <Input id="harvest-kg" type="number" min="0" step="any" value={form.quantity_kg} onChange={(e) => set("quantity_kg")(e.target.value)} data-testid="radacini-recolta-kg" />
          </Field>
          <Field label="Data recoltei" htmlFor="harvest-date">
            <Input id="harvest-date" type="date" max={todayIso()} value={form.date} onChange={(e) => set("date")(e.target.value)} data-testid="radacini-recolta-data" />
          </Field>
          <div className="sm:col-span-2">
            <Field label="Observații" htmlFor="harvest-note">
              <Input id="harvest-note" value={form.note} maxLength={300} onChange={(e) => set("note")(e.target.value)} data-testid="radacini-recolta-nota" />
            </Field>
          </div>
        </div>

        <DialogFooter>
          <DSButton variant="secondary" onClick={() => onOpenChange(false)} data-testid="radacini-recolta-anuleaza">
            Renunță
          </DSButton>
          <DSButton variant="primary" disabled={!valid || saving} onClick={save} data-testid="radacini-recolta-salveaza">
            {saving ? "Se salvează…" : "Înregistrează"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
