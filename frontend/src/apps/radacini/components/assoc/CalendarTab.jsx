import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { DSButton, EmptyState } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { errMsg } from "../../api";
import { s9Api } from "../../api_s9";

const STATUS = {
  done: ["Îndeplinit la timp", "bg-emerald-100 text-emerald-800"],
  on_time: ["Îndeplinit la timp", "bg-emerald-100 text-emerald-800"],
  late: ["Întârziat", "bg-amber-100 text-amber-800"],
  missed: ["Ratat", "bg-red-100 text-red-800"],
  upcoming: ["Urmează", "bg-slate-100 text-slate-700"],
};

const LEGEND = [
  ["AGA ordinară", "Adunarea generală ordinară trebuie ținută până la 30 aprilie și până la 30 noiembrie.", "art. 8(2)"],
  ["Bilanț", "Bilanțul anual se aprobă până la 31 martie.", "art. 33"],
  ["Buget", "Bugetul pe anul următor se stabilește în luna noiembrie.", "art. 32"],
  ["Plan de pășunat", "Planul de pășunat se adoptă până la sfârșitul lunii octombrie.", "art. 28"],
  ["Verificări cenzori", "Cenzorii verifică gestiunea în fiecare trimestru și întocmesc un raport.", "art. 29"],
  ["Actualizare registru", "Registrul membrilor se actualizează o dată pe an.", "art. 4(4)"],
];

const fmt = (d) => (d ? new Date(d).toLocaleDateString("ro-RO") : "—");
const asArr = (d) => (Array.isArray(d) ? d : d?.obligations || d?.items || []);

export default function CalendarTab({ assoc, access, reload }) {
  const id = assoc?.id;
  const now = new Date().getFullYear();
  const [year, setYear] = useState(now);
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  const [target, setTarget] = useState(null);
  const [note, setNote] = useState("");
  const [docId, setDocId] = useState("");
  const [docs, setDocs] = useState([]);
  const [saving, setSaving] = useState(false);

  const canEdit = ["manager", "operator", "council"].includes(access?.role);

  const load = useCallback(() => {
    setItems(null);
    setError(null);
    s9Api
      .obligations(id, year)
      .then((d) => setItems(asArr(d)))
      .catch((e) => setError(errMsg(e, "Nu am putut încărca calendarul")));
  }, [id, year]);

  useEffect(() => {
    if (id) load();
  }, [id, load]);

  const openEvidence = (o) => {
    setTarget(o);
    setNote("");
    setDocId("");
    if (!docs.length)
      s9Api
        .documentsList(id)
        .then((d) => setDocs(Array.isArray(d) ? d : d?.documents || d?.items || []))
        .catch(() => {});
  };

  const save = async () => {
    if (!note.trim()) return toast.error("Adaugă o notă");
    setSaving(true);
    try {
      await s9Api.obligationEvidence(id, target.key, { note: note.trim(), document_id: docId || undefined, year });
      toast.success("Dovada a fost adăugată");
      setTarget(null);
      load();
      reload?.();
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut salva dovada"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5" data-testid="calendar-tab">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-bold">Calendar obligații statutare</h2>
        <label className="flex items-center gap-2 text-sm">
          An
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="rounded-lg border border-slate-300 px-2 py-1.5"
            data-testid="calendar-year"
          >
            {[now + 1, now, now - 1, now - 2, now - 3].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </label>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert" data-testid="calendar-error">
          {error} <button className="ml-2 underline" onClick={load}>Reîncearcă</button>
        </div>
      ) : items === null ? (
        <div className="space-y-2" data-testid="calendar-loading">
          {[0, 1, 2].map((i) => <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-100" />)}
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="Nicio obligație pentru acest an." testid="calendar-empty" />
      ) : (
        <ol className="space-y-3 border-l-2 border-slate-200 pl-4" data-testid="calendar-timeline">
          {items.map((o) => {
            const [label, cls] = STATUS[o.status] || STATUS.upcoming;
            const ev = o.evidence || {};
            return (
              <li key={o.key} className="relative rounded-xl border border-slate-200 bg-white p-3" data-testid={`obligation-${o.key}`}>
                <span className="absolute -left-[25px] top-4 h-3 w-3 rounded-full border-2 border-white bg-slate-400" />
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold">{o.title || o.label || o.key}</p>
                    <p className="text-xs text-slate-600">
                      Termen: {fmt(o.deadline || o.due_at)}
                      {o.article ? ` · ${o.article}` : ""}
                    </p>
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${cls}`} data-testid={`obligation-status-${o.key}`}>{label}</span>
                </div>
                {(ev.note || ev.document_id || o.evidence_url || o.evidence_label) && (
                  <p className="mt-2 text-xs text-slate-700" data-testid={`obligation-evidence-${o.key}`}>
                    Dovadă:{" "}
                    {o.evidence_url || ev.url ? (
                      <a className="text-emerald-700 underline" href={o.evidence_url || ev.url}>{o.evidence_label || ev.title || "deschide"}</a>
                    ) : (
                      o.evidence_label || ev.note || ev.document_id
                    )}
                    {ev.date ? ` (${fmt(ev.date)})` : ""}
                  </p>
                )}
                {canEdit && (
                  <DSButton variant="secondary" className="mt-2" onClick={() => openEvidence(o)} data-testid={`obligation-add-evidence-${o.key}`}>
                    Adaugă dovadă
                  </DSButton>
                )}
              </li>
            );
          })}
        </ol>
      )}

      <section className="rounded-xl bg-slate-50 p-4" data-testid="calendar-legend">
        <h3 className="mb-2 font-semibold">Ce înseamnă fiecare obligație</h3>
        <ul className="space-y-2 text-sm">
          {LEGEND.map(([t, d, a]) => (
            <li key={t}><strong>{t}</strong> ({a}): {d}</li>
          ))}
        </ul>
      </section>

      <Dialog open={!!target} onOpenChange={(o) => !o && setTarget(null)}>
        <DialogContent data-testid="evidence-dialog">
          <DialogHeader>
            <DialogTitle>Dovadă manuală</DialogTitle>
            <DialogDescription>{target?.title || target?.key}</DialogDescription>
          </DialogHeader>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={4}
            placeholder="Nota (ce s-a făcut, când)"
            className="w-full rounded-lg border border-slate-300 p-2 text-sm"
            data-testid="evidence-note"
          />
          <select value={docId} onChange={(e) => setDocId(e.target.value)} className="w-full rounded-lg border border-slate-300 p-2 text-sm" data-testid="evidence-doc">
            <option value="">Fără document</option>
            {docs.map((d) => <option key={d.id} value={d.id}>{d.title || d.id}</option>)}
          </select>
          <DialogFooter>
            <DSButton variant="secondary" onClick={() => setTarget(null)}>Renunță</DSButton>
            <DSButton onClick={save} disabled={saving} data-testid="evidence-save">{saving ? "Se salvează…" : "Salvează"}</DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
