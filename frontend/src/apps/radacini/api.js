// Wrappers pentru contractul API Rădăcini S1 (docs/radacini/PLAN.md). Toate rutele sunt sub /api/radacini.
import { api, apiErr } from "../../lib/api";

const data = (p) => p.then((r) => r.data);

export const radaciniApi = {
  health: () => data(api.get("/radacini/health")),
  meta: () => data(api.get("/radacini/meta")),

  // Membri
  memberMe: () => data(api.get("/radacini/members/me")),
  saveMember: (body) => data(api.put("/radacini/members/me", body)),

  // Terenuri
  parcels: (params) => data(api.get("/radacini/parcels", { params })),
  // Răspunsul single vine învelit: {parcel}.
  parcel: (id) => data(api.get(`/radacini/parcels/${id}`)).then((d) => d?.parcel ?? d),
  myParcels: () => data(api.get("/radacini/parcels/mine")),
  createParcel: (body) => data(api.post("/radacini/parcels", body)),
  updateParcel: (id, body) => data(api.patch(`/radacini/parcels/${id}`, body)),
  submitParcel: (id) => data(api.post(`/radacini/parcels/${id}/submit`)),
  pauseParcel: (id) => data(api.post(`/radacini/parcels/${id}/pause`)),
  resumeParcel: (id) => data(api.post(`/radacini/parcels/${id}/resume`)),
  deleteParcel: (id) => data(api.delete(`/radacini/parcels/${id}`)),

  // Conturi de test (doar super-admin)
  testAccounts: () => data(api.get("/radacini/test-accounts")),
  ensureTestAccounts: () => data(api.post("/radacini/test-accounts/ensure")),
  seedDemoScenario: () => data(api.post("/radacini/test-accounts/seed")),
  resetDemoScenario: () => data(api.post("/radacini/test-accounts/reset")),

  // Personal (operator / manager)
  staffMe: () => data(api.get("/radacini/staff/me")),
  staffQueue: () => data(api.get("/radacini/staff/queue")),
  verifyParcel: (id, body) => data(api.post(`/radacini/staff/parcels/${id}/verify`, body)),
  staffList: () => data(api.get("/radacini/staff")),
  addStaff: (body) => data(api.post("/radacini/staff", body)),
  removeStaff: (userId) => data(api.delete(`/radacini/staff/${userId}`)),

  // Cereri de teren (S2). Singulare învelite: {request}, {message}, {agreement}, {request, messages}, {request, agreement}.
  createRequest: (parcelId, body) =>
    data(api.post(`/radacini/parcels/${parcelId}/requests`, body)).then((d) => d?.request ?? d),
  requestsSent: () => data(api.get("/radacini/requests/sent")),
  requestsReceived: () => data(api.get("/radacini/requests/received")),
  // Returnează {request, messages}.
  request: (id) => data(api.get(`/radacini/requests/${id}`)),
  sendRequestMessage: (id, text) =>
    data(api.post(`/radacini/requests/${id}/messages`, { text })).then((d) => d?.message ?? d),
  counterRequest: (id, body) => data(api.post(`/radacini/requests/${id}/counter`, body)).then((d) => d?.request ?? d),
  declineRequest: (id, reason) => data(api.post(`/radacini/requests/${id}/decline`, reason ? { reason } : {})),
  withdrawRequest: (id) => data(api.post(`/radacini/requests/${id}/withdraw`)),
  // Returnează {request, agreement}.
  acceptRequest: (id) => data(api.post(`/radacini/requests/${id}/accept`)),

  // Acorduri (S2)
  agreements: () => data(api.get("/radacini/agreements")),
  agreement: (id) => data(api.get(`/radacini/agreements/${id}`)).then((d) => d?.agreement ?? d),
  // body = termenii (parțial): {terms: {...}}
  updateAgreement: (id, terms) =>
    data(api.patch(`/radacini/agreements/${id}`, { terms })).then((d) => d?.agreement ?? d),
  proposeAgreement: (id) => data(api.post(`/radacini/agreements/${id}/propose`)).then((d) => d?.agreement ?? d),
  signAgreement: (id, version) =>
    data(api.post(`/radacini/agreements/${id}/sign`, { version })).then((d) => d?.agreement ?? d),
  cancelAgreement: (id, reason) =>
    data(api.post(`/radacini/agreements/${id}/cancel`, reason ? { reason } : {})).then((d) => d?.agreement ?? d),

  // GDPR: export JSON al datelor proprii și cerere de ștergere (409 dacă există deja una în curs).
  exportMyData: () => data(api.get("/radacini/me/export")),
  requestDataDeletion: () => data(api.post("/radacini/me/delete-request")),

  // Proiecte agricole (S3). Singulare învelite: {project}, {crop}, {activity}, {contribution}.
  // Liste: {items}; plan culturi: + warnings; contribuții: + totals.
  projects: () => data(api.get("/radacini/projects")),
  project: (id) => data(api.get(`/radacini/projects/${id}`)).then((d) => d?.project ?? d),
  addProjectMember: (id, email) => data(api.post(`/radacini/projects/${id}/members`, { email })),
  updateProjectMember: (id, userId, role) => data(api.patch(`/radacini/projects/${id}/members/${userId}`, { role })),
  removeProjectMember: (id, userId) => data(api.delete(`/radacini/projects/${id}/members/${userId}`)),
  completeProject: (id) => data(api.post(`/radacini/projects/${id}/complete`)),

  // Plan culturi
  projectCrops: (id) => data(api.get(`/radacini/projects/${id}/crops`)),
  createCrop: (id, body) => data(api.post(`/radacini/projects/${id}/crops`, body)),
  updateCrop: (cropId, body) => data(api.patch(`/radacini/crops/${cropId}`, body)),
  deleteCrop: (cropId) => data(api.delete(`/radacini/crops/${cropId}`)),

  // Activități
  projectActivities: (id, params) => data(api.get(`/radacini/projects/${id}/activities`, { params })),
  createActivity: (id, body) => data(api.post(`/radacini/projects/${id}/activities`, body)),
  updateActivity: (actId, body) => data(api.patch(`/radacini/activities/${actId}`, body)),
  joinActivity: (actId) => data(api.post(`/radacini/activities/${actId}/join`)),
  leaveActivity: (actId) => data(api.post(`/radacini/activities/${actId}/leave`)),
  doneActivity: (actId) => data(api.post(`/radacini/activities/${actId}/done`)),
  cancelActivity: (actId) => data(api.post(`/radacini/activities/${actId}/cancel`)),

  // Contribuții (append-only; corecțiile = contribuție nouă cu corrects_id)
  projectContributions: (id, params) => data(api.get(`/radacini/projects/${id}/contributions`, { params })),
  createContribution: (id, body) => data(api.post(`/radacini/projects/${id}/contributions`, body)),
  reviewContribution: (contribId, decision, note) =>
    data(api.post(`/radacini/contributions/${contribId}/review`, note ? { decision, note } : { decision })),

  // Recoltă (S4). Singulare învelite: {harvest}, {allocation}. Liste: {items, totals} · {items, allocated_kg, remaining_kg}.
  projectHarvests: (id) => data(api.get(`/radacini/projects/${id}/harvests`)),
  createHarvest: (id, body) => data(api.post(`/radacini/projects/${id}/harvests`, body)).then((d) => d?.harvest ?? d),
  confirmHarvest: (id) => data(api.post(`/radacini/harvests/${id}/confirm`)).then((d) => d?.harvest ?? d),
  harvestAllocations: (id) => data(api.get(`/radacini/harvests/${id}/allocations`)),
  createAllocation: (id, body) => data(api.post(`/radacini/harvests/${id}/allocations`, body)).then((d) => d?.allocation ?? d),
  deleteAllocation: (id) => data(api.delete(`/radacini/allocations/${id}`)),
  allocationReceived: (id) => data(api.post(`/radacini/allocations/${id}/received`)).then((d) => d?.allocation ?? d),

  // Piață (S4). Singulare învelite: {listing}, {reservation}. Liste: {items} · listări: {items, total}.
  listings: (params) => data(api.get("/radacini/listings", { params })),
  myListings: () => data(api.get("/radacini/listings/mine")),
  listing: (id) => data(api.get(`/radacini/listings/${id}`)).then((d) => d?.listing ?? d),
  createListing: (body) => data(api.post("/radacini/listings", body)).then((d) => d?.listing ?? d),
  updateListing: (id, body) => data(api.patch(`/radacini/listings/${id}`, body)).then((d) => d?.listing ?? d),
  closeListing: (id) => data(api.post(`/radacini/listings/${id}/close`)).then((d) => d?.listing ?? d),

  // Rezervări (S4). role = "buyer" | "seller".
  createReservation: (listingId, body) =>
    data(api.post(`/radacini/listings/${listingId}/reservations`, body)).then((d) => d?.reservation ?? d),
  myReservations: (role) => data(api.get("/radacini/reservations/mine", { params: { role } })),
  confirmReservation: (id) => data(api.post(`/radacini/reservations/${id}/confirm`)).then((d) => d?.reservation ?? d),
  declineReservation: (id) => data(api.post(`/radacini/reservations/${id}/decline`)).then((d) => d?.reservation ?? d),
  cancelReservation: (id) => data(api.post(`/radacini/reservations/${id}/cancel`)).then((d) => d?.reservation ?? d),
  pickedUpReservation: (id) => data(api.post(`/radacini/reservations/${id}/picked-up`)).then((d) => d?.reservation ?? d),
  noShowReservation: (id) => data(api.post(`/radacini/reservations/${id}/no-show`)).then((d) => d?.reservation ?? d),
  rateReservation: (id, body) => data(api.post(`/radacini/reservations/${id}/rate`, body)).then((d) => d?.reservation ?? d),

  // Administrare (S5, doar manager). Liste: {items, total?}; adminKpis: obiect plat cu contoare.
  adminKpis: () => data(api.get("/radacini/admin/kpis")),
  // before = created_at al ultimului eveniment primit (paginare spre vechi).
  adminActivity: ({ limit = 50, before } = {}) =>
    data(api.get("/radacini/admin/activity", { params: before ? { limit, before } : { limit } })),
  adminMembers: (params) => data(api.get("/radacini/admin/members", { params })),
  adminParcels: (params) => data(api.get("/radacini/admin/parcels", { params })),
  adminListings: (params) => data(api.get("/radacini/admin/listings", { params })),
  adminCloseListing: (id, reason) => data(api.post(`/radacini/admin/listings/${id}/close`, { reason })),
  adminDeletionRequests: (params) => data(api.get("/radacini/admin/deletion-requests", { params })),
  adminResolveDeletion: (id, decision, note) =>
    data(api.post(`/radacini/admin/deletion-requests/${id}/resolve`, note ? { decision, note } : { decision })),
  adminAudit: ({ limit = 100 } = {}) => data(api.get("/radacini/admin/audit", { params: { limit } })),
};

// Listele pot veni ca array sau învelite; acceptăm ambele forme.
export const asList = (d) => (Array.isArray(d) ? d : d?.items || d?.results || []);

export const IMPERSONATION_BLOCKED_MSG =
  "În modul test (impersonare) semnarea/acceptarea e blocată pentru siguranță. Pentru fluxul complet folosește conturile demo cu parolă (client@/specialist@propmanage.io).";

// Mesaj de eroare lizibil: FastAPI 422 trimite `detail` ca listă de {msg}.
export const errMsg = (e, fallback = "A apărut o eroare") => {
  const d = e?.response?.data?.detail;
  if (e?.response?.status === 403 && /impersonar/i.test(typeof d === "string" ? d : "")) return IMPERSONATION_BLOCKED_MSG;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d.length) return d.map((x) => x?.msg).filter(Boolean).join(" · ") || fallback;
  return String(apiErr(e, fallback));
};
