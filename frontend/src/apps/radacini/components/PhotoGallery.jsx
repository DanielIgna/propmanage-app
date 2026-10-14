import React, { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Camera, ImagePlus, Trash2 } from "lucide-react";
import { CARD, DSButton } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { useConfirm } from "./ConfirmDialog";
import { errMsg } from "../api";
import { s6bApi, photoUrl } from "../api_s6b";

const MAX_BYTES = 5 * 1024 * 1024;
const MAX_PHOTOS = 6;
const TYPES = ["image/jpeg", "image/png", "image/webp"];

// Galerie foto: grilă + lightbox + încărcare (canUpload) + ștergere (canDelete, implicit = canUpload).
// targetType: "parcel" | "listing" | "harvest". Dacă nu are poze și nu poți încărca, nu afișează nimic.
export default function PhotoGallery({ targetType, targetId, canUpload = false, canDelete, title = "Fotografii" }) {
  const deletable = canDelete ?? canUpload;
  const [confirm, confirmDialog] = useConfirm();
  const [items, setItems] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [viewing, setViewing] = useState(null);
  const fileRef = useRef(null);
  const camRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const d = await s6bApi.photos(targetType, targetId);
      setItems(Array.isArray(d) ? d : d?.items || d?.photos || []);
    } catch {
      setItems([]);
    } finally {
      setLoaded(true);
    }
  }, [targetType, targetId]);

  useEffect(() => {
    if (targetId) load();
  }, [targetId, load]);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!TYPES.includes(file.type)) return toast.error("Sunt acceptate doar imagini JPEG, PNG sau WebP.");
    if (file.size > MAX_BYTES) return toast.error("Imaginea depășește 5 MB.");
    if (items.length >= MAX_PHOTOS) return toast.error(`Maximum ${MAX_PHOTOS} fotografii.`);
    setUploading(true);
    try {
      await s6bApi.uploadPhoto(targetType, targetId, file);
      toast.success("Fotografia a fost încărcată");
      await load();
    } catch (err) {
      toast.error(errMsg(err, "Nu am putut încărca fotografia"));
    } finally {
      setUploading(false);
    }
  };

  const remove = async (p) => {
    if (!(await confirm({ title: "Ștergi fotografia?", description: "Acțiunea nu poate fi anulată.", confirmLabel: "Șterge", danger: true }))) return;
    setBusyId(p.id);
    try {
      await s6bApi.deletePhoto(p.id);
      setViewing(null);
      setItems((l) => l.filter((x) => x.id !== p.id));
      toast.success("Fotografia a fost ștearsă");
    } catch (err) {
      toast.error(errMsg(err, "Nu am putut șterge fotografia"));
    } finally {
      setBusyId(null);
    }
  };

  if (!loaded) return null;
  if (!items.length && !canUpload) return null;

  return (
    <section className={`${CARD} p-4 md:p-5 space-y-3`} data-testid={`radacini-galerie-${targetType}`}>
      {confirmDialog}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white">
          {title} <span className="font-normal text-slate-500 dark:text-slate-400">({items.length}/{MAX_PHOTOS})</span>
        </h3>
        {canUpload && (
          <>
            <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={onFile} data-testid="radacini-galerie-input" />
            <input ref={camRef} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden" onChange={onFile} data-testid="radacini-galerie-camera-input" />
            <DSButton
              variant="secondary"
              icon={ImagePlus}
              disabled={uploading || items.length >= MAX_PHOTOS}
              onClick={() => fileRef.current?.click()}
              data-testid="radacini-galerie-incarca"
            >
              {uploading ? "Se încarcă…" : "Adaugă fotografie"}
            </DSButton>
            <DSButton
              variant="secondary"
              icon={Camera}
              className="md:hidden"
              disabled={uploading || items.length >= MAX_PHOTOS}
              onClick={() => camRef.current?.click()}
              data-testid="radacini-galerie-camera"
            >
              Fă o poză
            </DSButton>
          </>
        )}
      </div>
      {canUpload && <p className="text-xs text-slate-500 dark:text-slate-400">JPEG, PNG sau WebP, până la 5 MB. Datele de locație din poză sunt eliminate automat.</p>}

      {items.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Nu există fotografii încă.</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {items.map((p) => (
            <div key={p.id} className="relative group aspect-[4/3] overflow-hidden rounded-xl bg-slate-100 dark:bg-white/5">
              <button type="button" className="absolute inset-0 w-full h-full" onClick={() => setViewing(p)} aria-label="Mărește fotografia" data-testid={`radacini-foto-${p.id}`}>
                <img src={photoUrl(p.id)} alt="" loading="lazy" className="w-full h-full object-cover" />
              </button>
              {deletable && (
                <button
                  type="button"
                  disabled={busyId === p.id}
                  onClick={() => remove(p)}
                  className="absolute top-1.5 right-1.5 rounded-full bg-black/70 p-1.5 text-white hover:bg-red-600 disabled:opacity-50"
                  aria-label="Șterge fotografia"
                  data-testid={`radacini-foto-sterge-${p.id}`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <Dialog open={!!viewing} onOpenChange={(o) => !o && setViewing(null)}>
        <DialogContent className="max-w-4xl" data-testid="radacini-lightbox">
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription className="sr-only">Fotografie mărită</DialogDescription>
          </DialogHeader>
          {viewing && <img src={photoUrl(viewing.id)} alt="" className="max-h-[75vh] w-full object-contain rounded-lg" />}
        </DialogContent>
      </Dialog>
    </section>
  );
}
