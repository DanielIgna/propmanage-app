import React, { useEffect, useState } from "react";
import { useConfirm } from "../components/ConfirmDialog";
import DisputeButton from "../components/DisputeButton";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Ban, Check, ChevronDown, Copy, FileSignature, Pencil, Printer, Send, ShieldOff } from "lucide-react";
import { useAuth } from "../../../auth";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Checkbox } from "../../../components/ui/checkbox";
import { Label } from "../../../components/ui/label";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../../../components/ui/collapsible";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { Textarea } from "../../../components/ui/textarea";
import ProposalForm, { proposalToForm } from "../components/ProposalForm";
import { radaciniApi, errMsg } from "../api";
import { useMeta } from "../hooks";
import {
  Chips,
  fmtArea,
  fmtDateTime,
  fmtPeriod,
  fmtRon,
  labelOf,
  PageSkeleton,
  ROLE_LABEL,
  shortBrowser,
  signedFor,
  StatusBadge,
} from "../shared";

const LEGAL_FALLBACK =
  "Acest acord consemnează înțelegerea dintre părți în platforma Rădăcini. Nu înlocuiește contractul de arendă/închiriere în forma cerută de lege și nici înregistrarea acestuia la primărie, unde este cazul.";

const Row = ({ label, children }) => (
  <div className="flex flex-col sm:flex-row sm:gap-4 py-2 border-b border-slate-100 dark:border-white/5 last:border-0">
    <dt className="sm:w-40 shrink-0 text-sm font-semibold text-slate-500 dark:text-slate-400">{label}</dt>
    <dd className="text-sm text-slate-800 dark:text-slate-200 min-w-0">{children}</dd>
  </div>
);

// Din corpul formularului păstrăm doar termenii schimbați față de versiunea curentă
// (altfel serverul revalidează câmpuri neatinse, ex. data de început devenită între timp trecută).
const changedTerms = (body, cur = {}) => {
  const same = (k, v) => {
    const prev = cur[k];
    if (k === "start_date" || k === "end_date") return String(prev || "").slice(0, 10) === v;
    if (k === "crops") return JSON.stringify(prev || []) === JSON.stringify(v || []);
    if (k === "custom_clauses") return (prev || "") === (v || "");
    return (prev ?? null) === (v ?? null);
  };
  return Object.fromEntries(Object.entries(body).filter(([k, v]) => !same(k, v)));
};

// Termenii unei versiuni (curentă sau din istoric).
function TermsDetails({ terms = {}, modelLabel }) {
  return (
    <dl>
      <Row label="Model">{modelLabel || "—"}</Row>
      <Row label="Suprafață">{terms.area_m2 != null ? fmtArea(terms.area_m2) : "—"}</Row>
      <Row label="Perioadă">{terms.start_date ? fmtPeriod(terms.start_date, terms.end_date) : "—"}</Row>
      {terms.price_ron_per_year != null && <Row label="Preț">{fmtRon(terms.price_ron_per_year)}</Row>}
      {terms.harvest_share_percent != null && <Row label="Parte din recoltă">{`${terms.harvest_share_percent}%`}</Row>}
      <Row label="Culturi">{terms.crops?.length ? <Chips items={terms.crops} /> : "Nespecificate"}</Row>
      {terms.custom_clauses && (
        <Row label="Clauze suplimentare">
          <span className="whitespace-pre-line break-words">{terms.custom_clauses}</span>
        </Row>
      )}
    </dl>
  );
}

export default function AcordDetaliu() {
  const [confirm, confirmDialog] = useConfirm();
  const { id } = useParams();
  const { user } = useAuth();
  const { meta } = useMeta();
  const [data, setData] = useState({ loading: true, error: null, agreement: null });
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [signOpen, setSignOpen] = useState(false);
  const [agree, setAgree] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  useEffect(() => {
    let alive = true;
    radaciniApi
      .agreement(id)
      .then((agreement) => alive && setData({ loading: false, error: null, agreement }))
      .catch((e) => alive && setData((s) => ({ ...s, loading: false, error: e })));
    return () => {
      alive = false;
    };
  }, [id, tick]);

  const refresh = () => setTick((t) => t + 1);
  const { loading, error, agreement: a } = data;

  const back = (
    <Link to="/radacini/acorduri" className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline print:hidden">
      <ArrowLeft className="w-4 h-4" /> Înapoi la acorduri
    </Link>
  );

  if (loading) return <PageSkeleton />;
  if (error || !a) {
    return (
      <div className="space-y-4">
        {back}
        <EmptyState icon={FileSignature} title="Acordul nu există sau nu ai acces" hint={error ? errMsg(error) : undefined} testid="radacini-acord-negasit" />
      </div>
    );
  }

  // Părțile acționează; personalul și super-adminul doar citesc (403 la acțiuni).
  const parties = a.parties || [];
  const partyIds = a.party_ids || parties.map((p) => p.user_id);
  const isParty = !!user && partyIds.includes(user.id);
  const isDraft = a.status === "draft";
  const isOpen = a.status === "draft" || a.status === "proposed";
  const canEdit = isParty && isOpen;
  const canPropose = isParty && isDraft;
  const canSign = isParty && a.status === "proposed" && !signedFor(a, user.id);
  const canCancel = isParty && isOpen;
  const modelLabel = labelOf(meta?.offer_models, a.model);
  const snap = a.terms?.parcel_snapshot || {};
  const history = a.versions_history || [];
  const legal = a.legal_notice || LEGAL_FALLBACK;

  const copyHash = async () => {
    try {
      await navigator.clipboard.writeText(a.terms_hash);
      toast.success("Amprenta a fost copiată");
    } catch {
      toast.error("Nu am putut copia amprenta");
    }
  };

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

  const propose = async () => {
    if (!(await confirm({ title: "Trimiți acordul spre semnare?", description: "Termenii rămân înghețați până la semnare. Orice modificare ulterioară creează o versiune nouă.", confirmLabel: "Trimite spre semnare" }))) return;
    run(() => radaciniApi.proposeAgreement(id), "Acordul a fost trimis spre semnare");
  };

  const saveTerms = (body) => {
    const changes = changedTerms(body, a.terms);
    if (!Object.keys(changes).length) {
      toast.info("Nu ai modificat niciun termen.");
      setEditOpen(false);
      return;
    }
    run(() => radaciniApi.updateAgreement(id, changes), "Termenii au fost salvați. Versiunea a fost actualizată.", () => setEditOpen(false));
  };

  const sign = () =>
    run(
      () => radaciniApi.signAgreement(id, a.version),
      `Ai semnat versiunea ${a.version}`,
      () => {
        setSignOpen(false);
        setAgree(false);
      }
    );

  const cancel = () =>
    run(
      () => radaciniApi.cancelAgreement(id, cancelReason.trim()),
      "Acordul a fost anulat",
      () => {
        setCancelOpen(false);
        setCancelReason("");
      }
    );

  return (
    <div className="space-y-5 max-w-5xl print:max-w-none" data-testid="radacini-acord-detaliu">
      {confirmDialog}
      {back}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white break-words print:text-black">{snap.title || "Acord de colaborare"}</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 print:text-slate-700">
            {snap.locality ? `${snap.locality} · ` : ""}Versiunea {a.version}
            {a.signed_at ? ` · Semnat la ${fmtDateTime(a.signed_at)}` : ""}
          </p>
          {a.terms_hash && (
            <p className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 print:text-slate-700" data-testid="radacini-acord-hash">
              Amprentă termeni:
              <code className="font-mono text-slate-700 dark:text-slate-200 print:text-black" title={a.terms_hash}>
                {String(a.terms_hash).slice(0, 12)}
              </code>
              <button
                type="button"
                onClick={copyHash}
                aria-label="Copiază amprenta termenilor"
                title="Copiază amprenta completă"
                className="print:hidden rounded p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10 hover:text-slate-800 dark:hover:text-white"
                data-testid="radacini-acord-hash-copy"
              >
                <Copy className="w-3.5 h-3.5" />
              </button>
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2 print:hidden">
          <StatusBadge status={a.status} testid="radacini-acord-status" />
          {isParty && a.status === "signed" && <DisputeButton scopeType="agreement" scopeId={a.id} testid="radacini-acord-disputa" />}
        </div>
      </div>

      {a.status === "cancelled" && (
        <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-slate-100 dark:bg-white/5 p-4 text-sm text-slate-600 dark:text-slate-300">
          Acordul a fost anulat.
          {a.cancel_reason && <span> Motiv: {a.cancel_reason}</span>}
        </div>
      )}
      {user && !isParty && (
        <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111213] p-4 text-sm text-slate-600 dark:text-slate-300 print:hidden">
          Vizualizare de personal. Nu poți acționa în acest acord.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <section className={`${CARD} p-5 print:shadow-none print:border-slate-400`} data-testid="radacini-acord-termeni">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-2 print:text-black">Termenii versiunii {a.version}</h3>
            <TermsDetails terms={a.terms} modelLabel={modelLabel} />
          </section>

          <aside
            className="rounded-2xl border-2 border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-500/10 p-5 print:bg-white print:border-black"
            data-testid="radacini-nota-legala"
          >
            <p className="text-sm font-bold text-amber-800 dark:text-amber-200 mb-1 print:text-black">Notă legală</p>
            <p className="text-sm text-amber-900 dark:text-amber-100 whitespace-pre-line print:text-black">{legal}</p>
          </aside>

          <section className={`${CARD} p-5 space-y-3 print:shadow-none print:border-slate-400`} data-testid="radacini-semnaturi">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white print:text-black">Părți și semnături</h3>
            <ul className="space-y-2">
              {parties.map((p) => {
                const sig = (a.signatures || []).find((s) => s.user_id === p.user_id && s.version === a.version);
                return (
                  <li key={p.user_id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 dark:border-white/10 px-3 py-2.5 text-sm">
                    <div className="min-w-0">
                      <p className="font-semibold text-slate-800 dark:text-slate-100">{p.name || "—"}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{ROLE_LABEL[p.role] || p.role}</p>
                    </div>
                    {sig ? (
                      <div className="text-right">
                        <span className="text-xs font-bold text-emerald-700 dark:text-emerald-300">Semnat la {fmtDateTime(sig.signed_at)}</span>
                        {sig.user_id === user?.id && sig.ip && (
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 print:text-slate-700" data-testid="radacini-semnatura-detalii">
                            semnat de pe {sig.ip}
                            {sig.user_agent ? ` · ${shortBrowser(sig.user_agent)}` : ""}
                          </p>
                        )}
                      </div>
                    ) : (
                      <span className="text-xs font-bold text-slate-500 dark:text-slate-400">
                        {a.status === "proposed" ? "Nesemnat" : "Nesemnat (ciornă)"}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>

          {history.length > 0 && (
            <Collapsible className={`${CARD} p-5 print:hidden`} data-testid="radacini-versiuni">
              <CollapsibleTrigger className="w-full flex items-center justify-between gap-2 text-left" data-testid="radacini-versiuni-toggle">
                <span className="text-sm font-bold text-slate-900 dark:text-white">Istoricul versiunilor ({history.length})</span>
                <ChevronDown className="w-4 h-4 text-slate-500 transition-transform [&[data-state=open]]:rotate-180" />
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-4 space-y-3">
                {history.map((h) => (
                  <div key={h.version} className="rounded-xl border border-slate-200 dark:border-white/10 p-3">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
                      Versiunea {h.version} · {h.by_user_id === user?.id ? "de tine" : "de cealaltă parte"} · {fmtDateTime(h.at)}
                    </p>
                    <TermsDetails terms={h.terms} modelLabel={modelLabel} />
                  </div>
                ))}
              </CollapsibleContent>
            </Collapsible>
          )}
        </div>

        <div className="space-y-4 order-first lg:order-none print:hidden">
          <section className={`${CARD} p-5 space-y-3`} data-testid="radacini-acord-actiuni">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Acțiuni</h3>
            <div className="flex flex-col gap-2">
              {canEdit && (
                <DSButton variant="secondary" icon={Pencil} disabled={busy} onClick={() => setEditOpen(true)} className="justify-center" data-testid="radacini-btn-editeaza">
                  Editează termenii
                </DSButton>
              )}
              {canPropose && (
                <DSButton variant="primary" icon={Send} disabled={busy} onClick={propose} className="justify-center" data-testid="radacini-btn-trimite-semnare">
                  Trimite spre semnare
                </DSButton>
              )}
              {canSign && (
                <DSButton variant="success" icon={Check} disabled={busy} onClick={() => setSignOpen(true)} className="justify-center" data-testid="radacini-btn-semneaza">
                  Semnează
                </DSButton>
              )}
              {canCancel && (
                <DSButton variant="danger" icon={Ban} disabled={busy} onClick={() => setCancelOpen(true)} className="justify-center" data-testid="radacini-btn-anuleaza">
                  Anulează
                </DSButton>
              )}
              <DSButton variant="ghost" icon={Printer} onClick={() => window.print()} className="justify-center" data-testid="radacini-btn-tipareste">
                Tipărește
              </DSButton>
            </div>
            {!isParty && user && <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5"><ShieldOff className="w-3.5 h-3.5" /> Nu ai acțiuni pe acest acord.</p>}
            {a.status === "proposed" && isParty && (
              <p className="text-xs text-slate-500 dark:text-slate-400">Dacă modifici termenii, se creează o versiune nouă și semnăturile date până acum se anulează.</p>
            )}
          </section>
        </div>
      </div>

      {/* Editare termeni: modelul rămâne fix, notele nu se aplică acordului. */}
      <Dialog open={editOpen} onOpenChange={(open) => !busy && setEditOpen(open)}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="radacini-edit-dialog">
          <DialogHeader>
            <DialogTitle>Editează termenii</DialogTitle>
            <DialogDescription>Orice modificare creează o versiune nouă. Semnăturile existente se resetează.</DialogDescription>
          </DialogHeader>
          {editOpen && (
            <ProposalForm
              idPrefix="acord"
              testidPrefix="radacini-acord-form"
              lockedModel={a.model}
              areaMax={snap.area_m2}
              initial={proposalToForm(a.terms, a.model)}
              showNote={false}
              showClauses
              nullBlank
              submitLabel="Salvează termenii"
              submitting={busy}
              onSubmit={saveTerms}
              onCancel={() => setEditOpen(false)}
            />
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={signOpen} onOpenChange={(open) => !busy && setSignOpen(open)}>
        <DialogContent data-testid="radacini-sign-dialog">
          <DialogHeader>
            <DialogTitle>Semnează acordul</DialogTitle>
            <DialogDescription>
              Semnezi versiunea {a.version}. Când toate părțile semnează aceeași versiune, acordul devine semnat.
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-start gap-3 rounded-xl border border-slate-200 dark:border-white/10 p-3">
            <Checkbox id="acord-agree" checked={agree} onCheckedChange={(v) => setAgree(!!v)} data-testid="radacini-sign-agree" />
            <Label htmlFor="acord-agree" className="text-sm leading-snug text-slate-700 dark:text-slate-200 cursor-pointer">
              Am citit și sunt de acord cu versiunea {a.version}.
            </Label>
          </div>
          <DialogFooter>
            <DSButton variant="secondary" onClick={() => setSignOpen(false)}>
              Anulează
            </DSButton>
            <DSButton variant="success" disabled={!agree || busy} onClick={sign} data-testid="radacini-sign-confirm">
              Semnează
            </DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={cancelOpen} onOpenChange={(open) => !busy && setCancelOpen(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Anulezi acordul?</DialogTitle>
            <DialogDescription>Cererea rămâne acceptată, iar terenul nu se schimbă. Motivul este opțional.</DialogDescription>
          </DialogHeader>
          <Textarea
            rows={3}
            maxLength={500}
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
            placeholder="ex. nu suntem de acord cu perioada propusă."
            data-testid="radacini-cancel-reason"
          />
          <DialogFooter>
            <DSButton variant="secondary" onClick={() => setCancelOpen(false)}>
              Înapoi
            </DSButton>
            <DSButton variant="danger" disabled={busy} onClick={cancel} data-testid="radacini-cancel-confirm">
              Anulează acordul
            </DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
