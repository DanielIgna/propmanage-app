import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Vote, X } from "lucide-react";
import { CARD, DSButton } from "../../../design-system";
import { Input } from "../../../components/ui/input";
import { useConfirm } from "./ConfirmDialog";
import { errMsg, asList } from "../api";
import { bucharestToIso, s6aApi } from "../api_s6a";
import { Field, fmtDateTime } from "../shared";

// Rezultate: array de numere, array de {option_index|index, count} sau obiect {index: count}. Returnează null dacă nu sunt livrate.
function resultCounts(d) {
  const r = d.results ?? d.tally ?? null;
  if (!r) return null;
  const n = (d.options || []).length;
  const out = Array(n).fill(0);
  if (Array.isArray(r)) {
    r.forEach((x, i) => {
      if (typeof x === "number") out[i] = x;
      else out[x.option_index ?? x.index ?? i] = x.count ?? x.votes ?? 0;
    });
  } else Object.entries(r).forEach(([k, v]) => (out[Number(k)] = Number(v) || 0));
  return out;
}

function DecisionCard({ d, canVote, canClose, onChanged }) {
  const [confirm, confirmDialog] = useConfirm();
  const [busy, setBusy] = useState(false);
  const open = d.status === "open";
  const myVote = d.my_vote ?? d.my_option_index ?? null;
  const voted = myVote != null || d.has_voted === true;
  const counts = resultCounts(d);
  const total = counts ? counts.reduce((a, b) => a + b, 0) : 0;

  const vote = async (i) => {
    if (!(await confirm({ title: "Confirmi votul?", description: `„${d.options[i]}”. Votul nu poate fi schimbat.`, confirmLabel: "Votează" }))) return;
    setBusy(true);
    try {
      await s6aApi.vote(d.id, i);
      toast.success("Votul a fost înregistrat");
      onChanged();
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut înregistra votul"));
    } finally {
      setBusy(false);
    }
  };
  const close = async () => {
    if (!(await confirm({ title: "Închizi votul?", description: "Rezultatele devin vizibile tuturor.", confirmLabel: "Închide" }))) return;
    setBusy(true);
    try {
      await s6aApi.closeDecision(d.id);
      onChanged();
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut închide votul"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className={`${CARD} p-4 space-y-3`} data-testid={`radacini-decizie-${d.id}`}>
      {confirmDialog}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="font-bold text-slate-900 dark:text-white break-words min-w-0">{d.question}</p>
        <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${open ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" : "bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300"}`}>
          {open ? "Deschis" : "Închis"}
        </span>
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">Se închide: {fmtDateTime(d.closes_at)}</p>
      <ul className="space-y-2">
        {(d.options || []).map((o, i) => {
          const pct = counts && total ? Math.round((counts[i] / total) * 100) : 0;
          return (
            <li key={i} className="space-y-1">
              <div className="flex items-center justify-between gap-2 text-sm">
                <span className={`break-words min-w-0 ${myVote === i ? "font-bold text-emerald-700 dark:text-emerald-300" : "text-slate-700 dark:text-slate-200"}`}>
                  {o}
                  {myVote === i ? " (votul tău)" : ""}
                </span>
                {open && canVote && !voted ? (
                  <DSButton variant="secondary" icon={Vote} disabled={busy} onClick={() => vote(i)} data-testid={`radacini-decizie-vot-${d.id}-${i}`}>
                    Votează
                  </DSButton>
                ) : counts ? (
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 whitespace-nowrap">
                    {counts[i]} ({pct}%)
                  </span>
                ) : null}
              </div>
              {counts && (open && canVote && !voted ? null : (
                <div className="h-1.5 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                  <div className="h-full bg-emerald-500" style={{ width: `${pct}%` }} />
                </div>
              ))}
            </li>
          );
        })}
      </ul>
      {!counts && open && <p className="text-xs text-slate-500 dark:text-slate-400">Rezultatele se văd după ce votezi sau după închidere.</p>}
      {open && canClose && (
        <div className="flex justify-end">
          <DSButton variant="ghost" icon={X} disabled={busy} onClick={close} data-testid={`radacini-decizie-inchide-${d.id}`}>
            Închide votul
          </DSButton>
        </div>
      )}
    </li>
  );
}

// scope: "community" | "project". canVote: membru activ. canCreate: coordonator.
export default function DecisionsPanel({ scope, scopeId, canVote = false, canCreate = false }) {
  const [state, setState] = useState({ loading: true, items: [], error: null });
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    s6aApi
      .decisions(scope, scopeId)
      .then((d) => setState({ loading: false, items: asList(d), error: null }))
      .catch((error) => setState({ loading: false, items: [], error }));
  }, [scope, scopeId]);
  useEffect(load, [load]);

  const setOpt = (i, v) => setForm((f) => ({ ...f, options: f.options.map((x, j) => (j === i ? v : x)) }));

  const create = async (e) => {
    e.preventDefault();
    const options = form.options.map((o) => o.trim()).filter(Boolean);
    if (form.question.trim().length < 5) return toast.error("Întrebarea are minim 5 caractere.");
    if (options.length < 2) return toast.error("Adaugă cel puțin 2 opțiuni.");
    if (!form.closes_at) return toast.error("Alege data închiderii.");
    setBusy(true);
    try {
      await s6aApi.createDecision({ scope, scope_id: scopeId, question: form.question.trim(), options, closes_at: bucharestToIso(form.closes_at) });
      toast.success("Votul a fost creat");
      setForm(null);
      load();
    } catch (err) {
      toast.error(errMsg(err, "Nu am putut crea votul"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="space-y-3" data-testid={`radacini-decizii-${scope}`}>
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white">Decizii și voturi</h3>
        {canCreate && !form && (
          <DSButton variant="secondary" icon={Plus} onClick={() => setForm({ question: "", options: ["", ""], closes_at: "" })} data-testid="radacini-decizie-nou">
            Vot nou
          </DSButton>
        )}
      </div>

      {form && (
        <form onSubmit={create} className={`${CARD} p-4 space-y-3`} data-testid="radacini-decizie-form">
          <Field label="Întrebare" htmlFor="dec-q">
            <Input id="dec-q" value={form.question} maxLength={200} onChange={(e) => setForm((f) => ({ ...f, question: e.target.value }))} />
          </Field>
          {form.options.map((o, i) => (
            <Field key={i} label={`Opțiunea ${i + 1}`} htmlFor={`dec-o${i}`}>
              <Input id={`dec-o${i}`} value={o} maxLength={80} onChange={(e) => setOpt(i, e.target.value)} />
            </Field>
          ))}
          {form.options.length < 6 && (
            <DSButton type="button" variant="ghost" icon={Plus} onClick={() => setForm((f) => ({ ...f, options: [...f.options, ""] }))}>
              Adaugă opțiune
            </DSButton>
          )}
          <Field label="Se închide la" htmlFor="dec-c" hint="Ora României (Europe/Bucharest).">
            <Input id="dec-c" type="datetime-local" value={form.closes_at} onChange={(e) => setForm((f) => ({ ...f, closes_at: e.target.value }))} />
          </Field>
          <div className="flex justify-end gap-2">
            <DSButton type="button" variant="secondary" onClick={() => setForm(null)}>
              Renunță
            </DSButton>
            <DSButton type="submit" disabled={busy} data-testid="radacini-decizie-salveaza">
              {busy ? "Se creează…" : "Creează votul"}
            </DSButton>
          </div>
        </form>
      )}

      {state.loading ? (
        <p className="text-sm text-slate-500">Se încarcă…</p>
      ) : state.error ? (
        <p className="text-sm text-rose-600">{errMsg(state.error, "Nu am putut încărca deciziile")}</p>
      ) : state.items.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400" data-testid="radacini-decizii-gol">Nicio decizie încă.</p>
      ) : (
        <ul className="space-y-3">
          {state.items.map((d) => (
            <DecisionCard key={d.id} d={d} canVote={canVote} canClose={canCreate} onChanged={load} />
          ))}
        </ul>
      )}
    </section>
  );
}
