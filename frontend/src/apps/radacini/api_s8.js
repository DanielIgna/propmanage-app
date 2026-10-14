// Wrappers API Rădăcini S8: termeni legali și onboarding (contract în docs/radacini/PLAN.md).
import { api } from "../../lib/api";

const data = (p) => p.then((r) => r.data);

export const s8Api = {
  legalDocuments: () => data(api.get("/radacini/legal/documents")),
  legalMe: () => data(api.get("/radacini/legal/me")),
  acceptLegal: (type, version) => data(api.post("/radacini/legal/accept", { type, version })),
  onboardingStep: (step) => data(api.post("/radacini/members/me/onboarding", { step })),
  onboardingComplete: () => data(api.post("/radacini/members/me/onboarding/complete")),
  onboardingReset: () => data(api.post("/radacini/members/me/onboarding/reset")),
};

export const ONBOARDING_OPEN_EVENT = "radacini:onboarding-open";

export const isTermsRequired = (e) =>
  e?.response?.status === 428 && e?.response?.data?.detail?.code === "terms_required";

// Dialogul de termeni se înregistrează aici (TermsGateProvider).
let asker = null;
export const setTermsAsker = (fn) => {
  asker = fn;
};
// Rezolvă true dacă termenii au fost acceptați, false dacă utilizatorul a renunțat.
export const askTerms = () => (asker ? asker() : Promise.resolve(false));

// Rulează fn; la 428 deschide dialogul, apoi reia o singură dată.
export async function withTerms(fn) {
  try {
    return await fn();
  } catch (e) {
    if (!isTermsRequired(e)) throw e;
    if (!(await askTerms())) throw e;
    return fn();
  }
}
