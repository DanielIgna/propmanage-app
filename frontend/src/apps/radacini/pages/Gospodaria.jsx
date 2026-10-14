import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Home, Trash2, UserPlus } from "lucide-react";
import { useAuth } from "../../../auth";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Checkbox } from "../../../components/ui/checkbox";
import { Input } from "../../../components/ui/input";
import { useConfirm } from "../components/ConfirmDialog";
import { errMsg } from "../api";
import { s6aApi } from "../api_s6a";
import { Field, PageHeader, PageSkeleton } from "../shared";

export const MINOR_CONSENT_TEXT =
  "Sunt părintele/tutorele legal și sunt de acord cu prelucrarea prenumelui și anului nașterii minorului în Rădăcini.";

const EMPTY = { kind: "adult", email: "", name: "", relation: "", birth_year: "", consent: false };

export default function Gospodaria() {
  const { user } = useAuth();
  const [confirm, confirmDialog] = useConfirm();
  const [state, setState] = useState({ loading: true, household: null, invitations: [], error: null });
  const [name, setName] = useState("");
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    s6aApi
      .myHousehold()
      .then((d) => setState({ loading: false, household: d?.household ?? null, invitations: d?.invitations || (d?.invitation ? [d.invitation] : []), error: null }))
      .catch((error) => setState({ loading: false, household: null, invitations: [], error }));
  }, []);
  useEffect(load, [load]);

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

  if (state.loading) return <PageSkeleton />;
  const h = state.household;

  const add = async (e) => {
    e.preventDefault();
    let body;
    if (form.kind === "adult") {
      if (!form.email.trim()) return toast.error("Introdu emailul adultului (are deja cont).");
      body = { email: form.email.trim(), relation: form.relation.trim(), is_minor: false };
    } else {
      const year = Number(form.birth_year);
      if (!form.name.trim()) return toast.error("Introdu prenumele minorului.");
      if (!year || year < 2000 || year > new Date().getFullYear()) return toast.error("Anul nașterii nu este valid.");
      if (!form.consent) return toast.error("Bifează consimțământul părintelui/tutorelui.");
      body = { name: form.name.trim(), relation: form.relation.trim(), is_minor: true, birth_year: year, parental_consent: true };
    }
    if (await run(() => s6aApi.addHouseholdMember(h.id, body), "Membru adăugat", "Nu am putut adăuga membrul")) setForm(EMPTY);
  };

  const remove = async (m, idx) => {
    if (!(await confirm({ title: "Elimini membrul?", description: `${m.name} va fi scos din gospodărie.`, confirmLabel: "Elimină", danger: true }))) return;
    run(() => s6aApi.removeHouseholdMember(h.id, m.user_id || idx), "Membru eliminat", "Nu am putut elimina membrul");
  };

  return (
    <div className="space-y-5 max-w-3xl" data-testid="radacini-gospodaria">
      {confirmDialog}
      <PageHeader title="Gospodăria mea" subtitle="Cont familial: adulți cu cont și copii (doar prenume și an de naștere)." />

      {state.invitations.map((inv) => (
        <div key={inv.id} className={`${CARD} p-4 flex flex-wrap items-center justify-between gap-3`} data-testid={`radacini-gospodarie-invitatie-${inv.id}`}>
          <p className="text-sm text-slate-800 dark:text-slate-100">Ai fost invitat în gospodăria „{inv.name}”.</p>
          <DSButton disabled={busy} onClick={() => run(() => s6aApi.acceptHousehold(inv.id), "Invitație acceptată", "Nu am putut accepta")}>
            Acceptă
          </DSButton>
        </div>
      ))}

      {state.error && <EmptyState icon={Home} title="Nu am putut încărca gospodăria" hint={errMsg(state.error)} />}

      {!state.error && !h && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim().length < 2) return toast.error("Dă un nume gospodăriei.");
            run(() => s6aApi.createHousehold({ name: name.trim() }), "Gospodărie creată", "Nu am putut crea gospodăria");
          }}
          className={`${CARD} p-5 space-y-4`}
          data-testid="radacini-gospodarie-creeaza"
        >
          <Field label="Numele gospodăriei" htmlFor="gosp-nume">
            <Input id="gosp-nume" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} placeholder="ex. Familia Pop" />
          </Field>
          <div className="flex justify-end">
            <DSButton type="submit" disabled={busy} icon={Home}>
              Creează gospodăria
            </DSButton>
          </div>
        </form>
      )}

      {h && (
        <>
          <section className={`${CARD} p-5 space-y-3`}>
            <h3 className="text-base font-bold text-slate-900 dark:text-white break-words">{h.name}</h3>
            <ul className="divide-y divide-slate-100 dark:divide-white/5" data-testid="radacini-gospodarie-membri">
              {(h.members || []).map((m, i) => (
                <li key={m.user_id || `${m.name}-${i}`} className="py-2.5 flex flex-wrap items-center justify-between gap-2 text-sm">
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-800 dark:text-slate-100 break-words">
                      {m.name}
                      {m.user_id === user?.id ? " (tu)" : ""}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {m.relation || "—"}
                      {m.is_minor ? ` · minor${m.birth_year ? `, născut în ${m.birth_year}` : ""}` : ""}
                      {m.status === "invited" || m.status === "pending" ? " · invitație trimisă" : ""}
                    </p>
                  </div>
                  {m.user_id !== user?.id && h.owner_user_id === user?.id && (
                    <DSButton variant="ghost" icon={Trash2} disabled={busy} onClick={() => remove(m, i)} data-testid={`radacini-gospodarie-elimina-${i}`}>
                      Elimină
                    </DSButton>
                  )}
                </li>
              ))}
            </ul>
          </section>

          {h.owner_user_id === user?.id && (
            <form onSubmit={add} className={`${CARD} p-5 space-y-4`} data-testid="radacini-gospodarie-adauga">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">Adaugă un membru</h3>
              <div className="flex gap-2">
                {[["adult", "Adult (cu cont)"], ["minor", "Minor"]].map(([k, l]) => (
                  <DSButton key={k} type="button" variant={form.kind === k ? "primary" : "secondary"} onClick={() => setForm({ ...EMPTY, kind: k })} data-testid={`radacini-gospodarie-tip-${k}`}>
                    {l}
                  </DSButton>
                ))}
              </div>
              {form.kind === "adult" ? (
                <Field label="Email" htmlFor="gosp-email" hint="Persoana primește o invitație pe care trebuie să o accepte.">
                  <Input id="gosp-email" type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
                </Field>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Prenume" htmlFor="gosp-prenume">
                    <Input id="gosp-prenume" value={form.name} maxLength={40} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
                  </Field>
                  <Field label="Anul nașterii" htmlFor="gosp-an">
                    <Input id="gosp-an" type="number" value={form.birth_year} onChange={(e) => setForm((f) => ({ ...f, birth_year: e.target.value }))} />
                  </Field>
                </div>
              )}
              <Field label="Relația" htmlFor="gosp-rel" hint="ex. soț/soție, fiu, fiică">
                <Input id="gosp-rel" value={form.relation} maxLength={40} onChange={(e) => setForm((f) => ({ ...f, relation: e.target.value }))} />
              </Field>
              {form.kind === "minor" && (
                <label htmlFor="gosp-consimt" className="flex items-start gap-2.5 rounded-xl border border-slate-200 dark:border-white/10 p-3 text-sm cursor-pointer">
                  <Checkbox id="gosp-consimt" checked={form.consent} onCheckedChange={(v) => setForm((f) => ({ ...f, consent: !!v }))} data-testid="radacini-gospodarie-consimtamant" />
                  <span className="text-slate-700 dark:text-slate-200">{MINOR_CONSENT_TEXT}</span>
                </label>
              )}
              <div className="flex justify-end">
                <DSButton type="submit" icon={UserPlus} disabled={busy || (form.kind === "minor" && !form.consent)} data-testid="radacini-gospodarie-adauga-btn">
                  Adaugă
                </DSButton>
              </div>
            </form>
          )}
        </>
      )}
    </div>
  );
}
