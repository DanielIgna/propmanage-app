import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { CalendarDays, CheckCheck, Pencil, Plus, Ban } from "lucide-react";
import { useConfirm } from "../ConfirmDialog";
import { CARD, DSButton, EmptyState } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";
import { radaciniApi, asList, errMsg } from "../../api";
import { useMeta } from "../../hooks";
import { ACTIVITY_TYPES, Field, PageSkeleton, SelectField, StatusBadge, fmtDate, labelOf, optsOr, todayIso } from "../../shared";

const NONE = "__none__";

// Săptămâna ISO a unei date "YYYY-MM-DD" (calcul în UTC, fără deplasări de fus orar).
export function isoWeekOf(iso) {
  const [y, m, d] = String(iso).slice(0, 10).split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  const dow = dt.getUTCDay() || 7; // luni = 1 … duminică = 7
  const monday = new Date(dt);
  monday.setUTCDate(dt.getUTCDate() - dow + 1);
  const thursday = new Date(monday);
  thursday.setUTCDate(monday.getUTCDate() + 3);
  const yearStart = new Date(Date.UTC(thursday.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((thursday - yearStart) / 86400000 + 1) / 7);
  return { key: monday.toISOString().slice(0, 10), week, year: thursday.getUTCFullYear(), monday };
}

const shortDay = (d) => d.toLocaleDateString("ro-RO", { day: "numeric", month: "short", timeZone: "UTC" });

function ActivityDialog({ open, onOpenChange, activity, crops, types, projectId, onSaved }) {
  const blank = { type: "work_day", title: "", date: todayIso(), start_time: "", duration_h: "", slots: "", crop_plan_id: NONE, notes: "" };
  const [form, setForm] = useState(blank);
  const [saving, setSaving] = useState(false);
  const isEdit = !!activity;

  useEffect(() => {
    if (!open) return;
    setForm(
      activity
        ? {
            type: activity.type,
            title: activity.title || "",
            date: String(activity.date || "").slice(0, 10),
            start_time: activity.start_time || "",
            duration_h: activity.duration_h ?? "",
            slots: activity.slots ?? "",
            crop_plan_id: activity.crop_plan_id || NONE,
            notes: activity.notes || "",
          }
        : { ...blank, date: todayIso() }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, activity]);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const valid = form.title.trim().length >= 3 && !!form.date;

  const save = async () => {
    if (!valid) return;
    const body = { type: form.type, title: form.title.trim(), date: form.date };
    if (form.start_time) body.start_time = form.start_time;
    if (form.duration_h !== "") body.duration_h = Number(form.duration_h);
    if (form.slots !== "") body.slots = Number(form.slots);
    if (form.crop_plan_id !== NONE) body.crop_plan_id = form.crop_plan_id;
    if (form.notes.trim()) body.notes = form.notes.trim();
    setSaving(true);
    try {
      if (isEdit) await radaciniApi.updateActivity(activity.id, body);
      else await radaciniApi.createActivity(projectId, body);
      toast.success(isEdit ? "Activitatea a fost actualizată" : "Activitatea a fost adăugată");
      onOpenChange(false);
      onSaved();
    } catch (e) {
      toast.error(errMsg(e, "Activitatea nu a putut fi salvată"));
    } finally {
      setSaving(false);
    }
  };

  const cropOptions = [{ id: NONE, label: "Fără cultură" }, ...crops.map((c) => ({ id: c.id, label: c.label || c.crop }))];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="radacini-activitate-dialog" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editează activitatea" : "Adaugă activitate"}</DialogTitle>
          <DialogDescription>Activitățile programate pot fi modificate până la marcarea ca făcute.</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Tip" htmlFor="act-type">
            <SelectField id="act-type" value={form.type} onValueChange={set("type")} options={types} testid="radacini-activitate-tip" />
          </Field>
          <Field label="Titlu" htmlFor="act-title">
            <Input id="act-title" value={form.title} onChange={(e) => set("title")(e.target.value)} maxLength={120} data-testid="radacini-activitate-titlu" />
          </Field>
          <Field label="Data" htmlFor="act-date">
            <Input id="act-date" type="date" value={form.date} onChange={(e) => set("date")(e.target.value)} data-testid="radacini-activitate-data" />
          </Field>
          <Field label="Ora de început" htmlFor="act-time">
            <Input id="act-time" type="time" value={form.start_time} onChange={(e) => set("start_time")(e.target.value)} />
          </Field>
          <Field label="Durată (ore)" htmlFor="act-duration">
            <Input id="act-duration" type="number" min="0" step="0.5" value={form.duration_h} onChange={(e) => set("duration_h")(e.target.value)} />
          </Field>
          <Field label="Locuri disponibile" htmlFor="act-slots" hint="Lasă gol dacă nu există limită.">
            <Input id="act-slots" type="number" min="1" step="1" value={form.slots} onChange={(e) => set("slots")(e.target.value)} />
          </Field>
          <Field label="Cultura vizată" htmlFor="act-crop">
            <SelectField id="act-crop" value={form.crop_plan_id} onValueChange={set("crop_plan_id")} options={cropOptions} testid="radacini-activitate-cultura" />
          </Field>
          <div className="sm:col-span-2">
            <Field label="Notițe" htmlFor="act-notes">
              <Textarea id="act-notes" value={form.notes} onChange={(e) => set("notes")(e.target.value)} maxLength={500} rows={3} />
            </Field>
          </div>
        </div>

        <DialogFooter>
          <DSButton variant="secondary" onClick={() => onOpenChange(false)} data-testid="radacini-activitate-anuleaza">
            Renunță
          </DSButton>
          <DSButton variant="primary" disabled={!valid || saving} onClick={save} data-testid="radacini-activitate-salveaza">
            {saving ? "Se salvează…" : "Salvează"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ActivityRow({ a, types, isMember, canCoord, onJoin, onLeave, onDone, onCancel, onEdit, busy }) {
  const names = a.participant_names || [];
  const joined = !!a.joined;
  const full = a.slots_left != null && a.slots_left <= 0 && !joined;
  const scheduled = a.status === "scheduled";
  const btn = "p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5";

  return (
    <li
      className={`py-3 flex flex-col sm:flex-row sm:items-center gap-3 ${a.status === "cancelled" ? "opacity-60" : ""}`}
      data-testid={`radacini-activitate-${a.id}`}
    >
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-slate-900 dark:text-white break-words">{a.title}</span>
          <span className="rounded-md bg-slate-100 dark:bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:text-slate-300">
            {labelOf(types, a.type)}
          </span>
          <StatusBadge status={a.status} testid={`radacini-activitate-status-${a.id}`} />
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {fmtDate(a.date)}
          {a.start_time ? ` · ${a.start_time}` : ""}
          {a.duration_h ? ` · ${a.duration_h} h` : ""}
          {a.slots_left != null ? ` · ${a.slots_left} locuri libere` : ` · ${names.length} participanți`}
        </p>
        {names.length > 0 && <p className="text-xs text-slate-600 dark:text-slate-300">{names.join(", ")}</p>}
      </div>

      <div className="flex flex-wrap items-center gap-1.5 sm:justify-end">
        {isMember && scheduled && (
          <DSButton
            variant={joined ? "secondary" : "primary"}
            disabled={busy || full}
            onClick={() => (joined ? onLeave(a) : onJoin(a))}
            data-testid={`radacini-activitate-particip-${a.id}`}
          >
            {joined ? "Nu mai particip" : full ? "Complet" : "Particip"}
          </DSButton>
        )}
        {canCoord && scheduled && (
          <>
            <button type="button" aria-label="Editează activitatea" className={btn} onClick={() => onEdit(a)} data-testid={`radacini-activitate-edit-${a.id}`}>
              <Pencil className="w-4 h-4 text-slate-600 dark:text-slate-300" />
            </button>
            <DSButton variant="secondary" icon={CheckCheck} disabled={busy} onClick={() => onDone(a)} data-testid={`radacini-activitate-done-${a.id}`}>
              Marchează făcut
            </DSButton>
            <DSButton variant="danger" icon={Ban} disabled={busy} onClick={() => onCancel(a)} data-testid={`radacini-activitate-cancel-${a.id}`}>
              Anulează
            </DSButton>
          </>
        )}
      </div>
    </li>
  );
}

export default function CalendarTab({ project, isMember, canCoord, reload }) {
  const [confirm, confirmDialog] = useConfirm();
  const { meta } = useMeta();
  const types = optsOr(meta?.activity_types, ACTIVITY_TYPES);
  const [data, setData] = useState({ loaded: false, items: [] });
  const [crops, setCrops] = useState([]);
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const [dialog, setDialog] = useState({ open: false, activity: null });

  useEffect(() => {
    let alive = true;
    radaciniApi
      .projectActivities(project.id)
      .then((d) => alive && setData({ loaded: true, items: asList(d) }))
      .catch((e) => {
        if (!alive) return;
        toast.error(errMsg(e, "Nu am putut încărca calendarul"));
        setData({ loaded: true, items: [] });
      });
    return () => {
      alive = false;
    };
  }, [project.id, tick]);

  useEffect(() => {
    if (!canCoord) return;
    let alive = true;
    radaciniApi
      .projectCrops(project.id)
      .then((d) => alive && setCrops(asList(d)))
      .catch(() => alive && setCrops([]));
    return () => {
      alive = false;
    };
  }, [project.id, canCoord]);

  const refresh = () => setTick((t) => t + 1);

  // Grupare pe săptămâni ISO, în ordinea datelor.
  const weeks = useMemo(() => {
    const sorted = [...data.items].sort((a, b) => `${a.date}${a.start_time || ""}`.localeCompare(`${b.date}${b.start_time || ""}`));
    const map = new Map();
    for (const a of sorted) {
      const w = isoWeekOf(a.date);
      if (!map.has(w.key)) map.set(w.key, { ...w, items: [] });
      map.get(w.key).items.push(a);
    }
    return [...map.values()];
  }, [data.items]);

  const act = async (fn, okMsg, errFallback) => {
    setBusy(true);
    try {
      await fn();
      toast.success(okMsg);
      refresh();
    } catch (e) {
      toast.error(errMsg(e, errFallback));
    } finally {
      setBusy(false);
    }
  };

  const join = (a) => act(() => radaciniApi.joinActivity(a.id), "Ai fost înscris la activitate", "Nu te-ai putut înscrie");
  const leave = (a) => act(() => radaciniApi.leaveActivity(a.id), "Te-ai retras din activitate", "Nu te-ai putut retrage");

  const done = async (a) => {
    if (!(await confirm({ title: "Marchezi activitatea ca făcută?", description: `„${a.title}” nu mai poate fi modificată după aceasta.`, confirmLabel: "Marchează făcut" })))
      return;
    act(() => radaciniApi.doneActivity(a.id), "Activitatea a fost marcată ca făcută", "Nu am putut marca activitatea");
  };

  const cancel = async (a) => {
    if (!(await confirm({ title: "Anulezi activitatea?", description: `„${a.title}” va apărea ca anulată.`, confirmLabel: "Anulează activitatea", danger: true })))
      return;
    act(() => radaciniApi.cancelActivity(a.id), "Activitatea a fost anulată", "Nu am putut anula activitatea");
  };

  if (!data.loaded) return <PageSkeleton />;

  return (
    <div className="space-y-4" data-testid="radacini-calendar">
      {confirmDialog}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {isMember ? "Înscrie-te la activități. Coordonatorul le marchează ca făcute." : "Doar membrii proiectului se pot înscrie la activități."}
        </p>
        {canCoord && (
          <DSButton
            variant="primary"
            icon={Plus}
            onClick={() => setDialog({ open: true, activity: null })}
            data-testid="radacini-btn-adauga-activitate"
          >
            Adaugă activitate
          </DSButton>
        )}
      </div>

      {weeks.length === 0 ? (
        <EmptyState
          icon={CalendarDays}
          title="Nicio activitate programată"
          hint={canCoord ? "Adaugă prima activitate din proiect." : "Coordonatorul nu a programat încă activități."}
          testid="radacini-calendar-empty"
        />
      ) : (
        weeks.map((w) => {
          const sunday = new Date(w.monday);
          sunday.setUTCDate(w.monday.getUTCDate() + 6);
          return (
            <section key={w.key} className={`${CARD} p-4 md:p-5`} data-testid={`radacini-saptamana-${w.key}`}>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Săptămâna {w.week} · {w.year}
                <span className="ml-2 font-normal text-slate-500 dark:text-slate-400">
                  {shortDay(w.monday)} – {shortDay(sunday)}
                </span>
              </h3>
              <ul className="mt-2 divide-y divide-slate-100 dark:divide-white/5">
                {w.items.map((a) => (
                  <ActivityRow
                    key={a.id}
                    a={a}
                    types={types}
                    isMember={isMember}
                    canCoord={canCoord}
                    busy={busy}
                    onJoin={join}
                    onLeave={leave}
                    onDone={done}
                    onCancel={cancel}
                    onEdit={(x) => setDialog({ open: true, activity: x })}
                  />
                ))}
              </ul>
            </section>
          );
        })
      )}

      <ActivityDialog
        open={dialog.open}
        onOpenChange={(open) => setDialog((d) => ({ ...d, open }))}
        activity={dialog.activity}
        crops={crops}
        types={types}
        projectId={project.id}
        onSaved={() => {
          refresh();
          reload?.();
        }}
      />
    </div>
  );
}
