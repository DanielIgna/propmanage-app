import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Pencil, Plus, Sprout, Trash2, AlertTriangle } from "lucide-react";
import { useConfirm } from "../ConfirmDialog";
import { CARD, DSButton, EmptyState } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Input } from "../../../../components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../../components/ui/table";
import { radaciniApi, asList, errMsg } from "../../api";
import { useMeta } from "../../hooks";
import { CROP_STATUSES, Field, PageSkeleton, SelectField, StatusBadge, fmtArea, fmtDate, isoToDateInput, optsOr } from "../../shared";

const OTHER = "__other__";

const EMPTY_FORM = {
  cropId: "",
  cropText: "",
  area_m2: "",
  sow_date: "",
  expected_harvest_date: "",
  expected_yield_kg: "",
  status: "planned",
  notes: "",
};

// Cultura se trimite ca id din meta.crops sau ca text liber (backend-ul stabilește familia).
// Din backend vine stocată: crop (eticheta), crop_id (id-ul din meta, dacă există).
const toForm = (c, cropsMeta) => {
  const match = cropsMeta.find((x) => x.id === c.crop_id || x.label === c.crop);
  return {
    cropId: match ? match.id : OTHER,
    cropText: match ? "" : c.crop || "",
    area_m2: c.area_m2 ?? "",
    sow_date: isoToDateInput(c.sow_date),
    expected_harvest_date: isoToDateInput(c.expected_harvest_date),
    expected_yield_kg: c.expected_yield_kg ?? "",
    status: c.status || "planned",
    notes: c.notes || "",
  };
};

const toBody = (f) => {
  const body = {
    crop: f.cropId === OTHER ? f.cropText.trim() : f.cropId,
    area_m2: Number(f.area_m2),
    sow_date: f.sow_date,
    status: f.status,
  };
  if (f.expected_harvest_date) body.expected_harvest_date = f.expected_harvest_date;
  if (f.expected_yield_kg !== "" && f.expected_yield_kg != null) body.expected_yield_kg = Number(f.expected_yield_kg);
  if (f.notes.trim()) body.notes = f.notes.trim();
  return body;
};

function CropDialog({ open, onOpenChange, crop, cropsMeta, statuses, projectId, onSaved }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const isEdit = !!crop;

  useEffect(() => {
    if (!open) return;
    setForm(crop ? toForm(crop, cropsMeta) : { ...EMPTY_FORM, cropId: cropsMeta[0]?.id || OTHER });
  }, [open, crop, cropsMeta]);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const cropOptions = [...cropsMeta.map((c) => ({ id: c.id, label: c.label })), { id: OTHER, label: "Altă cultură (text liber)" }];

  const valid =
    !!(form.cropId === OTHER ? form.cropText.trim() : form.cropId) &&
    Number(form.area_m2) > 0 &&
    !!form.sow_date;

  const save = async () => {
    if (!valid) return;
    setSaving(true);
    try {
      const body = toBody(form);
      if (isEdit) await radaciniApi.updateCrop(crop.id, body);
      else await radaciniApi.createCrop(projectId, body);
      toast.success(isEdit ? "Cultura a fost actualizată" : "Cultura a fost adăugată");
      onOpenChange(false);
      onSaved();
    } catch (e) {
      toast.error(errMsg(e, "Cultura nu a putut fi salvată"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="radacini-cultura-dialog" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editează cultura" : "Adaugă cultură"}</DialogTitle>
          <DialogDescription>Suprafața culturilor nu poate depăși suprafața proiectului.</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Cultură" htmlFor="crop-select">
            <SelectField
              id="crop-select"
              value={form.cropId}
              onValueChange={set("cropId")}
              options={cropOptions}
              placeholder="Alege cultura"
              testid="radacini-cultura-select"
            />
          </Field>
          {form.cropId === OTHER && (
            <Field label="Numele culturii" htmlFor="crop-text">
              <Input id="crop-text" value={form.cropText} onChange={(e) => set("cropText")(e.target.value)} maxLength={60} data-testid="radacini-cultura-text" />
            </Field>
          )}
          <Field label="Suprafață (m²)" htmlFor="crop-area">
            <Input id="crop-area" type="number" min="0" step="any" value={form.area_m2} onChange={(e) => set("area_m2")(e.target.value)} data-testid="radacini-cultura-suprafata" />
          </Field>
          <Field label="Data semănatului / plantării" htmlFor="crop-sow">
            <Input id="crop-sow" type="date" value={form.sow_date} onChange={(e) => set("sow_date")(e.target.value)} data-testid="radacini-cultura-semanat" />
          </Field>
          <Field label="Recoltare estimată" htmlFor="crop-harvest">
            <Input id="crop-harvest" type="date" value={form.expected_harvest_date} onChange={(e) => set("expected_harvest_date")(e.target.value)} />
          </Field>
          <Field label="Producție estimată (kg) — estimare, nu garanție" htmlFor="crop-yield" hint="Cifră orientativă, nu un angajament.">
            <Input id="crop-yield" type="number" min="0" step="any" value={form.expected_yield_kg} onChange={(e) => set("expected_yield_kg")(e.target.value)} />
          </Field>
          <Field label="Stare" htmlFor="crop-status">
            <SelectField id="crop-status" value={form.status} onValueChange={set("status")} options={statuses} testid="radacini-cultura-stare" />
          </Field>
          <Field label="Observații" htmlFor="crop-notes">
            <Input id="crop-notes" value={form.notes} onChange={(e) => set("notes")(e.target.value)} maxLength={300} />
          </Field>
        </div>

        <DialogFooter>
          <DSButton variant="secondary" onClick={() => onOpenChange(false)} data-testid="radacini-cultura-anuleaza">
            Renunță
          </DSButton>
          <DSButton variant="primary" disabled={!valid || saving} onClick={save} data-testid="radacini-cultura-salveaza">
            {saving ? "Se salvează…" : "Salvează"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function CropsTab({ project, canCoord, reload }) {
  const [confirm, confirmDialog] = useConfirm();
  const { meta } = useMeta();
  const cropsMeta = useMemo(() => meta?.crops || [], [meta]);
  const statuses = optsOr(meta?.crop_statuses, CROP_STATUSES);
  const [data, setData] = useState({ loaded: false, items: [], warnings: [] });
  const [tick, setTick] = useState(0);
  const [dialog, setDialog] = useState({ open: false, crop: null });

  useEffect(() => {
    let alive = true;
    radaciniApi
      .projectCrops(project.id)
      .then((d) => alive && setData({ loaded: true, items: asList(d), warnings: d?.warnings || [] }))
      .catch((e) => {
        if (!alive) return;
        toast.error(errMsg(e, "Nu am putut încărca planul de culturi"));
        setData({ loaded: true, items: [], warnings: [] });
      });
    return () => {
      alive = false;
    };
  }, [project.id, tick]);

  const refresh = () => setTick((t) => t + 1);

  const remove = async (c) => {
    if (
      !(await confirm({
        title: "Ștergi cultura?",
        description: `„${c.crop}” va fi eliminată din plan.`,
        confirmLabel: "Șterge",
        danger: true,
      }))
    )
      return;
    try {
      await radaciniApi.deleteCrop(c.id);
      toast.success("Cultura a fost ștearsă");
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Cultura nu a putut fi ștearsă"));
    }
  };

  if (!data.loaded) return <PageSkeleton />;

  const used = data.items.reduce((s, c) => s + Number(c.area_m2 || 0), 0);
  const total = Number(project.area_m2 || 0);
  const pct = total > 0 ? Math.min(100, Math.round((used / total) * 100)) : 0;
  const over = total > 0 && used > total;

  return (
    <div className="space-y-4" data-testid="radacini-plan-culturi">
      {confirmDialog}

      {data.warnings.length > 0 && (
        <div
          className="rounded-2xl border-2 border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-500/10 p-4 space-y-2"
          data-testid="radacini-plan-avertizari"
        >
          <p className="flex items-center gap-2 text-sm font-bold text-amber-800 dark:text-amber-200">
            <AlertTriangle className="w-4 h-4" /> Avertizări
          </p>
          <ul className="list-disc pl-5 space-y-1 text-sm text-amber-900 dark:text-amber-100">
            {data.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <section className={`${CARD} p-4 space-y-2`} data-testid="radacini-plan-ocupare">
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="font-semibold text-slate-700 dark:text-slate-200">Suprafață folosită</span>
          <span className={`font-bold ${over ? "text-rose-700 dark:text-rose-300" : "text-slate-900 dark:text-white"}`}>
            {fmtArea(used)} din {fmtArea(total)} ({pct}%)
          </span>
        </div>
        <div className="h-2.5 w-full rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${over ? "bg-rose-500" : "bg-emerald-500"}`}
            style={{ width: `${pct}%` }}
            data-testid="radacini-plan-bara"
          />
        </div>
      </section>

      <div className="flex justify-end">
        {canCoord && (
          <DSButton
            variant="primary"
            icon={Plus}
            onClick={() => setDialog({ open: true, crop: null })}
            data-testid="radacini-btn-adauga-cultura"
          >
            Adaugă cultură
          </DSButton>
        )}
      </div>

      {data.items.length === 0 ? (
        <EmptyState
          icon={Sprout}
          title="Nicio cultură în plan"
          hint={canCoord ? "Adaugă prima cultură ca să vezi ocuparea terenului." : "Coordonatorul nu a adăugat încă culturi."}
          testid="radacini-plan-empty"
        />
      ) : (
        <div className={`${CARD} overflow-x-auto`}>
          <Table data-testid="radacini-plan-tabel">
            <TableHeader>
              <TableRow>
                <TableHead>Cultură</TableHead>
                <TableHead>Suprafață</TableHead>
                <TableHead>Semănat</TableHead>
                <TableHead>Recoltare est.</TableHead>
                <TableHead>Producție est.</TableHead>
                <TableHead>Stare</TableHead>
                {canCoord && <TableHead className="text-right">Acțiuni</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((c) => (
                <TableRow key={c.id} data-testid={`radacini-cultura-${c.id}`}>
                  <TableCell className="font-semibold">{c.crop}</TableCell>
                  <TableCell>{fmtArea(c.area_m2)}</TableCell>
                  <TableCell>{fmtDate(c.sow_date)}</TableCell>
                  <TableCell>{fmtDate(c.expected_harvest_date)}</TableCell>
                  <TableCell>
                    {c.expected_yield_kg != null ? (
                      <span title="Estimare, nu garanție">{Number(c.expected_yield_kg).toLocaleString("ro-RO")} kg (est.)</span>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={c.status} />
                  </TableCell>
                  {canCoord && (
                    <TableCell className="text-right whitespace-nowrap">
                      <button
                        type="button"
                        aria-label="Editează cultura"
                        onClick={() => setDialog({ open: true, crop: c })}
                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5"
                        data-testid={`radacini-cultura-edit-${c.id}`}
                      >
                        <Pencil className="w-4 h-4 text-slate-600 dark:text-slate-300" />
                      </button>
                      <button
                        type="button"
                        aria-label="Șterge cultura"
                        onClick={() => remove(c)}
                        className="p-2 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-500/10"
                        data-testid={`radacini-cultura-delete-${c.id}`}
                      >
                        <Trash2 className="w-4 h-4 text-rose-600 dark:text-rose-300" />
                      </button>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <CropDialog
        open={dialog.open}
        onOpenChange={(open) => setDialog((d) => ({ ...d, open }))}
        crop={dialog.crop}
        cropsMeta={cropsMeta}
        statuses={statuses}
        projectId={project.id}
        onSaved={() => {
          refresh();
          reload?.();
        }}
      />
    </div>
  );
}
