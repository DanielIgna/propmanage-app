// Wrappers S6 (comunități, gospodării, decizii, dispute). Contract: docs/radacini/PLAN.md "S6".
// Singularele vin învelite ({community}, {household}, {decision}, {dispute}); listele ca {items}.
import { api } from "../../lib/api";

const data = (p) => p.then((r) => r.data);
const P = "/radacini";

export const s6aApi = {
  // Comunități
  communities: (params) => data(api.get(`${P}/communities`, { params })),
  community: (id) => data(api.get(`${P}/communities/${id}`)),
  createCommunity: (body) => data(api.post(`${P}/communities`, body)),
  joinCommunity: (id) => data(api.post(`${P}/communities/${id}/join`)),
  leaveCommunity: (id) => data(api.post(`${P}/communities/${id}/leave`)),
  memberAction: (id, uid, action) => data(api.post(`${P}/communities/${id}/members/${uid}/${action}`)),
  posts: (id) => data(api.get(`${P}/communities/${id}/posts`)),
  createPost: (id, body) => data(api.post(`${P}/communities/${id}/posts`, body)),
  deletePost: (postId) => data(api.delete(`${P}/posts/${postId}`)),

  // Gospodării
  myHousehold: () => data(api.get(`${P}/households/mine`)),
  createHousehold: (body) => data(api.post(`${P}/households`, body)),
  addHouseholdMember: (id, body) => data(api.post(`${P}/households/${id}/members`, body)),
  removeHouseholdMember: (id, key) => data(api.delete(`${P}/households/${id}/members/${encodeURIComponent(key)}`)),
  acceptHousehold: (id) => data(api.post(`${P}/households/${id}/accept`)),

  // Decizii
  decisions: (scope, scopeId) => data(api.get(`${P}/decisions`, { params: { scope, scope_id: scopeId } })),
  createDecision: (body) => data(api.post(`${P}/decisions`, body)),
  vote: (id, optionIndex) => data(api.post(`${P}/decisions/${id}/vote`, { option_index: optionIndex })),
  closeDecision: (id) => data(api.post(`${P}/decisions/${id}/close`)),

  // Dispute
  openDispute: (body) => data(api.post(`${P}/disputes`, body)),
  myDisputes: () => data(api.get(`${P}/disputes/mine`)),
  dispute: (id) => data(api.get(`${P}/disputes/${id}`)),
  disputeMessage: (id, text) => data(api.post(`${P}/disputes/${id}/messages`, { text })),
  staffDisputes: () => data(api.get(`${P}/staff/disputes`)),
  takeDispute: (id) => data(api.post(`${P}/disputes/${id}/take`)),
  resolveDispute: (id, status, note) => data(api.post(`${P}/disputes/${id}/resolve`, { status, resolution: note, note })),
};

export const DISPUTE_STATUS = {
  open: { label: "Deschisă", cls: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  in_mediation: { label: "În mediere", cls: "bg-sky-50 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300" },
  resolved: { label: "Rezolvată", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  rejected: { label: "Respinsă", cls: "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300" },
};
export const DISPUTE_SCOPE = { contribution: "Contribuție", reservation: "Rezervare", harvest: "Recoltă", agreement: "Acord" };

// "YYYY-MM-DDTHH:mm" (ora din Europe/Bucharest) -> ISO UTC.
export function bucharestToIso(local) {
  if (!local) return null;
  const [d, t] = local.split("T");
  const [y, mo, da] = d.split("-").map(Number);
  const [h, mi] = (t || "00:00").split(":").map(Number);
  const guess = Date.UTC(y, mo - 1, da, h, mi);
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Europe/Bucharest", hourCycle: "h23", year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric",
  }).formatToParts(new Date(guess));
  const g = (k) => Number(parts.find((p) => p.type === k).value);
  const asBuc = Date.UTC(g("year"), g("month") - 1, g("day"), g("hour"), g("minute"));
  return new Date(guess - (asBuc - guess)).toISOString();
}
