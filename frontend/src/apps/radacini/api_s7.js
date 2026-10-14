// Wrappers API Rădăcini S7: necesar, lucrări mecanizate, prestatori (contract în docs/radacini/PLAN.md).
import { api } from "../../lib/api";

const data = (p) => p.then((r) => r.data);

export const s7Api = {
  needs: (projectId) => data(api.get(`/radacini/projects/${projectId}/needs`)),
  createNeed: (projectId, body) => data(api.post(`/radacini/projects/${projectId}/needs`, body)).then((d) => d?.need ?? d),
  pledge: (needId, quantity) => data(api.post(`/radacini/needs/${needId}/pledge`, { quantity })),
  pledgeFulfilled: (needId, index) => data(api.post(`/radacini/needs/${needId}/pledges/${index}/fulfilled`)),
  cancelNeed: (needId) => data(api.post(`/radacini/needs/${needId}/cancel`)),

  serviceTypes: () => data(api.get("/radacini/service-types")),
  providerMe: () => data(api.get("/radacini/providers/me")),
  saveProvider: (body) => data(api.put("/radacini/providers/me", body)),
  providers: (params) => data(api.get("/radacini/providers", { params })),

  serviceRequests: (projectId) => data(api.get(`/radacini/projects/${projectId}/service-requests`)),
  createServiceRequest: (projectId, body) =>
    data(api.post(`/radacini/projects/${projectId}/service-requests`, body)),
  openServiceRequests: () => data(api.get("/radacini/service-requests/open")),
  sendOffer: (id, body) => data(api.post(`/radacini/service-requests/${id}/offers`, body)),
  assign: (id, providerUserId) =>
    data(api.post(`/radacini/service-requests/${id}/assign`, { provider_user_id: providerUserId })),
  done: (id, rating) => data(api.post(`/radacini/service-requests/${id}/done`, { rating })),
  cancelRequest: (id) => data(api.post(`/radacini/service-requests/${id}/cancel`)),
};
