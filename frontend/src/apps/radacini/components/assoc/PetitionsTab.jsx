import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { PenLine, Plus, Reply } from "lucide-react";
import { DSButton } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";
import { errMsg } from "../../api";
import { canManage, petitionCreate, petitionRespond, petitionSign, petitionsList } from "../../api_s9";
import { Field, SelectField, fmtDate } from "../../shared";

const KINDS = [
  { id: "extraordinary_aga", label: "Convocarea unei AGA extraordinare" },
  { id: "agenda_item", label: "Punct pe ordinea de zi" },
];
const kindLabel = (k) => KINDS.find((x) => x.id === k)?.label || k;
const pctOf = (v, t) => (t > 0 ? Math.min(100, Math.round((v / t) * 100)) : 0);

function Bar({ label, value, threshold, testid }) {
  const p = Math.round((value || 0) * 100);
  const t = Math.round((threshold || 0) * 100);
  return (
    <div data-testid={testid}>
      <p className="text-xs text-slate-600 dark:text-slate-300">{label}: {p}% (prag {t}%)</p>
      <div className="relative h-2.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
        <div className={`h-full ${p >= t ? "bg-emerald-500" : "bg-sky-500"}`} style={{ width: `${Math.min(100, p)}%` }} />
        <div className="absolute top-0 bottom-0 w-0.5 bg-slate-800" style={{ left: `${Math.min(100, t)}%` }} />
      </div>
    </div>
  );
}

export default function PetitionsTab({ assoc, access, reload }) {
  const assocId = assoc?.id;
  const council = canManage(access);
  const [list, setList] = useState(null);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [respond, setRespond] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const rules = assoc?.rules?.extraordinary_petition || { members_fraction: 0.25, shares_fraction: 0.25 };

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await petitionsList(assocId);
      setList(Array.isArray(r) ? r : r?.items || r?.petitions || []);
    } catch (e) {
      setError(errMsg(e, "Nu am putut încărca petițiile"));
      setList([]);
    }
  }, [assocId]);
  useEffect(() => { if (assocId) load(); }, [assocId, load]);

  const sign = async (p) => {
    setBusyId(p.id);
    try { await petitionSign(p.id); toast.success("Ai semnat petiția"); await load(); reload?.(); }
    catch (e) { toast.error(errMsg(e, "Nu am putut înregistra semnătura")); }
    finally { setBusyId(null); }
  };

  return (
    <div className="space-y-4" data-testid="radacini-petitions-tab">
      <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-3 text-sm space-y-1" data-testid="radacini-petitions-explain">
        <p className="font-semibold">Cum funcționează o petiție</p>
        <p>Pentru o AGA extraordinară e nevoie de semnăturile a 1/4 dintre membri <em>sau</em> a 1/4 din cote. Când pragul e atins, consiliul are 10 zile să răspundă.</p>
        <p>Pentru un punct pe ordinea de zi sunt suficiente semnăturile a 1/10 dintre membri, cu cel puțin 5 zile înainte de ședință.</p>
      </div>
      {access?.member && (
        <div className="flex justify-end">
          <DSButton icon={Plus} onClick={() => setCreateOpen(true)} data-testid="radacini-petition-create-btn">Petiție nouă</DSButton>
        </div>
      )}
      {list === null && <p className="text-sm text-slate-500" data-testid="radacini-petitions-loading">Se încarcă…</p>}
      {error && <p className="text-sm text-red-600" data-testid="radacini-petitions-error">{error}</p>}
      {list && !list.length && !error && <p className="text-sm text-slate-500" data-testid="radacini-petitions-empty">Nu există petiții.</p>}
      <ul className="space-y-3">
        {(list || []).map((p) => {
          const s = p.signatures || {};
          const th = p.threshold || (p.kind === "agenda_item" ? assoc?.rules?.agenda_petition : rules) || {};
          const mFrac = s.members_fraction ?? pctOf(p.signatures_count ?? s.members ?? s.members_count ?? 0, p.members_count ?? s.total_members ?? assoc?.members_count ?? 0) / 100;
          const shFrac = s.shares_fraction ?? pctOf(p.signed_shares ?? s.shares ?? 0, p.total_shares ?? s.total_shares ?? assoc?.total_shares ?? 0) / 100;
          return (
            <li key={p.id} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 space-y-2" data-testid={`radacini-petition-${p.id}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-xs text-slate-500">{kindLabel(p.kind)} · {fmtDate(p.created_at)}</p>
                  <p className="font-semibold break-words">{p.title}</p>
                </div>
                {p.threshold_met && <span className="rounded-full bg-emerald-100 text-emerald-800 px-2 py-0.5 text-xs font-bold">Prag atins</span>}
              </div>
              {p.text && <p className="text-sm break-words">{p.text}</p>}
              <Bar label="Membri" value={mFrac} threshold={th.members_fraction} testid={`radacini-petition-members-${p.id}`} />
              {p.kind !== "agenda_item" && <Bar label="Cote" value={shFrac} threshold={th.shares_fraction} testid={`radacini-petition-shares-${p.id}`} />}
              {p.response_due_at && !p.response && <p className="text-xs text-amber-700">Răspuns datorat până la {fmtDate(p.response_due_at)}</p>}
              {p.response && <p className="text-sm rounded bg-emerald-50 dark:bg-emerald-950/30 p-2"><strong>Răspunsul CA:</strong> {p.response.text || p.response}</p>}
              <div className="flex flex-wrap gap-2">
                {access?.member && !p.signed_by_me && (
                  <DSButton icon={PenLine} onClick={() => sign(p)} disabled={busyId === p.id} data-testid={`radacini-petition-sign-${p.id}`}>Semnez</DSButton>
                )}
                {p.signed_by_me && <span className="text-sm text-emerald-700">Ai semnat</span>}
                {council && !p.response && <DSButton variant="secondary" icon={Reply} onClick={() => setRespond(p)} data-testid={`radacini-petition-respond-${p.id}`}>Răspunde</DSButton>}
              </div>
            </li>
          );
        })}
      </ul>
      {createOpen && <CreateDialog assocId={assocId} onClose={() => setCreateOpen(false)} onDone={() => { setCreateOpen(false); load(); }} />}
      {respond && <RespondDialog p={respond} onClose={() => setRespond(null)} onDone={() => { setRespond(null); load(); }} />}
    </div>
  );
}

function CreateDialog({ assocId, onClose, onDone }) {
  const [f, setF] = useState({ kind: "extraordinary_aga", title: "", text: "", meeting_id: "" });
  const [busy, setBusy] = useState(false);
  const set = (k) => (v) => setF((p) => ({ ...p, [k]: v }));
  const submit = async () => {
    if (!f.title.trim() || !f.text.trim()) return toast.error("Completează titlul și textul petiției.");
    const body = { kind: f.kind, title: f.title.trim(), text: f.text.trim() };
    if (f.kind === "agenda_item" && f.meeting_id.trim()) body.meeting_id = f.meeting_id.trim();
    setBusy(true);
    try { await petitionCreate(assocId, body); toast.success("Petiția a fost depusă"); onDone(); }
    catch (e) { toast.error(errMsg(e, "Nu am putut depune petiția")); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-petition-create-dialog">
        <DialogHeader><DialogTitle>Petiție nouă</DialogTitle><DialogDescription>Ceilalți membri o pot semna până la atingerea pragului.</DialogDescription></DialogHeader>
        <div className="space-y-3">
          <Field label="Tip" htmlFor="p-kind"><SelectField id="p-kind" value={f.kind} onValueChange={set("kind")} options={KINDS} testid="radacini-petition-kind" /></Field>
          <Field label="Titlu" htmlFor="p-title"><Input id="p-title" value={f.title} onChange={(e) => set("title")(e.target.value)} data-testid="radacini-petition-title" /></Field>
          <Field label="Text" htmlFor="p-text"><Textarea id="p-text" rows={4} value={f.text} onChange={(e) => set("text")(e.target.value)} data-testid="radacini-petition-text" /></Field>
          {f.kind === "agenda_item" && <Field label="ID ședință" htmlFor="p-m" hint="Ședința la care vrei să se adauge punctul."><Input id="p-m" value={f.meeting_id} onChange={(e) => set("meeting_id")(e.target.value)} /></Field>}
        </div>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton onClick={submit} disabled={busy} data-testid="radacini-petition-create-submit">{busy ? "Se trimite…" : "Depune"}</DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RespondDialog({ p, onClose, onDone }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!text.trim()) return toast.error("Scrie răspunsul.");
    setBusy(true);
    try { await petitionRespond(p.id, { text: text.trim() }); toast.success("Răspuns trimis"); onDone(); }
    catch (e) { toast.error(errMsg(e, "Nu am putut trimite răspunsul")); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-petition-respond-dialog">
        <DialogHeader><DialogTitle>Răspuns la petiție</DialogTitle><DialogDescription className="break-words">{p.title}</DialogDescription></DialogHeader>
        <Textarea rows={5} value={text} onChange={(e) => setText(e.target.value)} data-testid="radacini-petition-respond-text" />
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton onClick={submit} disabled={busy} data-testid="radacini-petition-respond-submit">{busy ? "Se trimite…" : "Trimite"}</DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
