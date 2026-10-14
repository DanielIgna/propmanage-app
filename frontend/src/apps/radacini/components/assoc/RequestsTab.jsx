import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Reply } from "lucide-react";
import { DSButton } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";
import { errMsg } from "../../api";
import { canManage, requestAnswer, requestCreate, requestsList } from "../../api_s9";
import { Field, fmtDate } from "../../shared";

export default function RequestsTab({ assoc, access, reload }) {
  const assocId = assoc?.id;
  const council = canManage(access);
  const [list, setList] = useState(null);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [answer, setAnswer] = useState(null);
  const days = assoc?.rules?.info_request_days ?? 30;

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await requestsList(assocId);
      setList(Array.isArray(r) ? r : r?.items || r?.requests || []);
    } catch (e) {
      setError(errMsg(e, "Nu am putut încărca cererile"));
      setList([]);
    }
  }, [assocId]);
  useEffect(() => { if (assocId) load(); }, [assocId, load]);

  const isLate = (r) => r.overdue ?? (!r.answered_at && !r.answer && r.due_at && new Date(r.due_at) < new Date());

  return (
    <div className="space-y-4" data-testid="radacini-requests-tab">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate-600 dark:text-slate-300 min-w-0">
          Orice membru poate cere informații sau documente. Consiliul trebuie să răspundă în {days} de zile.
        </p>
        {access?.member && <DSButton icon={Plus} onClick={() => setCreateOpen(true)} data-testid="radacini-request-create-btn">Cerere nouă</DSButton>}
      </div>
      {list === null && <p className="text-sm text-slate-500" data-testid="radacini-requests-loading">Se încarcă…</p>}
      {error && <p className="text-sm text-red-600" data-testid="radacini-requests-error">{error}</p>}
      {list && !list.length && !error && <p className="text-sm text-slate-500" data-testid="radacini-requests-empty">Nu există cereri.</p>}
      <ul className="space-y-3">
        {(list || []).map((r) => {
          const late = isLate(r);
          const answered = !!(r.answered_at || r.answer);
          return (
            <li key={r.id} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 space-y-2" data-testid={`radacini-request-${r.id}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-semibold break-words">{r.subject}</p>
                  <p className="text-xs text-slate-500">{r.member_name ? `${r.member_name} · ` : ""}depusă {fmtDate(r.created_at)} · termen {fmtDate(r.due_at)}</p>
                </div>
                {late && <span className="rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs font-bold" data-testid={`radacini-request-late-${r.id}`}>întârziată</span>}
                {answered && <span className="rounded-full bg-emerald-100 text-emerald-800 px-2 py-0.5 text-xs font-bold">Răspuns primit</span>}
              </div>
              <p className="text-sm break-words whitespace-pre-line">{r.text}</p>
              {answered && (
                <p className="text-sm rounded bg-emerald-50 dark:bg-emerald-950/30 p-2 break-words">
                  <strong>Răspuns:</strong> {r.answer?.text || r.answer}
                  {r.answer?.document_id ? ` (document ${r.answer.document_id})` : ""}
                </p>
              )}
              {council && !answered && (
                <DSButton variant="secondary" icon={Reply} onClick={() => setAnswer(r)} data-testid={`radacini-request-answer-${r.id}`}>Răspunde</DSButton>
              )}
            </li>
          );
        })}
      </ul>
      {createOpen && <CreateDialog assocId={assocId} onClose={() => setCreateOpen(false)} onDone={() => { setCreateOpen(false); load(); reload?.(); }} />}
      {answer && <AnswerDialog r={answer} onClose={() => setAnswer(null)} onDone={() => { setAnswer(null); load(); reload?.(); }} />}
    </div>
  );
}

function CreateDialog({ assocId, onClose, onDone }) {
  const [subject, setSubject] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!subject.trim() || !text.trim()) return toast.error("Completează subiectul și cererea.");
    setBusy(true);
    try { await requestCreate(assocId, { subject: subject.trim(), text: text.trim() }); toast.success("Cererea a fost trimisă"); onDone(); }
    catch (e) { toast.error(errMsg(e, "Nu am putut trimite cererea")); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-request-create-dialog">
        <DialogHeader><DialogTitle>Cerere de informații</DialogTitle><DialogDescription>Întrebare sau cerere de document către consiliu.</DialogDescription></DialogHeader>
        <Field label="Subiect" htmlFor="r-sub"><Input id="r-sub" value={subject} onChange={(e) => setSubject(e.target.value)} data-testid="radacini-request-subject" /></Field>
        <Field label="Cererea ta" htmlFor="r-text"><Textarea id="r-text" rows={5} value={text} onChange={(e) => setText(e.target.value)} data-testid="radacini-request-text" /></Field>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton onClick={submit} disabled={busy} data-testid="radacini-request-create-submit">{busy ? "Se trimite…" : "Trimite"}</DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AnswerDialog({ r, onClose, onDone }) {
  const [text, setText] = useState("");
  const [doc, setDoc] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!text.trim()) return toast.error("Scrie răspunsul.");
    const body = { text: text.trim() };
    if (doc.trim()) body.document_id = doc.trim();
    setBusy(true);
    try { await requestAnswer(r.id, body); toast.success("Răspuns trimis"); onDone(); }
    catch (e) { toast.error(errMsg(e, "Nu am putut trimite răspunsul")); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-request-answer-dialog">
        <DialogHeader><DialogTitle>Răspuns</DialogTitle><DialogDescription className="break-words">{r.subject}</DialogDescription></DialogHeader>
        <Textarea rows={5} value={text} onChange={(e) => setText(e.target.value)} data-testid="radacini-request-answer-text" />
        <Field label="ID document atașat" htmlFor="a-doc" hint="Opțional."><Input id="a-doc" value={doc} onChange={(e) => setDoc(e.target.value)} /></Field>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton onClick={submit} disabled={busy} data-testid="radacini-request-answer-submit">{busy ? "Se trimite…" : "Trimite"}</DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
