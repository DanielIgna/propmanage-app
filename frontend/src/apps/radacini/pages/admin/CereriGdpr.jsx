import React, { useState } from "react";
import { toast } from "sonner";
import { Check, ShieldAlert, X } from "lucide-react";
import { CARD, DSButton, EmptyState } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Textarea } from "../../../../components/ui/textarea";
import { errMsg, radaciniApi } from "../../api";
import { fmtDateTime, SelectField, StatusPill } from "../../shared";
import { clean, deletionStatusDef, ErrorBox, isOpenDeletion, TabSkeleton, usePaged } from "./adminShared";

const FILTERS = [
  { id: "pending", label: "Deschise" },
  { id: "done", label: "Finalizate" },
  { id: "rejected", label: "Respinse" },
  { id: "all", label: "Toate" },
];
const PAGE = 50;
const NOTE_MIN = 3; // obligatorie doar la respingere
const NOTE_MAX = 500;

const DECISIONS = [
  { id: "done", label: "Datele au fost șterse", icon: Check, hint: "Marchează cererea ca finalizată." },
  { id: "rejected", label: "Resping cererea", icon: X, hint: "Utilizatorul primește motivul." },
];

export default function CereriGdpr() {
  const [filter, setFilter] = useState("pending");
  const { rows, loading, loadingMore, error, moreError, hasMore, loadMore, reload } = usePaged(
    (skip) => radaciniApi.adminDeletionRequests(clean({ status: filter, skip: skip || "", limit: PAGE })),
    [filter],
    { pageSize: PAGE }
  );

  const [resolving, setResolving] = useState(null);
  const [decision, setDecision] = useState("done");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const trimmed = note.trim();
  // Nota e opțională la „finalizată” și obligatorie (minimum 3 caractere) la „respinsă”.
  const valid = trimmed.length <= NOTE_MAX && (decision === "done" || trimmed.length >= NOTE_MIN);

  const openDialog = (r) => {
    setResolving(r);
    setDecision("done");
    setNote("");
  };

  const resolve = async () => {
    if (!resolving || !valid) return;
    setBusy(true);
    try {
      await radaciniApi.adminResolveDeletion(resolving.id, decision, trimmed || undefined);
      toast.success(decision === "done" ? "Cerere marcată ca finalizată" : "Cerere respinsă");
      setResolving(null);
      reload();
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut salva decizia"));
    } finally {
      setBusy(false);
    }
  };

  if (loading && rows.length === 0 && !error) return <TabSkeleton />;
  if (error) return <ErrorBox title="Nu am putut încărca cererile GDPR" error={error} onRetry={reload} testid="radacini-admin-gdpr-error" />;

  return (
    <div className="space-y-4" data-testid="radacini-admin-gdpr">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <p className="text-sm text-slate-600 dark:text-slate-300 max-w-xl">
          În pilot, ștergerea datelor se face manual. Aici marchezi cererea ca rezolvată sau respinsă, iar utilizatorul este notificat.
        </p>
        <div className="w-full sm:w-44">
          <SelectField value={filter} onValueChange={setFilter} options={FILTERS} testid="radacini-admin-gdpr-filter" />
        </div>
      </div>

      {rows.length === 0 ? (
        <div className={CARD}>
          <EmptyState
            icon={ShieldAlert}
            title={filter === "pending" ? "Nicio cerere deschisă" : "Nicio cerere pentru acest filtru"}
            hint="Cererile apar când un membru cere ștergerea datelor din Setări."
            testid="radacini-admin-gdpr-empty"
          />
        </div>
      ) : (
        <ul className="grid grid-cols-1 lg:grid-cols-2 gap-3" data-testid="radacini-admin-gdpr-list">
          {rows.map((r) => {
            const open = isOpenDeletion(r.status);
            const who = r.user_name || r.user_email || (r.user_id ? `Utilizator ${String(r.user_id).slice(0, 8)}` : "Utilizator");
            return (
              <li key={r.id} className={`${CARD} p-4 space-y-2`} data-testid={`radacini-admin-gdpr-${r.id}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-bold text-slate-900 dark:text-white break-words">{who}</p>
                    {r.user_email && r.user_email !== who && <p className="text-sm text-slate-500 dark:text-slate-400 break-all">{r.user_email}</p>}
                  </div>
                  <StatusPill def={deletionStatusDef(r.status)} testid={`radacini-admin-gdpr-status-${r.id}`} />
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Cerută {fmtDateTime(r.at)}
                  {r.resolved_at ? ` · rezolvată ${fmtDateTime(r.resolved_at)}${r.resolved_by_name ? ` de ${r.resolved_by_name.split(/\s+/)[0]}` : ""}` : ""}
                </p>
                {r.resolution_note && (
                  <p className="text-sm text-slate-700 dark:text-slate-200 whitespace-pre-line">
                    <span className="font-semibold">Notă: </span>
                    {r.resolution_note}
                  </p>
                )}
                {open && (
                  <div className="pt-1">
                    <DSButton variant="primary" onClick={() => openDialog(r)} data-testid={`radacini-admin-gdpr-resolve-${r.id}`}>
                      Rezolvă cererea
                    </DSButton>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {moreError && (
        <p className="text-sm text-rose-600 dark:text-rose-400" role="alert">
          Nu am putut încărca cererile următoare.
        </p>
      )}
      {hasMore && (
        <div className="flex justify-center">
          <DSButton variant="secondary" disabled={loadingMore} onClick={loadMore} data-testid="radacini-admin-gdpr-more">
            {loadingMore ? "Se încarcă…" : "Încarcă mai multe"}
          </DSButton>
        </div>
      )}

      <Dialog open={!!resolving} onOpenChange={(open) => !open && !busy && setResolving(null)}>
        <DialogContent data-testid="radacini-admin-gdpr-dialog">
          <DialogHeader>
            <DialogTitle>Rezolvi cererea de ștergere?</DialogTitle>
            <DialogDescription>
              Ștergerea efectivă a datelor se face manual. Alege rezultatul și notează ce s-a făcut: nota intră în jurnalul de audit.
            </DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2" role="radiogroup" aria-label="Decizie">
            {DECISIONS.map((d) => {
              const on = decision === d.id;
              return (
                <button
                  key={d.id}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  onClick={() => setDecision(d.id)}
                  className={`flex items-start gap-2 rounded-xl border px-3 py-2.5 text-left text-sm transition-colors ${
                    on
                      ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10"
                      : "border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5"
                  }`}
                  data-testid={`radacini-admin-gdpr-decision-${d.id}`}
                >
                  <d.icon className="w-4 h-4 mt-0.5 shrink-0" aria-hidden="true" />
                  <span>
                    <span className="block font-semibold text-slate-900 dark:text-white">{d.label}</span>
                    <span className="block text-xs text-slate-500 dark:text-slate-400">{d.hint}</span>
                  </span>
                </button>
              );
            })}
          </div>
          <div className="space-y-1.5">
            <Textarea
              rows={4}
              maxLength={NOTE_MAX}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder={decision === "done" ? "ex. datele au fost șterse manual din toate colecțiile Rădăcini (opțional)." : "ex. contul are acorduri semnate active."}
              aria-label="Nota deciziei"
              data-testid="radacini-admin-gdpr-note"
            />
            <p className={`text-xs ${!valid && (trimmed.length > 0 || decision === "rejected") ? "text-rose-600 dark:text-rose-400" : "text-slate-500 dark:text-slate-400"}`}>
              {trimmed.length}/{NOTE_MAX} · {decision === "done" ? "notă opțională" : `motiv obligatoriu, minimum ${NOTE_MIN} caractere`}
            </p>
          </div>
          <DialogFooter>
            <DSButton variant="secondary" disabled={busy} onClick={() => setResolving(null)} data-testid="radacini-admin-gdpr-cancel">
              Renunță
            </DSButton>
            <DSButton
              variant={decision === "done" ? "success" : "danger"}
              disabled={!valid || busy}
              onClick={resolve}
              data-testid="radacini-admin-gdpr-confirm"
            >
              {busy ? "Se salvează…" : decision === "done" ? "Marchează finalizată" : "Respinge cererea"}
            </DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
