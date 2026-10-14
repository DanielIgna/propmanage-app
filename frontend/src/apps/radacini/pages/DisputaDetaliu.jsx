import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Gavel, Send } from "lucide-react";
import { useAuth } from "../../../auth";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { Textarea } from "../../../components/ui/textarea";
import { errMsg } from "../api";
import { DISPUTE_SCOPE, s6aApi } from "../api_s6a";
import { useStaffMe } from "../hooks";
import { PageSkeleton, fmtDateTime } from "../shared";
import { DisputeBadge } from "./Dispute";

export default function DisputaDetaliu() {
  const { id } = useParams();
  const { user } = useAuth();
  const { staff } = useStaffMe();
  const [data, setData] = useState({ loading: true, error: null, dispute: null });
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [resolve, setResolve] = useState(null); // {status, note}

  const load = useCallback(() => {
    s6aApi
      .dispute(id)
      .then((d) => setData({ loading: false, error: null, dispute: d?.dispute ?? d }))
      .catch((error) => setData((s) => ({ ...s, loading: false, error })));
  }, [id]);
  useEffect(load, [load]);

  const back = (
    <Link to="/radacini/dispute" className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline">
      <ArrowLeft className="w-4 h-4" /> Înapoi la dispute
    </Link>
  );
  if (data.loading) return <PageSkeleton />;
  const d = data.dispute;
  if (data.error || !d) {
    return (
      <div className="space-y-4">
        {back}
        <EmptyState icon={Gavel} title="Disputa nu există sau nu ai acces" hint={data.error ? errMsg(data.error) : undefined} />
      </div>
    );
  }

  const isStaff = !!staff?.is_staff;
  const isMediator = d.mediator_user_id && d.mediator_user_id === user?.id;
  const isParty = [d.opened_by, d.against_user_id].includes(user?.id);
  const closed = d.status === "resolved" || d.status === "rejected";
  const canWrite = !closed && (isParty || isMediator);

  const run = async (fn, ok, fallback) => {
    setBusy(true);
    try {
      await fn();
      if (ok) toast.success(ok);
      load();
      return true;
    } catch (e) {
      toast.error(errMsg(e, fallback));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const send = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    if (await run(() => s6aApi.disputeMessage(id, text.trim()), null, "Nu am putut trimite mesajul")) setText("");
  };
  const doResolve = async () => {
    if (!resolve.note.trim()) return toast.error("Nota de rezoluție este obligatorie.");
    if (await run(() => s6aApi.resolveDispute(id, resolve.status, resolve.note.trim()), "Disputa a fost închisă", "Nu am putut închide disputa")) setResolve(null);
  };

  return (
    <div className="space-y-5 max-w-3xl" data-testid="radacini-disputa-detaliu">
      {back}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Dispută: {DISPUTE_SCOPE[d.scope_type] || d.scope_type}</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {d.locality ? `${d.locality} · ` : ""}deschisă {fmtDateTime(d.created_at)}
          </p>
        </div>
        <DisputeBadge status={d.status} testid="radacini-disputa-status" />
      </div>

      <section className={`${CARD} p-5 space-y-2`}>
        <h3 className="text-sm font-bold text-slate-900 dark:text-white">Motiv</h3>
        <p className="text-sm text-slate-700 dark:text-slate-200 whitespace-pre-line break-words">{d.reason}</p>
        {d.resolution && (
          <div className="mt-3 rounded-xl bg-slate-50 dark:bg-white/5 p-3 text-sm" data-testid="radacini-disputa-rezolutie">
            <p className="font-bold text-slate-900 dark:text-white">Rezoluție</p>
            <p className="text-slate-700 dark:text-slate-200 whitespace-pre-line break-words">{typeof d.resolution === "string" ? d.resolution : d.resolution.note}</p>
          </div>
        )}
      </section>

      {isStaff && !closed && (
        <section className={`${CARD} p-5 flex flex-wrap gap-2`}>
          {d.status === "open" && (
            <DSButton disabled={busy} onClick={() => run(() => s6aApi.takeDispute(id), "Ai preluat disputa", "Nu am putut prelua disputa")} data-testid="radacini-disputa-preia">
              Preia medierea
            </DSButton>
          )}
          {d.status === "in_mediation" && (isMediator || staff.role === "manager") && (
            <>
              <DSButton variant="success" onClick={() => setResolve({ status: "resolved", note: "" })} data-testid="radacini-disputa-rezolva">
                Marchează rezolvată
              </DSButton>
              <DSButton variant="danger" onClick={() => setResolve({ status: "rejected", note: "" })} data-testid="radacini-disputa-respinge">
                Respinge
              </DSButton>
            </>
          )}
        </section>
      )}

      <section className={`${CARD} p-5 space-y-3`}>
        <h3 className="text-sm font-bold text-slate-900 dark:text-white">Mesaje</h3>
        {(d.messages || []).length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">Niciun mesaj încă.</p>
        ) : (
          <ul className="space-y-2" data-testid="radacini-disputa-mesaje">
            {d.messages.map((m, i) => {
              const own = m.user_id === user?.id;
              const who = own ? "Tu" : m.user_id === d.mediator_user_id ? "Mediator" : m.name || "Cealaltă parte";
              return (
                <li key={i} className={`rounded-xl p-3 text-sm ${own ? "bg-emerald-50 dark:bg-emerald-500/10" : "bg-slate-50 dark:bg-white/5"}`}>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {who} · {fmtDateTime(m.at)}
                  </p>
                  <p className="text-slate-800 dark:text-slate-100 whitespace-pre-line break-words">{m.text}</p>
                </li>
              );
            })}
          </ul>
        )}
        {canWrite && (
          <form onSubmit={send} className="space-y-2">
            <Textarea rows={3} maxLength={1000} value={text} onChange={(e) => setText(e.target.value)} placeholder="Scrie un mesaj" data-testid="radacini-disputa-mesaj" />
            <div className="flex justify-end">
              <DSButton type="submit" icon={Send} disabled={busy || !text.trim()} data-testid="radacini-disputa-trimite">
                Trimite
              </DSButton>
            </div>
          </form>
        )}
      </section>

      <Dialog open={!!resolve} onOpenChange={(o) => !busy && !o && setResolve(null)}>
        <DialogContent data-testid="radacini-disputa-rezolva-dialog">
          <DialogHeader>
            <DialogTitle>{resolve?.status === "resolved" ? "Marchezi disputa ca rezolvată?" : "Respingi disputa?"}</DialogTitle>
            <DialogDescription>Nota este obligatorie și va fi vizibilă ambelor părți.</DialogDescription>
          </DialogHeader>
          <Textarea rows={4} maxLength={1000} value={resolve?.note || ""} onChange={(e) => setResolve((r) => ({ ...r, note: e.target.value }))} data-testid="radacini-disputa-nota" />
          <DialogFooter>
            <DSButton variant="secondary" onClick={() => setResolve(null)} disabled={busy}>
              Renunță
            </DSButton>
            <DSButton onClick={doResolve} disabled={busy || !resolve?.note?.trim()} data-testid="radacini-disputa-confirma">
              Confirmă
            </DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
