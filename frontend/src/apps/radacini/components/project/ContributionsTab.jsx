import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Check, CornerDownRight, Flag, Plus, Wallet } from "lucide-react";
import { useConfirm } from "../ConfirmDialog";
import { CARD, DSButton, EmptyState } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../../components/ui/table";
import { radaciniApi, asList, errMsg } from "../../api";
import { useMeta } from "../../hooks";
import {
  CONTRIBUTION_KINDS,
  Field,
  FORCED_UNIT,
  PROJECT_DISCLAIMER,
  PageSkeleton,
  SelectField,
  StatusBadge,
  fmtDate,
  labelOf,
  optsOr,
  todayIso,
} from "../../shared";

const NONE = "__none__";
const ALL = "__all__";

const kindOf = (id) => CONTRIBUTION_KINDS.find((k) => k.id === id);
const unitFor = (kind) => FORCED_UNIT[kind] ?? kindOf(kind)?.unit ?? "";

// Formular: adăugare nouă sau corecție (corects_id) a unei înregistrări existente.
function ContributionDialog({ open, onOpenChange, original, activities, kinds, projectId, onSaved }) {
  const blank = { kind: "labor_hours", amount: "", unit: "ore", description: "", date: todayIso(), activity_id: NONE };
  const [form, setForm] = useState(blank);
  const [saving, setSaving] = useState(false);
  const isCorrection = !!original;

  useEffect(() => {
    if (!open) return;
    setForm(
      original
        ? {
            kind: original.kind,
            amount: original.amount ?? "",
            unit: original.unit || "",
            description: original.description || "",
            date: String(original.date || todayIso()).slice(0, 10),
            activity_id: original.activity_id || NONE,
          }
        : { ...blank, date: todayIso() }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, original]);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const setKind = (kind) => setForm((f) => ({ ...f, kind, unit: unitFor(kind) }));

  const desc = form.description.trim();
  const valid = Number(form.amount) > 0 && desc.length >= 3 && desc.length <= 300 && !!form.date && form.date <= todayIso();

  const save = async () => {
    if (!valid) return;
    const body = {
      kind: form.kind,
      amount: Number(form.amount),
      description: desc,
      date: form.date,
    };
    if (form.unit.trim()) body.unit = form.unit.trim();
    if (form.activity_id !== NONE) body.activity_id = form.activity_id;
    if (isCorrection) body.corrects_id = original.id;
    setSaving(true);
    try {
      await radaciniApi.createContribution(projectId, body);
      toast.success(isCorrection ? "Corecția a fost înregistrată" : "Contribuția a fost înregistrată");
      onOpenChange(false);
      onSaved();
    } catch (e) {
      toast.error(errMsg(e, "Contribuția nu a putut fi salvată"));
    } finally {
      setSaving(false);
    }
  };

  const activityOptions = [{ id: NONE, label: "Fără activitate" }, ...activities.map((a) => ({ id: a.id, label: `${a.title} (${fmtDate(a.date)})` }))];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="radacini-contributie-dialog" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isCorrection ? "Corectează înregistrarea" : "Adaugă contribuție"}</DialogTitle>
          <DialogDescription>
            {isCorrection
              ? "Corecția este o înregistrare nouă. Înregistrarea inițială rămâne în istoric."
              : "Înregistrează ce ai adus în proiect: timp, materiale sau bani cheltuiți."}
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Tip" htmlFor="contrib-kind">
            <SelectField id="contrib-kind" value={form.kind} onValueChange={setKind} options={kinds} testid="radacini-contributie-tip" />
          </Field>
          <Field label="Cantitate" htmlFor="contrib-amount">
            <Input id="contrib-amount" type="number" min="0" step="any" value={form.amount} onChange={(e) => set("amount")(e.target.value)} data-testid="radacini-contributie-cantitate" />
          </Field>
          <Field label="Unitate" htmlFor="contrib-unit" hint={FORCED_UNIT[form.kind] ? "Unitatea este fixă pentru acest tip." : "Ex. kg, buc., m²."}>
            <Input
              id="contrib-unit"
              value={form.unit}
              maxLength={20}
              disabled={!!FORCED_UNIT[form.kind]}
              onChange={(e) => set("unit")(e.target.value)}
            />
          </Field>
          <Field label="Data" htmlFor="contrib-date">
            <Input id="contrib-date" type="date" max={todayIso()} value={form.date} onChange={(e) => set("date")(e.target.value)} />
          </Field>
          <div className="sm:col-span-2">
            <Field label="Descriere" htmlFor="contrib-desc" hint="Între 3 și 300 de caractere.">
              <Textarea id="contrib-desc" rows={3} maxLength={300} value={form.description} onChange={(e) => set("description")(e.target.value)} data-testid="radacini-contributie-descriere" />
            </Field>
          </div>
          {activities.length > 0 && (
            <div className="sm:col-span-2">
              <Field label="Activitate legată" htmlFor="contrib-activity">
                <SelectField id="contrib-activity" value={form.activity_id} onValueChange={set("activity_id")} options={activityOptions} testid="radacini-contributie-activitate" />
              </Field>
            </div>
          )}
        </div>

        <DialogFooter>
          <DSButton variant="secondary" onClick={() => onOpenChange(false)} data-testid="radacini-contributie-anuleaza">
            Renunță
          </DSButton>
          <DSButton variant="primary" disabled={!valid || saving} onClick={save} data-testid="radacini-contributie-salveaza">
            {saving ? "Se salvează…" : "Salvează"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Contestarea cere o notă (obligatorie în backend).
function DisputeDialog({ target, onClose, onDone }) {
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const ok = note.trim().length >= 3;

  useEffect(() => {
    if (target) setNote("");
  }, [target]);

  const submit = async () => {
    if (!ok) return;
    setSaving(true);
    try {
      await radaciniApi.reviewContribution(target.id, "dispute", note.trim());
      toast.success("Contribuția a fost contestată");
      onClose();
      onDone();
    } catch (e) {
      toast.error(errMsg(e, "Contestarea nu a reușit"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={!!target} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-contestare-dialog">
        <DialogHeader>
          <DialogTitle>Contestă contribuția</DialogTitle>
          <DialogDescription>Explică pe scurt de ce nu poate fi confirmată. Nota este vizibilă tuturor membrilor.</DialogDescription>
        </DialogHeader>
        <Field label="Motivul contestării" htmlFor="dispute-note">
          <Textarea id="dispute-note" rows={3} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} data-testid="radacini-contestare-nota" />
        </Field>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose} data-testid="radacini-contestare-anuleaza">
            Renunță
          </DSButton>
          <DSButton variant="danger" disabled={!ok || saving} onClick={submit} data-testid="radacini-contestare-trimite">
            {saving ? "Se trimite…" : "Contestă"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function ContributionsTab({ project, members, isMember, me, reload }) {
  const [confirm, confirmDialog] = useConfirm();
  const { meta } = useMeta();
  const kinds = optsOr(meta?.contribution_kinds, CONTRIBUTION_KINDS);
  const [data, setData] = useState({ loaded: false, items: [], totals: [] });
  const [activities, setActivities] = useState([]);
  const [memberFilter, setMemberFilter] = useState(ALL);
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [correcting, setCorrecting] = useState(null);
  const [disputing, setDisputing] = useState(null);

  // Drepturile de confirmare le decide backend-ul (can_review); aici doar ascundem când proiectul nu e scriptibil.
  const canReview = (c) => isMember && !!c.can_review && c.status === "logged";

  useEffect(() => {
    let alive = true;
    const params = memberFilter === ALL ? undefined : { member: memberFilter };
    radaciniApi
      .projectContributions(project.id, params)
      .then((d) => alive && setData({ loaded: true, items: asList(d), totals: d?.totals || [] }))
      .catch((e) => {
        if (!alive) return;
        toast.error(errMsg(e, "Nu am putut încărca contribuțiile"));
        setData({ loaded: true, items: [], totals: [] });
      });
    return () => {
      alive = false;
    };
  }, [project.id, memberFilter, tick]);

  useEffect(() => {
    let alive = true;
    radaciniApi
      .projectActivities(project.id)
      .then((d) => alive && setActivities(asList(d).filter((a) => a.status !== "cancelled")))
      .catch(() => alive && setActivities([]));
    return () => {
      alive = false;
    };
  }, [project.id]);

  const refresh = () => setTick((t) => t + 1);
  const memberName = (uid) => members.find((m) => m.user_id === uid)?.name || "—";

  const review = async (c) => {
    if (
      !(await confirm({
        title: "Confirmi contribuția?",
        description: `${c.member_name || memberName(c.member_user_id)} · ${labelOf(kinds, c.kind)} · ${c.amount} ${c.unit || ""}`,
        confirmLabel: "Confirmă",
      }))
    )
      return;
    setBusy(true);
    try {
      await radaciniApi.reviewContribution(c.id, "confirm");
      toast.success("Contribuția a fost confirmată");
      refresh();
      reload?.();
    } catch (e) {
      toast.error(errMsg(e, "Confirmarea nu a reușit"));
    } finally {
      setBusy(false);
    }
  };

  if (!data.loaded) return <PageSkeleton />;

  return (
    <div className="space-y-4" data-testid="radacini-contributii">
      {confirmDialog}

      <aside
        className="rounded-2xl border-2 border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-500/10 p-4 text-sm text-amber-900 dark:text-amber-100"
        data-testid="radacini-contributii-disclaimer"
      >
        {PROJECT_DISCLAIMER}
      </aside>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="w-full sm:w-64">
          <SelectField
            id="contrib-filter"
            value={memberFilter}
            onValueChange={setMemberFilter}
            options={[{ id: ALL, label: "Toți membrii" }, ...members.map((m) => ({ id: m.user_id, label: m.name || "—" }))]}
            testid="radacini-contributii-filtru"
          />
        </div>
        {isMember && (
          <DSButton variant="primary" icon={Plus} onClick={() => setFormOpen(true)} data-testid="radacini-btn-adauga-contributie">
            Adaugă contribuție
          </DSButton>
        )}
      </div>

      {data.items.length === 0 ? (
        <EmptyState icon={Wallet} title="Nicio contribuție încă" hint="Contribuțiile apar aici după ce sunt înregistrate." testid="radacini-contributii-empty" />
      ) : (
        <ul className="space-y-2" data-testid="radacini-contributii-lista">
          {data.items.map((c) => {
            const mine = c.member_user_id === me;
            return (
              <li
                key={c.id}
                className={`${CARD} p-4 space-y-2 ${c.corrects_id ? "ml-0 sm:ml-6" : ""}`}
                data-testid={`radacini-contributie-${c.id}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-900 dark:text-white break-words">
                      {c.member_name || memberName(c.member_user_id)} · {labelOf(kinds, c.kind)}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {fmtDate(c.date)} · {c.amount} {c.unit || ""}
                      {c.corrects_id && (
                        <span className="ml-2 inline-flex items-center gap-1 font-semibold text-slate-600 dark:text-slate-300">
                          <CornerDownRight className="w-3 h-3" /> Corecție
                        </span>
                      )}
                      {c.corrected_by_id && (
                        <span className="ml-2 font-semibold text-slate-600 dark:text-slate-300" data-testid={`radacini-contributie-corectata-${c.id}`}>
                          · Corectată
                        </span>
                      )}
                    </p>
                  </div>
                  <StatusBadge status={c.status} testid={`radacini-contributie-status-${c.id}`} />
                </div>

                <p className="text-sm text-slate-700 dark:text-slate-200 whitespace-pre-line break-words">{c.description}</p>

                {c.status === "disputed" && c.review_note && (
                  <p className="text-xs text-rose-700 dark:text-rose-300">Motiv contestare: {c.review_note}</p>
                )}

                {(canReview(c) || (isMember && mine && !c.corrected_by_id)) && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {canReview(c) && (
                      <>
                        <DSButton variant="success" icon={Check} disabled={busy} onClick={() => review(c)} data-testid={`radacini-contributie-confirma-${c.id}`}>
                          Confirmă
                        </DSButton>
                        <DSButton variant="danger" icon={Flag} disabled={busy} onClick={() => setDisputing(c)} data-testid={`radacini-contributie-contesta-${c.id}`}>
                          Contestă
                        </DSButton>
                      </>
                    )}
                    {isMember && mine && !c.corrected_by_id && (
                      <DSButton variant="secondary" onClick={() => setCorrecting(c)} data-testid={`radacini-contributie-corecteaza-${c.id}`}>
                        Corectează
                      </DSButton>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <section className={`${CARD} overflow-x-auto`} data-testid="radacini-contributii-totaluri">
        <div className="p-4 pb-2">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">Totaluri pe membru</h3>
        </div>
        {data.totals.length === 0 ? (
          <p className="px-4 pb-4 text-sm text-slate-500 dark:text-slate-400">Nu există totaluri încă.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Membru</TableHead>
                <TableHead>Tip</TableHead>
                <TableHead>Confirmate</TableHead>
                <TableHead>În așteptare</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.totals.map((t) => (
                <TableRow key={`${t.member_user_id}-${t.kind}-${t.unit}`}>
                  <TableCell className="font-semibold">{t.member_name || memberName(t.member_user_id)}</TableCell>
                  <TableCell>{labelOf(kinds, t.kind)}</TableCell>
                  <TableCell>
                    {Number(t.confirmed || 0).toLocaleString("ro-RO")} {t.unit}
                  </TableCell>
                  <TableCell>
                    {Number(t.pending || 0).toLocaleString("ro-RO")} {t.unit}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>

      <ContributionDialog
        open={formOpen || !!correcting}
        onOpenChange={(open) => {
          if (!open) {
            setFormOpen(false);
            setCorrecting(null);
          }
        }}
        original={correcting}
        activities={activities}
        kinds={kinds}
        projectId={project.id}
        onSaved={() => {
          refresh();
          reload?.();
        }}
      />

      <DisputeDialog
        target={disputing}
        onClose={() => setDisputing(null)}
        onDone={() => {
          refresh();
          reload?.();
        }}
      />
    </div>
  );
}
