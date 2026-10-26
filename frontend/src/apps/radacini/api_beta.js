// Wrappers API Rădăcini pentru lansarea beta: raportarea conținutului (DSA), starea sistemului, datele operatorului.
import { api } from "../../lib/api";

const data = (p) => p.then((r) => r.data);

export const betaApi = {
  report: (body) => data(api.post("/radacini/reports", body)),
  myReports: () => data(api.get("/radacini/reports/mine")),
  staffReports: (status) => data(api.get("/radacini/staff/reports", { params: status ? { status } : undefined })),
  resolveReport: (id, body) => data(api.post(`/radacini/staff/reports/${id}/resolve`, body)),
  system: () => data(api.get("/radacini/admin/system")),
  operator: () => data(api.get("/radacini/operator")),
};

export const REPORT_REASONS = [
  { id: "illegal", label: "Conținut ilegal" },
  { id: "fraud", label: "Înșelătorie sau date false" },
  { id: "unsafe_food", label: "Produs alimentar nesigur" },
  { id: "abuse", label: "Hărțuire sau limbaj abuziv" },
  { id: "privacy", label: "Date personale expuse" },
  { id: "spam", label: "Spam sau reclamă" },
  { id: "other", label: "Altceva" },
];

export const REPORT_DECISIONS = [
  { id: "no_action", label: "Fără măsuri: conținutul respectă regulile" },
  { id: "content_restricted", label: "Conținutul a fost restricționat" },
  { id: "user_warned", label: "Utilizatorul a fost avertizat" },
];

export const REPORT_TARGETS = { listing: "Anunț", parcel: "Teren", community: "Comunitate", user: "Utilizator" };
