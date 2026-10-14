import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { DSButton } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { useMember } from "../hooks";
import { errMsg } from "../api";
import { s8Api, ONBOARDING_OPEN_EVENT } from "../api_s8";
import { useTerms } from "./TermsGate";

const STEPS = ["terms", "profile", "discover", "notifications"];
const SKIP_KEY = "radacini_onboarding_skipped";
const readSkip = () => {
  try { return sessionStorage.getItem(SKIP_KEY) === "1"; } catch { return false; }
};
const writeSkip = (v) => {
  try { v ? sessionStorage.setItem(SKIP_KEY, "1") : sessionStorage.removeItem(SKIP_KEY); } catch { /* ignorat */ }
};

const LINKS = [
  ["/radacini/terenuri", "Vezi terenuri disponibile"],
  ["/radacini/piata", "Piața: produse și schimburi"],
  ["/radacini/proiecte", "Proiecte comune"],
  ["/radacini/comunitati", "Comunități din zona ta"],
];

export default function OnboardingGuide() {
  const { loading, member, refresh } = useMember();
  const { ensureTerms } = useTerms();
  const [open, setOpen] = useState(false);
  const [idx, setIdx] = useState(0);
  const [busy, setBusy] = useState(false);

  const done = !!member?.onboarding?.completed_at;
  useEffect(() => {
    if (!loading && !done && !readSkip()) setOpen(true);
  }, [loading, done]);
  useEffect(() => {
    const h = () => {
      writeSkip(false);
      setIdx(0);
      refresh();
      setOpen(true);
    };
    window.addEventListener(ONBOARDING_OPEN_EVENT, h);
    return () => window.removeEventListener(ONBOARDING_OPEN_EVENT, h);
  }, [refresh]);

  const mark = useCallback((step) => s8Api.onboardingStep(step).catch(() => {}), []);

  const skip = () => {
    writeSkip(true);
    setOpen(false);
  };
  const finish = async () => {
    setBusy(true);
    try {
      await s8Api.onboardingComplete();
      writeSkip(false);
      setOpen(false);
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut salva"));
    } finally {
      setBusy(false);
    }
  };
  const next = async () => {
    await mark(STEPS[idx]);
    if (idx >= STEPS.length - 1) return finish();
    setIdx(idx + 1);
  };

  const interests = member?.interests || [];
  const step = STEPS[idx];
  const titles = {
    terms: "1. Termenii Rădăcini",
    profile: "2. Interese și localitate",
    discover: "3. Ce poți face",
    notifications: "4. Notificări (opțional)",
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && skip()}>
      <DialogContent data-testid="radacini-onboarding">
        <DialogHeader>
          <DialogTitle>{titles[step]}</DialogTitle>
          <DialogDescription>Pasul {idx + 1} din {STEPS.length}. Poți sări peste ghid și îl reiei din Setări.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3 text-sm text-slate-700 dark:text-slate-300">
          {step === "terms" && (
            <>
              <p>Pentru acțiuni precum publicarea unui teren sau trimiterea unei cereri, trebuie să accepți termenii. Navigarea rămâne liberă.</p>
              <div className="flex flex-wrap gap-2">
                <DSButton variant="secondary" onClick={() => ensureTerms()} data-testid="radacini-onboarding-terms">Acceptă termenii</DSButton>
                <Link to="/radacini/termeni" target="_blank" className="self-center text-emerald-700 underline">Citește textul</Link>
              </div>
            </>
          )}
          {step === "profile" && (
            <>
              <p>Alege-ți interesele și localitatea, ca să-ți arătăm lucruri relevante.</p>
              {interests.length > 0 && <p className="text-xs text-slate-500">Interese curente: {interests.join(", ")}</p>}
              <Link to="/radacini/profil" onClick={() => setOpen(false)} className="text-emerald-700 underline" data-testid="radacini-onboarding-profil">Deschide profilul</Link>
            </>
          )}
          {step === "discover" && (
            <ul className="space-y-1">
              {LINKS.map(([to, label]) => (
                <li key={to}><Link to={to} onClick={() => setOpen(false)} className="text-emerald-700 underline">{label}</Link></li>
              ))}
            </ul>
          )}
          {step === "notifications" && <p>Vei primi notificări despre cereri, acorduri și anunțuri direct în aplicație. Pasul e opțional.</p>}
        </div>
        <DialogFooter>
          <DSButton variant="secondary" onClick={skip} data-testid="radacini-onboarding-skip">Sari peste</DSButton>
          {idx > 0 && <DSButton variant="secondary" onClick={() => setIdx(idx - 1)}>Înapoi</DSButton>}
          <DSButton disabled={busy} onClick={next} data-testid="radacini-onboarding-next">
            {idx >= STEPS.length - 1 ? "Gata" : "Continuă"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
