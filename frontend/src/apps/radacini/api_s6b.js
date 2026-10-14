// S6 (partea F/G): fotografii și pagini publice. Integrat de coordonator în api.js dacă se dorește.
import { api, BACKEND_URL } from "../../lib/api";

const data = (p) => p.then((r) => r.data);

export const s6bApi = {
  // Fotografii: target_type = "parcel" | "listing" | "harvest". Răspuns: {items:[{id,width,height,...}]}
  photos: (targetType, targetId) =>
    data(api.get("/radacini/photos", { params: { target_type: targetType, target_id: targetId } })),
  uploadPhoto: (targetType, targetId, file) => {
    const fd = new FormData();
    fd.append("target_type", targetType);
    fd.append("target_id", targetId);
    fd.append("file", file);
    return data(api.post("/radacini/photos", fd));
  },
  deletePhoto: (id) => data(api.delete(`/radacini/photos/${id}`)),

  // Public (fără cont)
  publicListings: (params) => data(api.get("/radacini/public/listings", { params })),
  publicCommunities: (params) => data(api.get("/radacini/public/communities", { params })),
  publicParcels: (params) => data(api.get("/radacini/parcels", { params })),
};

export const photoUrl = (id) => `${BACKEND_URL || ""}/api/radacini/photos/${id}`;
