import React, { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Upload } from "lucide-react";
import { CARD, DSButton, EmptyState } from "../../../../design-system";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";
import { useConfirm } from "../ConfirmDialog";
import { asList, errMsg } from "../../api";
import {
  COUNCIL_ROLE, MEMBER_STATUS, MEMBER_STATUS_OPTS, assocImport, assocMemberCreate, assocMemberPatch, assocMembers,
  assocParticipation, canManage, canSeeRegistry, claimDecide, claimsList, fmtShare,
} from "../../api_s9";
import { Field, SelectField } from "../../shared";

const ALL = "__all__";
const NONE = "__none__";
const nf = (v) => Number(v || 0).toLocaleString("ro-RO", { maximumFractionDigits: 2 });

function Participation({ p }) {
  if (!p) return null;
  const total = Number(p.total_shares) || 1;
  const pct = (v) => Math.min(100, Math.max(0, (Number(v || 0) / total) * 100));
  const quorum = pct(p.quorum_needed_shares);
  const gap = Number(p.gap_to_quorum || 0);
  return (
    <div className={`${CARD} p-5 space-y-4`} data-testid="assoc-participation">
      <h3 className="text-lg font-bold text-slate-900 dark:text-white">Participare și cvorum</h3>
      <div className="relative h-10 rounded-xl bg-slate-200 dark:bg-white/10 overflow-hidden" role="img" aria-label="Cote active, necunoscute și cvorum">
        <div className="absolute inset-y-0 left-0 bg-emerald-500" style={{ width: `${pct(p.active_shares)}%` }} />
        <div className="absolute inset-y-0 bg-slate-500/60" style={{ left: `${pct(p.active_shares)}%`, width: `${pct(p.unknown_shares)}%` }} />
        <div className="absolute inset-y-0 w-0.5 bg-red-600" style={{ left: `${quorum}%` }} title="Cvorum" />
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-600 dark:text-slate-300">
        <span><i className="inline-block w-3 h-3 rounded-sm bg-emerald-500 mr-1" />Cote active: {nf(p.active_shares)}</span>
        <span><i className="inline-block w-3 h-3 rounded-sm bg-slate-500/60 mr-1" />Cote necunoscute: {nf(p.unknown_shares)}</span>
        <span><i className="inline-block w-0.5 h-3 bg-red-600 mr-2" />Cvorum necesar: {nf(p.quorum_needed_shares)}</span>
      </div>
      <p className={`text-2xl font-extrabold ${gap > 0 ? "text-red-700 dark:text-red-300" : "text-emerald-700 dark:text-emerald-300"}`} data-testid="assoc-gap">
        {gap > 0 ? `Mai lipsesc ${nf(gap)} cote până la cvorum` : "Cvorumul este atins"}
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div><div className="text-xs text-slate-500">Membri în registru</div><b>{p.members_count}</b></div>
        <div><div className="text-xs text-slate-500">Membri activi</div><b>{p.active_members}</b></div>
        <div><div className="text-xs text-slate-500">Total cote</div><b>{nf(p.total_shares)}</b></div>
        <div><div className="text-xs text-slate-500">Decedați nerezolvați</div><b>{p.deceased_unresolved}</b></div>
      </div>
      <div className="flex flex-wrap gap-2">
        {Object.entries(p.by_status || {}).map(([k, v]) => (
          <span key={k} className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${MEMBER_STATUS[k]?.cls || ""}`}>{MEMBER_STATUS[k]?.label || k}: {typeof v === "object" ? v.count ?? v.members : v}</span>
        ))}
      </div>
    </div>
  );
}

export default function RegistryTab({ assoc, access, reload }) {
  const id = assoc?.id;
  const allowed = canSeeRegistry(access);
  const edit = canManage(access);
  const [confirm, confirmDialog] = useConfirm();
  const [rows, setRows] = useState(null);
  const [part, setPart] = useState(null);
  const [claims, setClaims] = useState([]);
  const [status, setStatus] = useState(ALL);
  const [q, setQ] = useState("");
  const [form, setForm] = useState(null); // member edit/create
  const [reject, setReject] = useState(null);
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);

  const load = useCallback(() => {
    if (!id || !allowed) return;
    const params = {};
    if (status !== ALL) params.status = status;
    if (q.trim()) params.q = q.trim();
    assocMembers(id, params).then((d) => setRows(asList(d))).catch((e) => { setRows([]); toast.error(errMsg(e)); });
    assocParticipation(id).then(setPart).catch(() => {});
    if (edit) claimsList(id).then((d) => setClaims(asList(d).filter((c) => c.status === "pending"))).catch(() => {});
  }, [id, allowed, status, q, edit]);
  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  if (!allowed) return <EmptyState title="Registrul este vizibil doar conducerii, cenzorilor și operatorului." />;

  const save = async (e) => {
    e.preventDefault();
    const shares = Number(String(form.shares).replace(",", "."));
    if (!form.name.trim() || !(shares >= 0)) return toast.error("Completează numele și cotele.");
    const body = {
      name: form.name.trim(), shares, status: form.status,
      sources: String(form.sources || "").split(/[;\n]/).map((s) => s.trim()).filter(Boolean),
      council_role: form.council_role === NONE ? null : form.council_role,
    };
    if (form.id) {
      if (shares !== Number(form._shares) && (form.reason || "").trim().length < 5) return toast.error("Schimbarea cotelor cere un motiv (minim 5 caractere).");
      if (shares !== Number(form._shares)) body.reason = form.reason.trim();
    } else {
      body.code = form.code?.trim() || undefined;
    }
    setBusy(true);
    try {
      if (form.id) await assocMemberPatch(id, form.id, body);
      else await assocMemberCreate(id, body);
      toast.success("Registru actualizat");
      setForm(null);
      load();
    } catch (err) {
      toast.error(errMsg(err, "Nu am putut salva"));
    } finally {
      setBusy(false);
    }
  };

  const doImport = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setBusy(true);
    try {
      const r = await assocImport(id, f);
      setReport(r);
      toast.success(`Importate: ${r.imported}`);
      load();
    } catch (err) {
      toast.error(errMsg(err, "Import eșuat"));
    } finally {
      setBusy(false);
    }
  };

  const approve = async (c) => {
    if (!(await confirm({ title: "Aprobi revendicarea?", description: c.kind === "heir" ? "Se creează un rând „Moștenitor în curs” până la decizia AGA." : "Contul solicitantului va fi legat de rândul din registru.", confirmLabel: "Aprobă" }))) return;
    try {
      await claimDecide(c.id, { decision: "approve", member_id: c.member_id });
      toast.success("Revendicare aprobată");
      load();
      reload?.();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };
  const doReject = async () => {
    if (!reject.note.trim()) return toast.error("Motivul este obligatoriu.");
    try {
      await claimDecide(reject.id, { decision: "reject", note: reject.note.trim() });
      setReject(null);
      load();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  return (
    <div className="space-y-5" data-testid="assoc-registry">
      <Participation p={part} />

      {edit && claims.length > 0 && (
        <div className={`${CARD} p-5 space-y-3`} data-testid="assoc-claims-queue">
          <h3 className="font-bold text-slate-900 dark:text-white">Revendicări de analizat ({claims.length})</h3>
          {claims.map((c) => (
            <div key={c.id} className="rounded-xl border border-slate-200 dark:border-white/10 p-3 text-sm space-y-1">
              <div><b>{c.kind === "heir" ? "Moștenitor" : "Sunt eu"}</b> · {c.name_on_record || c.member_code || "—"}{c.relation ? ` · ${c.relation}` : ""}{c.user_name ? ` · cont: ${c.user_name}` : ""}</div>
              {c.note && <p className="text-slate-600 dark:text-slate-300">{c.note}</p>}
              <div className="flex gap-2 pt-1">
                <DSButton onClick={() => approve(c)} data-testid="assoc-claim-approve">Aprobă</DSButton>
                <DSButton variant="secondary" onClick={() => setReject({ id: c.id, note: "" })} data-testid="assoc-claim-reject">Respinge</DSButton>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className={`${CARD} p-5 space-y-3`}>
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-48"><Field label="Stare"><SelectField value={status} onValueChange={setStatus} options={[{ id: ALL, label: "Toate" }, ...MEMBER_STATUS_OPTS]} /></Field></div>
          <div className="flex-1 min-w-[10rem]"><Field label="Caută (cod sau nume)"><Input value={q} onChange={(e) => setQ(e.target.value)} data-testid="assoc-registry-search" /></Field></div>
          {edit && (
            <div className="flex gap-2">
              <DSButton variant="secondary" onClick={() => setForm({ name: "", shares: "", status: "unknown", sources: "", council_role: NONE, code: "" })}>Adaugă</DSButton>
              <DSButton variant="secondary" icon={Upload} disabled={busy} onClick={() => fileRef.current?.click()} data-testid="assoc-import-btn">Import CSV</DSButton>
              <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden" onChange={doImport} />
            </div>
          )}
        </div>
        {edit && <p className="text-xs text-slate-500">CSV: cod, nume, cote, surse, stare, localitate.</p>}

        {report && (
          <div className="rounded-xl bg-slate-50 dark:bg-white/5 p-3 text-sm" data-testid="assoc-import-report">
            <b>Importate: {report.imported}</b>{report.errors?.length ? ` · Erori: ${report.errors.length}` : " · fără erori"}
            {report.errors?.length > 0 && <ul className="mt-1 max-h-40 overflow-auto text-red-700 dark:text-red-300">{report.errors.map((x, i) => <li key={i}>Linia {x.line}: {x.error}</li>)}</ul>}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="assoc-registry-table">
            <thead><tr className="text-left text-xs text-slate-500"><th className="py-1">Cod</th><th>Nume</th><th className="text-right">Cote</th><th>Surse</th><th>Stare</th><th>Funcție</th><th /></tr></thead>
            <tbody>
              {(rows || []).map((r) => (
                <tr key={r.id} className="border-t border-slate-100 dark:border-white/10 align-top">
                  <td className="py-1.5">{r.code}</td><td>{r.name}</td><td className="text-right">{fmtShare(r.shares)}</td>
                  <td className="max-w-[16rem] text-xs text-slate-600 dark:text-slate-300">{(r.sources || []).map((s) => (typeof s === "string" ? s : `${s.ref || s.label} = ${fmtShare(s.share)}`)).join("; ")}</td>
                  <td><span className={`rounded-full px-2 py-0.5 text-[11px] font-bold whitespace-nowrap ${MEMBER_STATUS[r.status]?.cls || ""}`}>{MEMBER_STATUS[r.status]?.label || r.status}</span></td>
                  <td>{COUNCIL_ROLE[r.council_role] || ""}</td>
                  <td>{edit && <button className="text-xs underline font-semibold" onClick={() => setForm({ ...r, _shares: r.shares, sources: (r.sources || []).map((s) => (typeof s === "string" ? s : `${s.ref || s.label} = ${s.share}`)).join("; "), council_role: r.council_role || NONE, reason: "" })}>Editează</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows && rows.length === 0 && <p className="py-4 text-sm text-slate-500">Niciun rând.</p>}
        </div>
      </div>

      <Dialog open={!!form} onOpenChange={(o) => !o && setForm(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>{form?.id ? `Editează ${form.code}` : "Rând nou în registru"}</DialogTitle></DialogHeader>
          {form && (
            <form onSubmit={save} className="space-y-3">
              <Field label="Nume"><Input value={form.name} onChange={set("name")} /></Field>
              <Field label="Cote"><Input inputMode="decimal" value={form.shares} onChange={set("shares")} /></Field>
              {form.id && String(form.shares).replace(",", ".") !== String(form._shares) && (
                <Field label="Motivul schimbării cotelor (obligatoriu)"><Textarea value={form.reason} onChange={set("reason")} data-testid="assoc-shares-reason" /></Field>
              )}
              <Field label="Surse (separate prin ;)" hint="Ex: Nr 372 = 0,20; Nr 410 = 0,10"><Input value={form.sources} onChange={set("sources")} /></Field>
              <Field label="Stare"><SelectField value={form.status} onValueChange={(v) => setForm({ ...form, status: v })} options={MEMBER_STATUS_OPTS} /></Field>
              <Field label="Funcție"><SelectField value={form.council_role} onValueChange={(v) => setForm({ ...form, council_role: v })} options={[{ id: NONE, label: "Membru simplu" }, ...Object.entries(COUNCIL_ROLE).map(([id, label]) => ({ id, label }))]} /></Field>
              <DialogFooter>
                <DSButton type="button" variant="secondary" onClick={() => setForm(null)}>Renunță</DSButton>
                <DSButton type="submit" disabled={busy}>Salvează</DSButton>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={!!reject} onOpenChange={(o) => !o && setReject(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Respinge revendicarea</DialogTitle></DialogHeader>
          <Field label="Motiv (obligatoriu)"><Textarea value={reject?.note || ""} onChange={(e) => setReject({ ...reject, note: e.target.value })} /></Field>
          <DialogFooter>
            <DSButton variant="secondary" onClick={() => setReject(null)}>Renunță</DSButton>
            <DSButton variant="danger" onClick={doReject}>Respinge</DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {confirmDialog}
    </div>
  );
}
