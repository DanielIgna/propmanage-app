// PropManage · House Health A→G — SURSĂ UNICĂ (SSOT) pentru cadrul narativ A→G.
//
// A→G este un FRAMEWORK NARATIV / DE ORIENTARE („harta casei"), NU un nou sistem
// de scoring. NU calculează niciun scor propriu, NU are backend/DB/endpoint propriu.
// Statusul fiecărui capitol este derivat EXCLUSIV din motoarele existente:
//   • Property Completeness (`GET /api/properties/{id}/completeness`) — 14 itemi reali
//   • Maturity L0–L5 / PVI (context, doar afișare)
// House Health, Completeness, Maturity, PVI, PTR rămân separate și neatinse.
//
// Statusuri permise (Regula 6): "lipsa" | "documentat" | "verificat" | "lipsa_date".
// Nu inventăm stări: dacă nu se poate determina din date, => "lipsa_date".

export const AXIS_DISCLAIMER =
  "PropManage House Health A→G este un cadru de produs pentru a explica și organiza " +
  "starea locuinței. Nu înlocuiește certificatul de performanță energetică, documentația " +
  "tehnică sau orice evaluare/diagnostic obligatoriu prin lege. Cadrul se inspiră din " +
  "Legea 372/2005 (modificată prin Legea 238/2024) și Directiva (UE) 2024/1275 (EPBD), " +
  "dar PropManage nu emite certificări legale.";

// Cele 7 capitole A→G. Fiecare mapează pe funcții EXISTENTE (target) + itemi reali din
// Completeness (items). `target` e interpretat de UI: "section:<hubSectionId>" sau
// "action:<actionName>" (openHealth / openTwin / openPropManager).
export const HOUSE_HEALTH_AXIS = [
  {
    code: "A",
    key: "identitate",
    title: "Identitatea locuinței",
    homepageVerb: "Identifică locuința",
    question: "Ce este casa mea?",
    why: "Fără o identitate clară — adresă, cadastru, act de proprietate — nimic altceva nu poate fi documentat corect.",
    evidence: "Act de proprietate, cadastru / carte funciară, atribute de bază.",
    nextHint: "Completează actele de identitate ale locuinței.",
    legal: "Cadastru & Carte funciară (RO); fundament pentru Cartea tehnică a construcției.",
    items: ["act_proprietate", "cadastru", "dna_attrs"],
    target: "section:rezumat",
  },
  {
    code: "B",
    key: "documentatie",
    title: "Documentație & Cartea Casei",
    homepageVerb: "Documentează casa",
    question: "Ce acte am și ce îmi lipsește?",
    why: "Documentele, planurile și facturile adunate într-un singur loc devin memoria permanentă a casei.",
    evidence: "Fotografii, plan / schiță tehnică, garanții & manuale, facturi & contracte.",
    nextHint: "Încarcă documentele importante în Cartea Casei.",
    legal: "Cartea tehnică a construcției (RO); documentare conform bunei practici.",
    items: ["foto", "plan_tehnic", "garantii_manuale", "facturi"],
    target: "section:carte",
  },
  {
    code: "C",
    key: "energie",
    title: "Performanță energetică",
    homepageVerb: "Înțelege performanța energetică",
    question: "Cât de eficientă energetic este casa?",
    why: "Performanța energetică influențează costurile, confortul termic și valoarea locuinței.",
    evidence: "Certificat de performanță energetică, analiză termică.",
    nextHint: "Adaugă certificatul energetic sau comandă o analiză termică.",
    legal: "Legea 372/2005 (mod. Legea 238/2024) + Directiva (UE) 2024/1275 — performanță energetică. DPE A–G (Franța) folosit doar ca exemplu internațional, nu ca echivalent legal.",
    items: ["certificat_energetic"],
    target: "action:openHealth",
  },
  {
    code: "D",
    key: "sanatate",
    title: "Sănătate & siguranță (mediu interior)",
    homepageVerb: "Verifică sănătatea și siguranța",
    question: "Este casa sigură și sănătoasă?",
    why: "Calitatea aerului, umiditatea, siguranța electrică și radonul afectează direct sănătatea celor care locuiesc.",
    evidence: "Scor House Health, raport de inspecție / audit tehnic.",
    nextHint: "Generează scorul House Health sau comandă o inspecție.",
    legal: "Directiva (UE) 2024/1275 — calitatea mediului interior; norme RO de siguranță electrică.",
    items: ["audit"],
    target: "action:openHealth",
  },
  {
    code: "E",
    key: "sisteme",
    title: "Sisteme, active & mentenanță",
    homepageVerb: "Cunoaște și întreține sistemele",
    question: "Ce echipamente am și când le întrețin?",
    why: "Instalațiile mapate și un jurnal de mentenanță previn avariile și prelungesc viața echipamentelor.",
    evidence: "Instalații/echipamente înregistrate, jurnal de mentenanță, garanții active.",
    nextHint: "Înregistrează instalațiile majore și pornește jurnalul de mentenanță.",
    legal: "Directiva (UE) 2024/1275 — sistemele tehnice ale clădirii.",
    items: ["assets", "maintenance", "warranty"],
    target: "section:twin",
  },
  {
    code: "F",
    key: "lucrari",
    title: "Riscuri, recomandări & lucrări",
    homepageVerb: "Rezolvă riscurile și lucrările",
    question: "Ce trebuie reparat și de către cine?",
    why: "Recomandările devin lucrări reale, executate de specialiști verificați, cu plata protejată prin escrow.",
    evidence: "Lucrări confirmate prin platformă, recomandări House Health.",
    nextHint: "Rezolvă o recomandare cerând ofertă de la un specialist verificat.",
    legal: "Directiva (UE) 2024/1275 — recomandări de renovare (analog pașaportului de renovare).",
    items: ["works"],
    target: "section:istoric",
  },
  {
    code: "G",
    key: "twin",
    title: "Digital Twin & Pașaport (rezultate)",
    homepageVerb: "Construiește memoria digitală a casei",
    question: "Cum arată progresul și cum îl pot arăta altora?",
    why: "Digital Twin-ul și pașaportul transformă tot ce ai documentat într-o memorie vie, ușor de partajat.",
    evidence: "Proiect Digital Twin, pașaportul proprietății, pregătire pentru tranzacție.",
    nextHint: "Pornește sau validează Digital Twin-ul casei.",
    legal: "Directiva (UE) 2024/1275 — pașaportul de renovare (folosit ca analog de produs).",
    items: ["twin"],
    target: "action:openTwin",
  },
];

export const STATE_META = {
  verificat: {
    label: "Verificat",
    tone: "emerald",
    hint: "Toate elementele acestui capitol sunt documentate în PropManage. Nu înlocuiește verificările legale sau diagnosticele obligatorii.",
  },
  documentat: {
    label: "Documentat",
    tone: "lime",
    hint: "Ai început să documentezi acest capitol — mai poți adăuga informații.",
  },
  lipsa: {
    label: "Lipsă",
    tone: "slate",
    hint: "Acest capitol nu are încă nimic documentat.",
  },
  lipsa_date: {
    label: "Lipsă date",
    tone: "amber",
    hint: "Nu putem determina încă starea din datele existente.",
  },
};

// Derivă starea unui capitol EXCLUSIV din răspunsul `completeness` (fără scor nou).
// completeness.items = [{ id, earned, max, done }]
export function deriveChapterState(chapter, completeness) {
  if (!completeness || !Array.isArray(completeness.items)) return "lipsa_date";
  const byId = {};
  completeness.items.forEach((i) => { byId[i.id] = i; });
  const present = chapter.items.filter((id) => byId[id]);
  if (present.length === 0) return "lipsa_date";
  let earned = 0;
  let max = 0;
  present.forEach((id) => { earned += byId[id].earned || 0; max += byId[id].max || 0; });
  if (earned <= 0) return "lipsa";
  if (max > 0 && earned >= max) return "verificat";
  return "documentat";
}

// Găsește capitolul de care aparține `next_step` din completeness (item id).
export function chapterForNextStep(completeness) {
  const id = completeness?.next_step?.id;
  if (!id) return null;
  return HOUSE_HEALTH_AXIS.find((c) => c.items.includes(id)) || null;
}
