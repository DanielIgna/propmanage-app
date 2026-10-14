import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { CARD, DSButton, DSSkeleton } from "../../../design-system";
import { radaciniApi, errMsg } from "../api";
import { PageHeader } from "../shared";
import { useConfirm } from "../components/ConfirmDialog";
import { cachePersonas, impersonatePersona } from "../testAccounts";

// Ce poate deschide fiecare persoană după „Generează date demo”.
const SCENARIO = {
  proprietar: [
    "Cereri primite: 2 (una trimisă de Maria, una în negociere cu Elena, gata de acceptat)",
    "Terenuri: unul publicat, unul în verificare, o ciornă și unul cu acord semnat",
    "Acord semnat cu Maria și Proiectul din acesta (recoltă de confirmat: castraveți)",
    "Piață: anunțul tău de roșii (preț de referință)",
    "Comunități: coordonator în „Grădinarii din Florești” (anunț fixat, decizie în vot)",
  ],
  familie: [
    "Cereri trimise: una așteaptă răspuns, una acceptată",
    "Acord semnat și Proiect: culturi, calendar, contribuții și recolte",
    "Piață: anunțul tău de castraveți și o cerere de schimb pentru ouă",
    "Gospodăria mea: „Familia Ionescu” (Andrei adult, Ana minor cu consimțământ)",
    "Proiect → Necesar: semințe de fasole (promisiuni) · Lucrări: „Arat 1500 m²” cu oferta lui Vasile",
    "Comunitate: ai votat decizia despre ziua de lucru",
  ],
  producator: [
    "Piață: 3 anunțuri (roșii, ouă, miere) cu rezervări de confirmat",
    "Cereri primite: Andrei (refuzată) și un acord trimis spre semnare",
    "Teren propriu publicat (Solar Gilău) și o cerere în negociere la terenul lui Ion",
    "Dispute: parte într-o dispută în mediere (rezervarea de ouă cu Andrei)",
  ],
  consumator: [
    "Rezervări: una în așteptare, una confirmată, una ridicată și evaluată",
    "Acord de semnat cu Elena (semnarea e blocată în modul de impersonare)",
    "Participant în proiectul familiei: alocare de 10 kg de recoltă",
    "Dispute: ai deschis o dispută pe rezervarea de ouă (în mediere)",
    "Comunitate: poți vota decizia despre ziua de lucru · Necesar: promisiune de 0,5 kg de adus",
  ],
  operator: [
    "Operator: 1 teren în verificare (Teren arabil Gilău, 1 ha)",
    "Dispute: mediator pe disputa rezervării de ouă",
    "Prestator: arat, frezat, transport · ofertă de 300 RON pentru „Arat 1500 m²”",
  ],
  manager: ["Operator: 1 teren în verificare; vede toate localitățile și personalul"],
};

const COLLECTION_LABELS = {
  radacini_parcels: "terenuri",
  radacini_land_requests: "cereri",
  radacini_request_messages: "mesaje",
  radacini_agreements: "acorduri",
  radacini_projects: "proiecte",
  radacini_crop_plans: "culturi",
  radacini_activities: "activități",
  radacini_contributions: "contribuții",
  radacini_harvests: "recolte",
  radacini_allocations: "alocări",
  radacini_listings: "anunțuri",
  radacini_reservations: "rezervări",
  radacini_seller_stats: "statistici vânzător",
};

const summarize = (counts) =>
  Object.entries(counts || {})
    .filter(([, n]) => n > 0)
    .map(([k, n]) => `${n} ${COLLECTION_LABELS[k] || k}`)
    .join(", ");

export default function ConturiTest() {
  const [confirm, confirmDialog] = useConfirm();
  const [items, setItems] = useState(null);
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    try {
      const d = await radaciniApi.testAccounts();
      setItems(d.items);
      cachePersonas(d.items);
      return d.items;
    } catch (e) {
      toast.error(errMsg(e));
      setItems([]);
      return [];
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const ensure = async () => {
    setBusy("ensure");
    try {
      await radaciniApi.ensureTestAccounts();
      await load();
      toast.success("Conturile de test sunt gata");
    } catch (e) {
      toast.error(errMsg(e));
    }
    setBusy("");
  };

  const seed = async () => {
    setBusy("seed");
    try {
      const r = await radaciniApi.seedDemoScenario();
      await load();
      toast.success(`Date demo generate: ${summarize(r.counts)}`);
    } catch (e) {
      toast.error(errMsg(e));
    }
    setBusy("");
  };

  const reset = async () => {
    const ok = await confirm({
      title: "Resetezi datele demo?",
      description:
        "Se șterg doar datele generate de scenariul demo și ce s-a adăugat peste ele (cereri, proiecte, rezervări legate de acestea). Conturile de test rămân.",
      confirmLabel: "Resetează",
      danger: true,
    });
    if (!ok) return;
    setBusy("reset");
    try {
      const r = await radaciniApi.resetDemoScenario();
      await load();
      toast.success(r.total ? `Date demo șterse: ${summarize(r.counts)}` : "Nu existau date demo.");
    } catch (e) {
      toast.error(errMsg(e));
    }
    setBusy("");
  };

  const enter = async (p) => {
    setBusy(p.key);
    try {
      let persona = p;
      if (!p.user_id) {
        await radaciniApi.ensureTestAccounts();
        const fresh = await load();
        persona = fresh.find((x) => x.key === p.key);
        if (!persona?.user_id) throw new Error("Contul de test nu a putut fi creat.");
      }
      await impersonatePersona(persona);
    } catch (e) {
      toast.error(errMsg(e, e?.message));
      setBusy("");
    }
  };

  if (items === null) return <DSSkeleton kpis={0} blocks={2} />;

  return (
    <div className="space-y-4" data-testid="radacini-conturi-test">
      <PageHeader
        title="Conturi de test"
        subtitle="Intră în contul unui rol fictiv ca să încerci aplicația. Conturile nu au parolă; accesul se face doar prin impersonare, iar semnarea și acceptarea sunt blocate pentru siguranță."
      />
      <div className="flex flex-wrap gap-2">
        <DSButton onClick={ensure} disabled={!!busy} data-testid="radacini-test-ensure">
          Creează / actualizează conturile de test
        </DSButton>
        <DSButton onClick={seed} disabled={!!busy} data-testid="radacini-test-seed">
          Generează date demo
        </DSButton>
        <DSButton variant="secondary" onClick={reset} disabled={!!busy} data-testid="radacini-test-reset">
          Resetează datele demo
        </DSButton>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((p) => (
          <div key={p.key} className={`${CARD} p-4 flex flex-col gap-2`} data-testid={`radacini-test-card-${p.key}`}>
            <p className="font-bold text-slate-900 dark:text-white">{p.name}</p>
            <p className="text-sm text-emerald-700 dark:text-emerald-300">{p.label} · {p.locality}</p>
            <p className="text-sm text-slate-600 dark:text-slate-300 flex-1">{p.description}</p>
            {SCENARIO[p.key] && (
              <div className="text-sm text-slate-600 dark:text-slate-300" data-testid={`radacini-test-scenario-${p.key}`}>
                <p className="font-semibold text-slate-800 dark:text-slate-100">Ce găsești în scenariu</p>
                <ul className="list-disc pl-5 space-y-0.5">
                  {SCENARIO[p.key].map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              </div>
            )}
            {p.conflict && <p className="text-xs text-red-600">Emailul {p.email} există deja și nu e cont de test.</p>}
            <DSButton onClick={() => enter(p)} disabled={!!busy || p.conflict} data-testid={`radacini-test-enter-${p.key}`}>
              Intră ca {p.name}
            </DSButton>
          </div>
        ))}
      </div>
      {confirmDialog}
    </div>
  );
}
