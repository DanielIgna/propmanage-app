import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Flag } from "lucide-react";
import { CARD, DSButton, EmptyState, TabBar } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { Textarea } from "../../../components/ui/textarea";
import { errMsg } from "../api";
import { betaApi, REPORT_DECISIONS, REPORT_TARGETS } from "../api_beta";
import { useStaffMe } from "../hooks";
import { Field, fmtDateTime, PageHeader, PageSkeleton } from "../shared";

const TARGET_LINK = {
  listing: (id) => `/radacini/piata/${id}`,
  parcel: (id) => `/radacini/terenuri/${id}`,
  community: (id) => `/radacini/comunitati/${id}`,
};
const selectCls = "w-full rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm dark:border-white/15 dark:bg-white/5";

const StatusPill = ({ r }) =>
  r.status === "open" ? (
    <span className="rounded-full bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-200 px-2 py-0.5 text-xs font-bold">În analiză</span>
  ) : (
    <span className="rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-200 px-2 py-0.5 text-xs font-bold">Închisă</span>
  );

function ReportItem({ r, staff, onResolve }) {
  const link = TARGET_LINK[r.target_type]?.(r.target_id);
  const title = r.target_title || REPORT_TARGETS[r.target_type] || "conținut";
  return (
    <li className={`${CARD} p-4 space-y-2`} data-testid={`radacini-report-item-${r.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs text-slate-500">{REPORT_TARGETS[r.target_type] || r.target_type} · {fmtDateTime(r.created_at)}</p>
          <p className="font-semibold break-words text-slate-900 dark:text-white">
            {link ? <Link to={link} className="underline">{title}</Link> : title}
          </p>
        </div>
        <StatusPill r={r} />
      </div>
      <p className="text-sm"><b>Motiv:</b> {r.reason_label || r.reason}</p>
      {r.details && <p className="text-sm whitespace-pre-line break-words text-slate-700 dark:text-slate-200">{r.details}</p>}
      {staff && r.reporter_name && <p className="text-xs text-slate-500">Raportat de {r.reporter_name}</p>}
      {r.status === "resolved" && (
        <p className="text-sm rounded bg-slate-50 dark:bg-white/5 p-2 break-words">
          <b>Decizie:</b> {r.decision_label || r.decision}. {r.decision_note}
          {staff && r.resolved_by_name ? <span className="text-xs text-slate-500"> · {r.resolved_by_name}</span> : null}
        </p>
      )}
      {staff && r.status === "open" && (
        <DSButton variant="secondary" onClick={() => onResolve(r)} data-testid={`radacini-report-resolve-${r.id}`}>Decide</DSButton>
      )}
    </li>
  );
}

function ResolveDialog({ r, onClose, onDone }) {
  const [decision, setDecision] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!decision) return toast.error("Alege decizia.");
    if (note.trim().length < 3) return toast.error("Scrie motivarea (minimum 3 caractere).");
    setBusy(true);
    try {
      await betaApi.resolveReport(r.id, { decision, note: note.trim() });
      toast.success("Decizie trimisă. Raportorul a fost anunțat.");
      onDone();
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut salva decizia"));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-report-resolve-dialog">
        <DialogHeader>
          <DialogTitle>Decizie la raportare</DialogTitle>
          <DialogDescription className="break-words">
            {r.target_title || REPORT_TARGETS[r.target_type]} · {r.reason_label}. Pentru restricționare, închide întâi anunțul sau pune terenul pe pauză din paginile lor.
          </DialogDescription>
        </DialogHeader>
        <Field label="Decizie" htmlFor="res-decision">
          <select id="res-decision" value={decision} onChange={(e) => setDecision(e.target.value)} className={selectCls}>
            <option value="">— alege —</option>
            {REPORT_DECISIONS.map((d) => <option key={d.id} value={d.id}>{d.label}</option>)}
          </select>
        </Field>
        <Field label="Motivare" htmlFor="res-note" hint="O primesc raportorul și, dacă iei măsuri, autorul conținutului.">
          <Textarea id="res-note" rows={4} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton onClick={submit} disabled={busy} data-testid="radacini-report-resolve-submit">{busy ? "Se salvează…" : "Trimite decizia"}</DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Coada personalului (folosită și în Administrare → Raportări).
export function StaffReportsQueue() {
  const [status, setStatus] = useState("open");
  const [state, setState] = useState({ loading: true, items: [], error: null });
  const [resolving, setResolving] = useState(null);
  const load = useCallback(() => {
    setState((s) => ({ ...s, loading: true }));
    betaApi.staffReports(status === "all" ? undefined : status).then(
      (d) => setState({ loading: false, items: d?.items || [], error: null }),
      (e) => setState({ loading: false, items: [], error: e })
    );
  }, [status]);
  useEffect(() => { load(); }, [load]);
  return (
    <div className="space-y-3" data-testid="radacini-staff-reports">
      <TabBar tabs={[["open", "De analizat"], ["resolved", "Închise"], ["all", "Toate"]]} active={status} onChange={setStatus} testidPrefix="radacini-reports-filter" />
      {state.loading && <PageSkeleton />}
      {!state.loading && state.error && <EmptyState icon={Flag} title="Nu am putut încărca raportările" hint={errMsg(state.error)} />}
      {!state.loading && !state.error && !state.items.length && <EmptyState icon={Flag} title="Nicio raportare aici" />}
      <ul className="space-y-3">
        {state.items.map((r) => <ReportItem key={r.id} r={r} staff onResolve={setResolving} />)}
      </ul>
      {resolving && <ResolveDialog r={resolving} onClose={() => setResolving(null)} onDone={() => { setResolving(null); load(); }} />}
    </div>
  );
}

function MyReports() {
  const [state, setState] = useState({ loading: true, items: [], error: null });
  useEffect(() => {
    betaApi.myReports().then(
      (d) => setState({ loading: false, items: d?.items || [], error: null }),
      (e) => setState({ loading: false, items: [], error: e })
    );
  }, []);
  if (state.loading) return <PageSkeleton />;
  if (state.error) return <EmptyState icon={Flag} title="Nu am putut încărca raportările" hint={errMsg(state.error)} />;
  if (!state.items.length)
    return <EmptyState icon={Flag} title="Nu ai trimis nicio raportare" hint="Butonul „Raportează” apare pe anunțuri, terenuri și comunități." testid="radacini-reports-empty" />;
  return <ul className="space-y-3">{state.items.map((r) => <ReportItem key={r.id} r={r} />)}</ul>;
}

export default function Raportari() {
  const { staff } = useStaffMe();
  const [tab, setTab] = useState("mine");
  return (
    <div className="space-y-5 max-w-3xl" data-testid="radacini-raportari">
      <PageHeader
        title="Raportări"
        subtitle="Conținut semnalat ca ilegal sau contrar regulilor. Fiecare raportare primește o decizie motivată."
      />
      {staff?.is_staff ? (
        <>
          <TabBar tabs={[["mine", "Raportările mele"], ["queue", "De moderat"]]} active={tab} onChange={setTab} testidPrefix="radacini-reports-tab" />
          {tab === "mine" ? <MyReports /> : <StaffReportsQueue />}
        </>
      ) : (
        <MyReports />
      )}
    </div>
  );
}
