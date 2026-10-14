import React, { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, CalendarPlus, CheckCircle2, Gavel, Handshake, Mail, Plus, Users } from "lucide-react";
import { DSButton } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";
import { errMsg } from "../../api";
import {
  assocMembers, canManage, fmtShare, mandateCreate, mandateRevoke, meetingAck, meetingAttendance, meetingConvene,
  meetingCreate, meetingDecisions, meetingGet, meetingsList,
} from "../../api_s9";
import { useConfirm } from "../ConfirmDialog";
import { Field, SelectField, fmtDate, fmtDateTime } from "../../shared";

const KINDS = [
  { id: "aga_ordinary", label: "AGA ordinară" },
  { id: "aga_extraordinary", label: "AGA extraordinară" },
  { id: "council", label: "Ședință CA" },
];
const kindLabel = (k) => KINDS.find((x) => x.id === k)?.label || k;
const DAY = 86400000;
const daysUntil = (iso) => (iso ? Math.ceil((new Date(iso).getTime() - Date.now()) / DAY) : null);
const pct = (a, b) => (b > 0 ? Math.min(100, Math.round((Number(a || 0) / Number(b)) * 100)) : 0);

export default function MeetingsTab({ assoc, access, reload }) {
  const assocId = assoc?.id;
  const council = canManage(access);
  const [list, setList] = useState(null);
  const [error, setError] = useState("");
  const [sel, setSel] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await meetingsList(assocId);
      setList(Array.isArray(r) ? r : r?.items || r?.meetings || []);
    } catch (e) {
      setError(errMsg(e, "Nu am putut încărca ședințele"));
      setList([]);
    }
  }, [assocId]);
  useEffect(() => {
    if (assocId) load();
  }, [assocId, load]);

  const sorted = useMemo(() => [...(list || [])].sort((a, b) => String(b.date).localeCompare(String(a.date))), [list]);

  return (
    <div className="space-y-4" data-testid="radacini-meetings-tab">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate-600 dark:text-slate-300 min-w-0">
          Convocarea se face cu cel puțin {assoc?.rules?.convocation_days ?? 15} zile înainte. Hotărârile pot fi contestate în termenul afișat.
        </p>
        {council && (
          <DSButton icon={CalendarPlus} onClick={() => setCreateOpen(true)} data-testid="radacini-meeting-create-btn">Ședință nouă</DSButton>
        )}
      </div>
      {list === null && <p className="text-sm text-slate-500" data-testid="radacini-meetings-loading">Se încarcă…</p>}
      {error && <p className="text-sm text-red-600" data-testid="radacini-meetings-error">{error}</p>}
      {list && !list.length && !error && <p className="text-sm text-slate-500" data-testid="radacini-meetings-empty">Nicio ședință înregistrată.</p>}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <ul className="space-y-2">
          {sorted.map((m) => (
            <li key={m.id}>
              <button type="button" onClick={() => setSel(m.id)} data-testid={`radacini-meeting-item-${m.id}`}
                className={`w-full text-left rounded-lg border p-3 ${sel === m.id ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/30" : "border-slate-200 dark:border-slate-700"}`}>
                <span className="inline-block text-xs font-semibold rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5">{kindLabel(m.kind)}</span>
                <p className="font-semibold mt-1">{fmtDate(m.date)}{m.place ? ` · ${m.place}` : ""}</p>
                <div className="flex flex-wrap gap-1 mt-1 text-xs">
                  {m.held_without_quorum && <span className="rounded-full bg-red-100 text-red-700 px-2 py-0.5 font-semibold">ținută fără cvorum (art. 9(2))</span>}
                  {m.convened_at ? <span className="text-slate-500">convocată</span> : <span className="text-amber-600">neconvocată</span>}
                </div>
              </button>
            </li>
          ))}
        </ul>
        {sel ? (
          <MeetingDetail key={sel} id={sel} assoc={assoc} access={access} council={council} onChanged={() => { load(); reload?.(); }} />
        ) : (
          list?.length > 0 && <p className="text-sm text-slate-500">Alege o ședință din listă pentru detalii.</p>
        )}
      </div>
      {createOpen && <CreateDialog assocId={assocId} onClose={() => setCreateOpen(false)} onDone={() => { setCreateOpen(false); load(); }} />}
    </div>
  );
}

function CreateDialog({ assocId, onClose, onDone }) {
  const [f, setF] = useState({ kind: "aga_ordinary", date: "", place: "", agenda: "", materials: "" });
  const [busy, setBusy] = useState(false);
  const set = (k) => (v) => setF((p) => ({ ...p, [k]: v }));
  const submit = async () => {
    const agenda = f.agenda.split("\n").map((s) => s.trim()).filter(Boolean).map((title) => ({ title, details: "" }));
    if (!f.date) return toast.error("Alege data ședinței.");
    if (!agenda.length) return toast.error("Adaugă cel puțin un punct pe ordinea de zi.");
    setBusy(true);
    try {
      await meetingCreate(assocId, {
        kind: f.kind, date: f.date, place: f.place.trim(), agenda,
        material_ids: f.materials.split(/[\s,]+/).filter(Boolean),
      });
      toast.success("Ședința a fost creată");
      onDone();
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut crea ședința"));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-meeting-create-dialog" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>Ședință nouă</DialogTitle><DialogDescription>Convocarea se trimite separat, după creare.</DialogDescription></DialogHeader>
        <div className="space-y-3">
          <Field label="Tip" htmlFor="m-kind"><SelectField id="m-kind" value={f.kind} onValueChange={set("kind")} options={KINDS} testid="radacini-meeting-kind" /></Field>
          <Field label="Data" htmlFor="m-date"><Input id="m-date" type="date" value={f.date} onChange={(e) => set("date")(e.target.value)} data-testid="radacini-meeting-date" /></Field>
          <Field label="Locul" htmlFor="m-place"><Input id="m-place" value={f.place} onChange={(e) => set("place")(e.target.value)} data-testid="radacini-meeting-place" /></Field>
          <Field label="Ordinea de zi" htmlFor="m-agenda" hint="Un punct pe rând."><Textarea id="m-agenda" rows={4} value={f.agenda} onChange={(e) => set("agenda")(e.target.value)} data-testid="radacini-meeting-agenda" /></Field>
          <Field label="Materiale (ID-uri documente)" htmlFor="m-mat" hint="Opțional, separate prin virgulă."><Input id="m-mat" value={f.materials} onChange={(e) => set("materials")(e.target.value)} /></Field>
        </div>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton onClick={submit} disabled={busy} data-testid="radacini-meeting-create-submit">{busy ? "Se salvează…" : "Creează"}</DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function MeetingDetail({ id, assoc, access, council, onChanged }) {
  const [m, setM] = useState(null);
  const [err, setErr] = useState("");
  const [dlg, setDlg] = useState(null); // convene | attendance | decisions | mandate
  const [confirm, confirmDialog] = useConfirm();
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await meetingGet(id);
      setM(r?.meeting || r);
      setErr("");
    } catch (e) {
      setErr(errMsg(e, "Nu am putut încărca ședința"));
    }
  }, [id]);
  useEffect(() => { load(); }, [load]);
  const done = () => { setDlg(null); load(); onChanged?.(); };

  if (err) return <p className="text-sm text-red-600" data-testid="radacini-meeting-error">{err}</p>;
  if (!m) return <p className="text-sm text-slate-500">Se încarcă…</p>;

  const convs = m.convocations || [];
  const sent = convs.length;
  const confirmed = convs.filter((c) => c.read_at || c.acked_at).length;
  const myId = access?.member?.id;
  const myConv = convs.find((c) => c.member_id === myId);
  const dBefore = m.convened_at ? Math.floor((new Date(m.date) - new Date(m.convened_at)) / DAY) : null;
  const minDays = assoc?.rules?.convocation_days ?? 15;
  const short = dBefore != null && dBefore < minDays;
  const total = m.total_shares ?? assoc?.total_shares;
  const rep = m.represented_shares;
  const upcoming = new Date(m.date) > new Date();
  const myMandate = (m.mandates || []).find((x) => x.principal_member_id === myId);

  const ack = async () => {
    setBusy(true);
    try { await meetingAck(m.id); toast.success("Primirea a fost confirmată"); done(); }
    catch (e) { toast.error(errMsg(e, "Nu am putut confirma")); }
    finally { setBusy(false); }
  };
  const revoke = async (mand) => {
    if (!(await confirm({ title: "Revoci mandatul?", description: "Reprezentantul nu te va mai putea reprezenta la această ședință.", confirmLabel: "Revocă", danger: true }))) return;
    try { await mandateRevoke(mand.id); toast.success("Mandat revocat"); done(); }
    catch (e) { toast.error(errMsg(e, "Nu am putut revoca mandatul")); }
  };

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-4 min-w-0" data-testid="radacini-meeting-detail">
      <div>
        <p className="text-xs font-semibold text-slate-500">{kindLabel(m.kind)}</p>
        <h3 className="text-lg font-bold">{fmtDate(m.date)}{m.place ? ` · ${m.place}` : ""}</h3>
        {m.held_without_quorum && (
          <span className="inline-flex items-center gap-1 mt-1 rounded-full bg-red-100 text-red-700 px-2.5 py-0.5 text-xs font-bold" data-testid="radacini-meeting-no-quorum">
            <AlertTriangle className="h-3.5 w-3.5" /> ținută fără cvorum (art. 9(2))
          </span>
        )}
      </div>

      <section>
        <h4 className="text-sm font-bold">Ordinea de zi</h4>
        <ol className="list-decimal ml-5 text-sm space-y-0.5">
          {(m.agenda || []).map((a, i) => <li key={i}>{a.title}{a.details ? ` — ${a.details}` : ""}</li>)}
        </ol>
        {(m.material_ids || []).length > 0 && <p className="text-xs text-slate-500 mt-1">Materiale atașate: {m.material_ids.length} (vezi fila Documente)</p>}
      </section>

      <section className="space-y-2" data-testid="radacini-meeting-convocation">
        <h4 className="text-sm font-bold flex items-center gap-1.5"><Mail className="h-4 w-4" />Convocare</h4>
        {!m.convened_at ? <p className="text-sm text-amber-600">Ședința nu a fost încă convocată.</p> : (
          <p className="text-sm">Trimisă la {fmtDateTime(m.convened_at)} · {sent} destinatari · {confirmed} confirmări{dBefore != null ? ` · cu ${dBefore} zile înainte` : ""}</p>
        )}
        {short && (
          <p className="text-sm text-amber-700 bg-amber-50 dark:bg-amber-950/30 rounded p-2" data-testid="radacini-meeting-short-notice">
            Atenție: convocarea s-a făcut cu mai puțin de {minDays} zile înainte, deci hotărârile pot fi contestate.
          </p>
        )}
        {m.registered_mail_document_id && <p className="text-xs text-slate-500">Dovadă recomandată: document {m.registered_mail_document_id}</p>}
        {myConv && !(myConv.read_at || myConv.acked_at) && (
          <DSButton icon={CheckCircle2} onClick={ack} disabled={busy} data-testid="radacini-meeting-ack">Confirm primirea</DSButton>
        )}
        {myConv && (myConv.read_at || myConv.acked_at) && <p className="text-sm text-emerald-700">Ai confirmat primirea convocării.</p>}
      </section>

      {total > 0 && rep != null && (
        <section data-testid="radacini-meeting-quorum">
          <h4 className="text-sm font-bold flex items-center gap-1.5"><Users className="h-4 w-4" />Cvorum</h4>
          <p className="text-sm">Cote reprezentate: {fmtShare(rep)} din {fmtShare(total)} ({pct(rep, total)}%)</p>
          <div className="relative h-3 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden mt-1">
            <div className={`h-full ${m.quorum_met ? "bg-emerald-500" : "bg-amber-500"}`} style={{ width: `${pct(rep, total)}%` }} />
            <div className="absolute top-0 bottom-0 w-0.5 bg-slate-800" style={{ left: "50%" }} title="Majoritatea cotelor" />
          </div>
          <p className="text-xs text-slate-500 mt-1">{m.quorum_met ? "Cvorum întrunit." : "Cvorum neîntrunit (e nevoie de majoritatea cotelor)."}</p>
        </section>
      )}

      {(m.decisions || []).length > 0 && (
        <section data-testid="radacini-meeting-decisions">
          <h4 className="text-sm font-bold flex items-center gap-1.5"><Gavel className="h-4 w-4" />Hotărâri</h4>
          <ul className="space-y-2 text-sm">
            {m.decisions.map((d, i) => (
              <li key={i} className="rounded bg-slate-50 dark:bg-slate-800/50 p-2">
                <p className="font-semibold">{d.title}</p>
                <p>{d.result_text}</p>
                {(d.votes_for != null || d.votes_against != null) && <p className="text-xs text-slate-500">Pentru {d.votes_for ?? 0} · Împotrivă {d.votes_against ?? 0} · Abțineri {d.abstentions ?? 0}</p>}
              </li>
            ))}
          </ul>
          {m.contest_until && (() => {
            const left = daysUntil(m.contest_until);
            return (
              <p className="text-sm mt-2 font-semibold" data-testid="radacini-meeting-contest">
                Termen de contestare până la {fmtDate(m.contest_until)}{" "}
                <span className={left > 0 ? "text-amber-700" : "text-slate-500"}>{left > 0 ? `(mai sunt ${left} zile)` : "(expirat)"}</span>
              </p>
            );
          })()}
        </section>
      )}

      {(m.mandates || []).length > 0 && council && <p className="text-xs text-slate-500">Mandate înregistrate: {m.mandates.length}</p>}

      <div className="flex flex-wrap gap-2">
        {council && (
          <>
            {!m.decisions?.length && <DSButton variant="secondary" icon={Mail} onClick={() => setDlg("convene")} data-testid="radacini-meeting-convene-btn">{m.convened_at ? "Retrimite convocarea" : "Convoacă"}</DSButton>}
            <DSButton variant="secondary" icon={Users} onClick={() => setDlg("attendance")} data-testid="radacini-meeting-attendance-btn">Prezență</DSButton>
            <DSButton variant="secondary" icon={Gavel} onClick={() => setDlg("decisions")} data-testid="radacini-meeting-decisions-btn">Hotărâri</DSButton>
          </>
        )}
        {access?.member && upcoming && !myMandate && (
          <DSButton variant="ghost" icon={Handshake} onClick={() => setDlg("mandate")} data-testid="radacini-meeting-mandate-btn">Dau mandat</DSButton>
        )}
        {myMandate && upcoming && <DSButton variant="ghost" icon={Plus} onClick={() => revoke(myMandate)} data-testid="radacini-meeting-mandate-revoke">Revocă mandatul</DSButton>}
      </div>

      {dlg === "convene" && <ConveneDialog m={m} minDays={minDays} onClose={() => setDlg(null)} onDone={done} />}
      {dlg === "attendance" && <AttendanceDialog m={m} assocId={assoc.id} onClose={() => setDlg(null)} onDone={done} />}
      {dlg === "decisions" && <DecisionsDialog m={m} onClose={() => setDlg(null)} onDone={done} />}
      {dlg === "mandate" && <MandateDialog m={m} onClose={() => setDlg(null)} onDone={done} />}
      {confirmDialog}
    </div>
  );
}

function ConveneDialog({ m, minDays, onClose, onDone }) {
  const [doc, setDoc] = useState("");
  const [busy, setBusy] = useState(false);
  const left = daysUntil(m.date);
  const submit = async () => {
    setBusy(true);
    try {
      const body = {};
      if (doc.trim()) body.registered_mail_document_id = doc.trim();
      const r = await meetingConvene(m.id, body);
      if (r?.warning) toast.warning(r.warning);
      toast.success("Convocarea a fost trimisă");
      onDone();
    } catch (e) { toast.error(errMsg(e, "Nu am putut trimite convocarea")); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-meeting-convene-dialog">
        <DialogHeader><DialogTitle>Convocare</DialogTitle><DialogDescription>Se notifică toți membrii activi și confirmați.</DialogDescription></DialogHeader>
        {left != null && left < minDays && <p className="text-sm text-amber-700 bg-amber-50 rounded p-2">Rămân doar {left} zile până la ședință, sub termenul de {minDays} zile.</p>}
        <Field label="ID document dovadă scrisoare recomandată" htmlFor="c-doc" hint="Încarcă mai întâi dovada în fila Documente, apoi lipește ID-ul. Opțional.">
          <Input id="c-doc" value={doc} onChange={(e) => setDoc(e.target.value)} data-testid="radacini-meeting-convene-doc" />
        </Field>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton onClick={submit} disabled={busy} data-testid="radacini-meeting-convene-submit">{busy ? "Se trimite…" : "Trimite convocarea"}</DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AttendanceDialog({ m, assocId, onClose, onDone }) {
  const [members, setMembers] = useState(null);
  const [present, setPresent] = useState(new Set(m.present_member_ids || []));
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    assocMembers(assocId).then((r) => setMembers(Array.isArray(r) ? r : r?.items || r?.members || [])).catch((e) => { toast.error(errMsg(e, "Nu am putut încărca registrul")); setMembers([]); });
  }, [assocId]);
  const toggle = (id) => setPresent((p) => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const list = (members || []).filter((x) => !q || `${x.name} ${x.code}`.toLowerCase().includes(q.toLowerCase()));
  const submit = async () => {
    setBusy(true);
    try {
      const r = await meetingAttendance(m.id, { present_member_ids: [...present], mandates_ids: (m.mandates || []).map((x) => x.id) });
      toast.success(r?.held_without_quorum ? "Prezență salvată: ședință fără cvorum" : "Prezență salvată");
      onDone();
    } catch (e) { toast.error(errMsg(e, "Nu am putut salva prezența")); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-meeting-attendance-dialog" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>Prezență</DialogTitle><DialogDescription>Bifează membrii prezenți. Mandatele înregistrate ({(m.mandates || []).length}) se iau în calcul automat.</DialogDescription></DialogHeader>
        <Input placeholder="Caută după nume sau cod" value={q} onChange={(e) => setQ(e.target.value)} />
        {members === null && <p className="text-sm text-slate-500">Se încarcă…</p>}
        <ul className="max-h-72 overflow-y-auto space-y-1">
          {list.map((x) => (
            <li key={x.id}>
              <label className="flex items-center gap-2 text-sm py-1 cursor-pointer">
                <input type="checkbox" checked={present.has(x.id)} onChange={() => toggle(x.id)} data-testid={`radacini-attendance-${x.id}`} />
                <span className="min-w-0 break-words">{x.name} <span className="text-xs text-slate-500">({x.code} · {fmtShare(x.shares)} cote)</span></span>
              </label>
            </li>
          ))}
        </ul>
        <p className="text-xs text-slate-500">{present.size} prezenți</p>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton onClick={submit} disabled={busy} data-testid="radacini-meeting-attendance-submit">{busy ? "Se salvează…" : "Salvează"}</DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DecisionsDialog({ m, onClose, onDone }) {
  const blank = () => ({ title: "", result_text: "", votes_for: "", votes_against: "", abstentions: "" });
  const [rows, setRows] = useState((m.agenda || []).length ? m.agenda.map((a) => ({ ...blank(), title: a.title })) : [blank()]);
  const [minutes, setMinutes] = useState("");
  const [busy, setBusy] = useState(false);
  const upd = (i, k, v) => setRows((r) => r.map((x, j) => (j === i ? { ...x, [k]: v } : x)));
  const num = (v) => (v === "" ? undefined : Number(v));
  const submit = async () => {
    const decisions = rows.filter((r) => r.title.trim() && r.result_text.trim()).map((r) => ({
      title: r.title.trim(), result_text: r.result_text.trim(), votes_for: num(r.votes_for), votes_against: num(r.votes_against), abstentions: num(r.abstentions),
    }));
    if (!decisions.length) return toast.error("Completează cel puțin o hotărâre (titlu și rezultat).");
    if (!minutes.trim()) return toast.error("Adaugă ID-ul documentului cu procesul-verbal.");
    setBusy(true);
    try {
      await meetingDecisions(m.id, { decisions, minutes_document_id: minutes.trim() });
      toast.success("Hotărârile au fost consemnate");
      onDone();
    } catch (e) { toast.error(errMsg(e, "Nu am putut salva hotărârile")); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-meeting-decisions-dialog" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>Hotărâri și proces-verbal</DialogTitle><DialogDescription>Se calculează automat termenul de contestare.</DialogDescription></DialogHeader>
        {rows.map((r, i) => (
          <div key={i} className="rounded border border-slate-200 dark:border-slate-700 p-2 space-y-2">
            <Input placeholder="Titlu" value={r.title} onChange={(e) => upd(i, "title", e.target.value)} />
            <Textarea placeholder="Rezultat (ce s-a hotărât)" rows={2} value={r.result_text} onChange={(e) => upd(i, "result_text", e.target.value)} />
            <div className="grid grid-cols-3 gap-2">
              <Input type="number" min="0" placeholder="Pentru" value={r.votes_for} onChange={(e) => upd(i, "votes_for", e.target.value)} />
              <Input type="number" min="0" placeholder="Împotrivă" value={r.votes_against} onChange={(e) => upd(i, "votes_against", e.target.value)} />
              <Input type="number" min="0" placeholder="Abțineri" value={r.abstentions} onChange={(e) => upd(i, "abstentions", e.target.value)} />
            </div>
          </div>
        ))}
        <DSButton variant="ghost" icon={Plus} onClick={() => setRows((r) => [...r, blank()])}>Adaugă hotărâre</DSButton>
        <Field label="ID document proces-verbal" htmlFor="d-min" hint="Încarcă PV-ul în fila Documente (tip PV AGA / PV CA).">
          <Input id="d-min" value={minutes} onChange={(e) => setMinutes(e.target.value)} data-testid="radacini-meeting-minutes-doc" />
        </Field>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton onClick={submit} disabled={busy} data-testid="radacini-meeting-decisions-submit">{busy ? "Se salvează…" : "Consemnează"}</DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function MandateDialog({ m, onClose, onDone }) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!code.trim()) return toast.error("Introdu codul de membru al reprezentantului.");
    setBusy(true);
    try {
      await mandateCreate(m.id, { representative_member_code: code.trim(), representative_member_id: code.trim() });
      toast.success("Mandat înregistrat");
      onDone();
    } catch (e) { toast.error(errMsg(e, "Nu am putut înregistra mandatul")); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-mandate-dialog">
        <DialogHeader>
          <DialogTitle>Dau mandat</DialogTitle>
          <DialogDescription>Un alt membru te reprezintă la ședința din {fmtDate(m.date)}. Un reprezentant poate primi cel mult 5 mandate și 5% din cote.</DialogDescription>
        </DialogHeader>
        <Field label="Codul de membru al reprezentantului" htmlFor="mand-code" hint="Îl găsești la reprezentant, în fila „Cota mea”.">
          <Input id="mand-code" value={code} onChange={(e) => setCode(e.target.value)} data-testid="radacini-mandate-code" />
        </Field>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton onClick={submit} disabled={busy} data-testid="radacini-mandate-submit">{busy ? "Se salvează…" : "Dau mandat"}</DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
