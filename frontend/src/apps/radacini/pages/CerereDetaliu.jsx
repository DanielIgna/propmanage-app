import React, { useEffect, useState } from "react";
import { useConfirm } from "../components/ConfirmDialog";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Check, ChevronDown, FileSignature, Inbox, MessageSquare, Pencil, Send, Undo2, X } from "lucide-react";
import { useAuth } from "../../../auth";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../../../components/ui/collapsible";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { Textarea } from "../../../components/ui/textarea";
import ProposalForm, { proposalToForm } from "../components/ProposalForm";
import { radaciniApi, errMsg } from "../api";
import { useMeta } from "../hooks";
import {
  ACTIVE_REQUEST,
  Chips,
  fmtArea,
  fmtDateTime,
  fmtPeriod,
  fmtRon,
  labelOf,
  linkBtnCls,
  PageSkeleton,
  StatusBadge,
} from "../shared";

const Row = ({ label, children }) => (
  <div className="flex flex-col sm:flex-row sm:gap-4 py-2 border-b border-slate-100 dark:border-white/5 last:border-0">
    <dt className="sm:w-40 shrink-0 text-sm font-semibold text-slate-500 dark:text-slate-400">{label}</dt>
    <dd className="text-sm text-slate-800 dark:text-slate-200 min-w-0">{children}</dd>
  </div>
);

// Detaliile unei propuneri (cerere, contrapropunere din istoric).
function ProposalDetails({ proposal = {}, modelLabel }) {
  return (
    <dl>
      <Row label="Model">{modelLabel || "—"}</Row>
      <Row label="Suprafață">{proposal.area_m2 != null ? fmtArea(proposal.area_m2) : "—"}</Row>
      <Row label="Perioadă">{proposal.start_date ? fmtPeriod(proposal.start_date, proposal.end_date) : "—"}</Row>
      {proposal.price_ron_per_year != null && <Row label="Preț">{fmtRon(proposal.price_ron_per_year)}</Row>}
      {proposal.harvest_share_percent != null && <Row label="Parte din recoltă">{`${proposal.harvest_share_percent}%`}</Row>}
      <Row label="Culturi">{proposal.crops?.length ? <Chips items={proposal.crops} /> : "Nespecificate"}</Row>
      {proposal.note && (
        <Row label="Mesaj">
          <span className="whitespace-pre-line break-words">{proposal.note}</span>
        </Row>
      )}
    </dl>
  );
}

export default function CerereDetaliu() {
  const [confirm, confirmDialog] = useConfirm();
  const { id } = useParams();
  const { user } = useAuth();
  const { meta } = useMeta();
  const [data, setData] = useState({ loading: true, error: null, request: null, messages: [] });
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState("");
  const [declineOpen, setDeclineOpen] = useState(false);
  const [declineReason, setDeclineReason] = useState("");
  const [counterOpen, setCounterOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    radaciniApi
      .request(id)
      .then((d) => alive && setData({ loading: false, error: null, request: d.request, messages: d.messages || [] }))
      .catch((e) => alive && setData((s) => ({ ...s, loading: false, error: e })));
    return () => {
      alive = false;
    };
  }, [id, tick]);

  const refresh = () => setTick((t) => t + 1);
  const { loading, error, request, messages } = data;

  const back = (
    <Link to="/radacini/cereri" className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline">
      <ArrowLeft className="w-4 h-4" /> Înapoi la cereri
    </Link>
  );

  if (loading) return <PageSkeleton />;
  if (error || !request) {
    return (
      <div className="space-y-4">
        {back}
        <EmptyState icon={Inbox} title="Cererea nu există sau nu ai acces" hint={error ? errMsg(error) : undefined} testid="radacini-cerere-negasita" />
      </div>
    );
  }

  // Părțile acționează; personalul și super-adminul doar citesc.
  const isOwner = !!user && request.owner_user_id === user.id;
  const isRequester = !!user && request.requester_user_id === user.id;
  const isParty = isOwner || isRequester;
  const active = ACTIVE_REQUEST.includes(request.status);
  const canAct = isParty && active;
  // Proprietarul nu poate accepta propria contrapropunere: așteaptă răspunsul solicitantului.
  const awaitingRequester = isOwner && request.proposal_by_user_id === request.owner_user_id;
  const modelLabel = labelOf(meta?.offer_models, request.model);
  const history = request.proposals_history || [];

  const run = async (fn, okMsg, after) => {
    setBusy(true);
    try {
      await fn();
      toast.success(okMsg);
      after?.();
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Acțiunea nu a reușit"));
    } finally {
      setBusy(false);
    }
  };

  const accept = async () => {
    if (!(await confirm({ title: "Accepți cererea?", description: "Se creează acordul în ciornă, cu propunerea curentă.", confirmLabel: "Acceptă cererea" }))) return;
    run(() => radaciniApi.acceptRequest(id), "Cererea a fost acceptată. Acordul a fost creat în ciornă.");
  };

  const withdraw = async () => {
    if (!(await confirm({ title: "Retragi cererea?", description: "Proprietarul va fi anunțat. Poți trimite o cerere nouă ulterior.", confirmLabel: "Retrage cererea", danger: true }))) return;
    run(() => radaciniApi.withdrawRequest(id), "Cererea a fost retrasă");
  };

  const decline = () =>
    run(
      () => radaciniApi.declineRequest(id, declineReason.trim()),
      "Cererea a fost refuzată",
      () => {
        setDeclineOpen(false);
        setDeclineReason("");
      }
    );

  // Contrapropunerea nu schimbă modelul (vezi backend): formularul îl fixează și nu-l trimite.
  const counter = (body) =>
    run(() => radaciniApi.counterRequest(id, body), "Contrapropunerea a fost trimisă", () => setCounterOpen(false));

  const sendMessage = async () => {
    const t = text.trim();
    if (!t) return;
    setBusy(true);
    try {
      await radaciniApi.sendRequestMessage(id, t);
      setText("");
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Mesajul nu a fost trimis"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5 max-w-5xl" data-testid="radacini-cerere-detaliu">
      {confirmDialog}
      {back}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white break-words">{request.parcel_title || "Cerere de teren"}</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {request.parcel_locality ? `${request.parcel_locality} · ` : ""}
            {isOwner ? `Solicitant: ${request.requester_name || "—"}` : isRequester ? `Proprietar: ${request.owner_name || "—"}` : ""}
            {" · "}Ultima activitate: {fmtDateTime(request.last_activity_at)}
          </p>
        </div>
        <StatusBadge status={request.status} testid="radacini-cerere-status" />
      </div>

      {request.status === "declined" && request.decline_reason && (
        <div className="rounded-xl border border-rose-200 dark:border-rose-500/30 bg-rose-50 dark:bg-rose-500/10 p-4 text-sm text-rose-800 dark:text-rose-200">
          <span className="font-bold">Motiv: </span>
          {request.decline_reason}
        </div>
      )}
      {request.status === "expired" && (
        <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-slate-100 dark:bg-white/5 p-4 text-sm text-slate-600 dark:text-slate-300">
          Cererea a expirat după 30 de zile fără activitate.
        </div>
      )}
      {user && !isParty && (
        <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111213] p-4 text-sm text-slate-600 dark:text-slate-300">
          Vizualizare de personal. Nu poți acționa în această cerere.
        </div>
      )}
      {isParty && !active && (
        <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111213] p-4 text-sm text-slate-600 dark:text-slate-300">
          Cererea este închisă. Nu mai poți trimite mesaje sau propuneri.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <section className={`${CARD} p-5`} data-testid="radacini-propunere-curenta">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-2">Propunerea curentă</h3>
            {request.proposal_at && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">
                {request.proposal_by_user_id === user?.id ? "Trimisă de tine" : "Trimisă de cealaltă parte"} · {fmtDateTime(request.proposal_at)}
              </p>
            )}
            <ProposalDetails proposal={request.proposal} modelLabel={modelLabel} />
          </section>

          {history.length > 0 && (
            <Collapsible className={`${CARD} p-5`} data-testid="radacini-istoric">
              <CollapsibleTrigger className="w-full flex items-center justify-between gap-2 text-left" data-testid="radacini-istoric-toggle">
                <span className="text-sm font-bold text-slate-900 dark:text-white">Istoric propuneri ({history.length})</span>
                <ChevronDown className="w-4 h-4 text-slate-500 transition-transform [&[data-state=open]]:rotate-180" />
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-4 space-y-3">
                {history.map((h, i) => (
                  <div key={`${h.at}-${i}`} className="rounded-xl border border-slate-200 dark:border-white/10 p-3">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
                      {h.by_user_id === user?.id ? "Tu" : "Cealaltă parte"} · {fmtDateTime(h.at)}
                    </p>
                    <ProposalDetails proposal={h.proposal} modelLabel={modelLabel} />
                  </div>
                ))}
              </CollapsibleContent>
            </Collapsible>
          )}

          <section className={`${CARD} p-5 space-y-4`} data-testid="radacini-conversatie">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <MessageSquare className="w-4 h-4" /> Conversație
            </h3>
            {messages.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400" data-testid="radacini-mesaje-gol">
                Nu există mesaje încă.
              </p>
            ) : (
              <ol className="space-y-3" data-testid="radacini-mesaje">
                {messages.map((m) => {
                  const mine = !!user && (m.sender_user_id ?? m.author_user_id) === user.id;
                  return (
                    <li key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                      <div
                        className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${
                          mine
                            ? "bg-emerald-600 text-white"
                            : "bg-slate-100 dark:bg-white/10 text-slate-800 dark:text-slate-100"
                        }`}
                      >
                        <p className={`text-[11px] font-bold mb-0.5 ${mine ? "text-emerald-100" : "text-slate-500 dark:text-slate-400"}`}>
                          {mine ? "Tu" : m.sender_name || "Cealaltă parte"} · {fmtDateTime(m.created_at)}
                        </p>
                        <p className="whitespace-pre-line break-words">{m.text}</p>
                      </div>
                    </li>
                  );
                })}
              </ol>
            )}

            {canAct && (
              <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-white/5">
                <Textarea
                  rows={3}
                  maxLength={2000}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Scrie un mesaj…"
                  data-testid="radacini-mesaj-input"
                />
                <div className="flex justify-end">
                  <DSButton icon={Send} disabled={busy || !text.trim()} onClick={sendMessage} data-testid="radacini-mesaj-trimite">
                    Trimite mesajul
                  </DSButton>
                </div>
              </div>
            )}
          </section>
        </div>

        <div className="space-y-4 order-first lg:order-none">
          {canAct && (
            <section className={`${CARD} p-5 space-y-3`} data-testid="radacini-cerere-actiuni">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">Acțiuni</h3>
              <div className="flex flex-col gap-2">
                {isOwner && (
                  <>
                    {awaitingRequester ? (
                      <p className="rounded-xl bg-amber-50 dark:bg-amber-500/10 px-3 py-2 text-sm font-semibold text-amber-800 dark:text-amber-200" data-testid="radacini-asteapta-solicitant">
                        Așteaptă răspunsul solicitantului
                      </p>
                    ) : (
                      <DSButton variant="success" icon={Check} disabled={busy} onClick={accept} className="justify-center" data-testid="radacini-btn-accepta">
                        Acceptă
                      </DSButton>
                    )}
                    <DSButton variant="danger" icon={X} disabled={busy} onClick={() => setDeclineOpen(true)} className="justify-center" data-testid="radacini-btn-refuza">
                      Refuză
                    </DSButton>
                  </>
                )}
                <DSButton variant="secondary" icon={Pencil} disabled={busy} onClick={() => setCounterOpen(true)} className="justify-center" data-testid="radacini-btn-contrapropunere">
                  Contrapropunere
                </DSButton>
                {isRequester && (
                  <DSButton variant="ghost" icon={Undo2} disabled={busy} onClick={withdraw} className="justify-center" data-testid="radacini-btn-retrage">
                    Retrage cererea
                  </DSButton>
                )}
              </div>
              {isOwner && !awaitingRequester && (
                <p className="text-xs text-slate-500 dark:text-slate-400">Acceptarea creează acordul în ciornă, din propunerea curentă.</p>
              )}
            </section>
          )}

          {request.agreement_id && (
            <section className={`${CARD} p-5 space-y-3`} data-testid="radacini-cerere-acord">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">Acord</h3>
              <p className="text-sm text-slate-600 dark:text-slate-300">Cererea a fost acceptată. Termenii sunt în acord.</p>
              <Link to={`/radacini/acorduri/${request.agreement_id}`} className={linkBtnCls()} data-testid="radacini-link-acord">
                <FileSignature className="w-3.5 h-3.5" /> Vezi acordul
              </Link>
            </section>
          )}
        </div>
      </div>

      <Dialog open={declineOpen} onOpenChange={(open) => !busy && setDeclineOpen(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Refuzi cererea?</DialogTitle>
            <DialogDescription>Motivul este opțional. Solicitantul îl va primi prin notificare.</DialogDescription>
          </DialogHeader>
          <Textarea
            rows={4}
            maxLength={500}
            value={declineReason}
            onChange={(e) => setDeclineReason(e.target.value)}
            placeholder="ex. terenul este rezervat pentru altă perioadă."
            data-testid="radacini-decline-reason"
          />
          <DialogFooter>
            <DSButton variant="secondary" onClick={() => setDeclineOpen(false)}>
              Anulează
            </DSButton>
            <DSButton variant="danger" disabled={busy} onClick={decline} data-testid="radacini-decline-confirm">
              Refuză cererea
            </DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={counterOpen} onOpenChange={(open) => !busy && setCounterOpen(open)}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="radacini-contra-dialog">
          <DialogHeader>
            <DialogTitle>Contrapropunere</DialogTitle>
            <DialogDescription>Propune alte condiții. Propunerea curentă rămâne în istoric.</DialogDescription>
          </DialogHeader>
          {counterOpen && (
            <ProposalForm
              idPrefix="contra"
              testidPrefix="radacini-contra-form"
              lockedModel={request.model}
              areaMax={request.parcel_area_m2}
              initial={{ ...proposalToForm(request.proposal, request.model), note: "" }}
              submitLabel="Trimite contrapropunerea"
              submitting={busy}
              onSubmit={counter}
              onCancel={() => setCounterOpen(false)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
