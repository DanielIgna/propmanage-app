// Wrappers API Rădăcini S9: Composesorate (contract în docs/radacini/PLAN.md, "S9 — contract").
// Rute sub /api/radacini/assoc. Singularele vin învelite ({association}, {member}, {claim}...), listele ca {items}.
import { api, BACKEND_URL } from "../../lib/api";

const data = (p) => p.then((r) => r.data);
const A = "/radacini/assoc";

// ── A. Asociații, registru, revendicări ─────────────────────────────────────
export const assocList = (params) => data(api.get(A, { params }));
export const assocGet = (id) => data(api.get(`${A}/${id}`));
export const assocCreate = (body) => data(api.post(A, body));
export const assocPatch = (id, body) => data(api.patch(`${A}/${id}`, body));
export const assocMe = (id) => data(api.get(`${A}/${id}/me`)); // {role, council_role, member, claims}
export const assocMembers = (id, params) => data(api.get(`${A}/${id}/members`, { params }));
export const assocMemberCreate = (id, body) => data(api.post(`${A}/${id}/members`, body));
export const assocMemberPatch = (id, mid, body) => data(api.patch(`${A}/${id}/members/${mid}`, body));
export const assocImport = (id, file) => {
  const fd = new FormData();
  fd.append("file", file);
  return data(api.post(`${A}/${id}/members/import`, fd)); // {imported, errors:[{line, error}]}
};
export const assocParticipation = (id) => data(api.get(`${A}/${id}/participation`));
export const claimCreate = (id, body) => data(api.post(`${A}/${id}/claims`, body));
export const claimsList = (id) => data(api.get(`${A}/${id}/claims`));
export const claimsMine = () => data(api.get(`${A}/claims/mine`));
export const claimDecide = (cid, body) => data(api.post(`${A}/claims/${cid}/decide`, body));

// ── B. Documente, ședințe, mandate, petiții, cereri ─────────────────────────
export const documentsList = (id, params) => data(api.get(`${A}/${id}/documents`, { params }));
// formData: type, title, date, visibility, replaces_id?, file
export const documentUpload = (id, formData) => data(api.post(`${A}/${id}/documents`, formData));
export const documentFileUrl = (did) => `${BACKEND_URL || ""}/api${A}/documents/${did}/file`;
export const documentAccessLog = (did) => data(api.get(`${A}/documents/${did}/access-log`));

export const meetingsList = (id) => data(api.get(`${A}/${id}/meetings`));
export const meetingGet = (mid) => data(api.get(`${A}/meetings/${mid}`));
export const meetingCreate = (id, body) => data(api.post(`${A}/${id}/meetings`, body));
export const meetingConvene = (mid, body = {}) => data(api.post(`${A}/meetings/${mid}/convene`, body));
export const meetingAck = (mid) => data(api.post(`${A}/meetings/${mid}/ack`));
export const meetingAttendance = (mid, body) => data(api.post(`${A}/meetings/${mid}/attendance`, body));
export const meetingDecisions = (mid, body) => data(api.post(`${A}/meetings/${mid}/decisions`, body));
export const mandateCreate = (mid, body) => data(api.post(`${A}/meetings/${mid}/mandates`, body));
export const mandateRevoke = (mandateId) => data(api.delete(`${A}/mandates/${mandateId}`));

export const petitionsList = (id) => data(api.get(`${A}/${id}/petitions`));
export const petitionCreate = (id, body) => data(api.post(`${A}/${id}/petitions`, body));
export const petitionSign = (pid) => data(api.post(`${A}/petitions/${pid}/sign`));
export const petitionRespond = (pid, body) => data(api.post(`${A}/petitions/${pid}/respond`, body));

export const requestsList = (id) => data(api.get(`${A}/${id}/requests`));
export const requestCreate = (id, body) => data(api.post(`${A}/${id}/requests`, body));
export const requestAnswer = (rid, body) => data(api.post(`${A}/requests/${rid}/answer`, body));

// ── C. Calendar, finanțe, transparență, jurnal, alerte ──────────────────────
export const obligations = (id, year) => data(api.get(`${A}/${id}/obligations`, { params: year ? { year } : undefined }));
export const obligationEvidence = (id, key, body) => data(api.post(`${A}/${id}/obligations/${encodeURIComponent(key)}/evidence`, body));
export const financeGet = (id) => data(api.get(`${A}/${id}/finance`));
export const financeYearCreate = (id, body) => data(api.post(`${A}/${id}/finance/years`, body));
export const financeDistribute = (id, year, body = {}) => data(api.post(`${A}/${id}/finance/years/${year}/distribute`, body));
export const distributionPaid = (distId) => data(api.post(`${A}/distributions/${distId}/paid`));
export const transparency = (id) => data(api.get(`${A}/${id}/transparency`));
export const audit = (id, params) => data(api.get(`${A}/${id}/audit`, { params }));
export const alertsMine = () => data(api.get(`${A}/alerts/mine`));
export const demoSeed = () => data(api.post(`${A}/demo/seed`));
export const demoReset = () => data(api.post(`${A}/demo/reset`));

// Încărcare dovezi pentru revendicări: contractul nu are rută dedicată; se folosește documentUpload (doar membri/CA).
export const claimEvidenceUpload = (id, formData) => documentUpload(id, formData);

// ── Etichete comune ─────────────────────────────────────────────────────────
export const MEMBER_STATUS = {
  unknown: { label: "Necunoscut", cls: "bg-slate-200 text-slate-700 dark:bg-white/15 dark:text-slate-200" },
  contacted: { label: "Contactat", cls: "bg-sky-100 text-sky-800 dark:bg-sky-500/20 dark:text-sky-200" },
  confirmed: { label: "Confirmat", cls: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-200" },
  active: { label: "Activ", cls: "bg-green-200 text-green-900 dark:bg-green-500/25 dark:text-green-100" },
  deceased: { label: "Decedat", cls: "bg-zinc-300 text-zinc-800 dark:bg-zinc-500/30 dark:text-zinc-100" },
  heir_pending: { label: "Moștenitor în curs", cls: "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-200" },
};
export const MEMBER_STATUS_OPTS = Object.entries(MEMBER_STATUS).map(([id, v]) => ({ id, label: v.label }));
export const COUNCIL_ROLE = {
  president: "Președinte",
  vice_president: "Vicepreședinte",
  secretary: "Secretar",
  cashier: "Casier",
  forest_pasture: "Responsabil silvic și pășuni",
  censor: "Cenzor",
};
export const ASSOC_TYPE = { composesorat: "Composesorat", obste: "Obște", pastoral: "Asociație pastorală" };
export const fmtShare = (v) => (v == null || v === "" ? "—" : Number(v).toLocaleString("ro-RO", { maximumFractionDigits: 4 }));
// Acces: CA / cenzor / operator / manager văd registrul.
export const canSeeRegistry = (access) =>
  !!access && (!!access.council_role || ["council", "censor", "operator", "manager", "admin", "super_admin"].includes(access.role));
export const canManage = (access) =>
  !!access && (["council", "manager", "admin", "super_admin", "operator"].includes(access.role) || (!!access.council_role && access.council_role !== "censor"));

// Obiect agregat (compatibilitate cu componentele care folosesc s9Api.<nume>).
export const s9Api = {
  assocList, assocGet, assocCreate, assocPatch, assocMe, assocMembers, assocMemberCreate, assocMemberPatch, assocImport,
  assocParticipation, claimCreate, claimsList, claimsMine, claimDecide, documentsList, documentUpload, documentFileUrl,
  documentAccessLog, meetingsList, meetingGet, meetingCreate, meetingConvene, meetingAck, meetingAttendance,
  meetingDecisions, mandateCreate, mandateRevoke, petitionsList, petitionCreate, petitionSign, petitionRespond,
  requestsList, requestCreate, requestAnswer, obligations, obligationEvidence, financeGet, financeYearCreate,
  financeDistribute, distributionPaid, transparency, audit, alertsMine, demoSeed, demoReset, claimEvidenceUpload,
};
