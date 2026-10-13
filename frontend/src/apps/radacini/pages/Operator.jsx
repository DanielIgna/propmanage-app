import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Check, ClipboardCheck, ShieldOff, X } from "lucide-react";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { Textarea } from "../../../components/ui/textarea";
import { PmMiniMap } from "../../../components/PmMap";
import { radaciniApi, asList, errMsg } from "../api";
import { useMeta, useStaffMe } from "../hooks";
import { Chips, fmtArea, fmtDate, labelOf, PageHeader, PageSkeleton } from "../shared";

export default function Operator() {
  const { staff, loading: staffLoading } = useStaffMe();
  const { meta } = useMeta();
  const canSee = !!staff?.is_staff;
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null);
  const [rejecting, setRejecting] = useState(null); // teren în curs de respingere
  const [note, setNote] = useState("");

  useEffect(() => {
    if (staffLoading) return undefined;
    if (!canSee) {
      setLoading(false);
      return undefined;
    }
    let alive = true;
    setLoading(true);
    radaciniApi
      .staffQueue()
      .then((d) => alive && setItems(asList(d)))
      .catch((e) => alive && setError(e))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [staffLoading, canSee]);

  if (staffLoading || loading) return <PageSkeleton />;
  if (!canSee) {
    return <EmptyState icon={ShieldOff} title="Nu ai acces la coada de verificare" hint="Pagina este pentru personalul Rădăcini." testid="radacini-operator-noaccess" />;
  }

  const verify = async (p, decision, noteText = "") => {
    setBusy(p.id);
    try {
      await radaciniApi.verifyParcel(p.id, decision === "approve" ? { decision } : { decision, note: noteText.trim() });
      toast.success(decision === "approve" ? "Teren publicat" : "Teren respins");
      setItems((list) => list.filter((x) => x.id !== p.id));
      setRejecting(null);
      setNote("");
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut salva decizia"));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-5" data-testid="radacini-operator">
      <PageHeader title="Coada de verificare" subtitle={`${items.length} ${items.length === 1 ? "teren" : "terenuri"} în așteptare`} />

      {error ? (
        <EmptyState icon={AlertTriangle} title="Nu am putut încărca coada" hint={errMsg(error)} testid="radacini-operator-error" />
      ) : items.length === 0 ? (
        <EmptyState icon={ClipboardCheck} title="Nu există terenuri de verificat" hint="Coada se actualizează când proprietarii trimit terenuri." testid="radacini-operator-empty" />
      ) : (
        items.map((p) => (
          <div key={p.id} className={`${CARD} p-4 md:p-5 grid grid-cols-1 lg:grid-cols-2 gap-4`} data-testid={`radacini-queue-${p.id}`}>
            <div className="space-y-3 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <p className="font-bold text-slate-900 dark:text-white break-words">{p.title}</p>
                <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">{fmtDate(p.updated_at)}</span>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {p.locality} · {fmtArea(p.area_m2)} · {p.access || "acces nespecificat"}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300 break-all">
                Proprietar: {p.owner_name || "—"} · {p.owner_email || "—"}
              </p>
              <Chips items={(p.offer?.models || []).map((m) => labelOf(meta?.offer_models, m))} />
              <Chips items={(p.water_sources || []).map((w) => labelOf(meta?.water_sources, w))} />
              {p.current_crops?.length > 0 && <Chips items={p.current_crops} />}
              {p.offer?.harvest_share_percent != null && (
                <p className="text-sm text-slate-600 dark:text-slate-300">Parte din recoltă: {p.offer.harvest_share_percent}%</p>
              )}
              {p.description && <p className="text-sm text-slate-600 dark:text-slate-300 whitespace-pre-line">{p.description}</p>}
              <div className="flex flex-wrap gap-2 pt-1">
                <DSButton variant="success" icon={Check} disabled={busy === p.id} onClick={() => verify(p, "approve")} data-testid={`radacini-aproba-${p.id}`}>
                  Aprobă
                </DSButton>
                <DSButton
                  variant="danger"
                  icon={X}
                  disabled={busy === p.id}
                  onClick={() => {
                    setRejecting(p);
                    setNote("");
                  }}
                  data-testid={`radacini-respinge-${p.id}`}
                >
                  Respinge
                </DSButton>
              </div>
            </div>
            <PmMiniMap lat={p.lat} lng={p.lng} label={p.title} height="260px" />
          </div>
        ))
      )}

      <Dialog open={!!rejecting} onOpenChange={(open) => !open && setRejecting(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Respingi terenul?</DialogTitle>
            <DialogDescription>Scrie motivul. Proprietarul îl va primi prin notificare.</DialogDescription>
          </DialogHeader>
          <Textarea
            rows={4}
            maxLength={500}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="ex. coordonatele nu corespund localității declarate."
            data-testid="radacini-reject-note"
          />
          <DialogFooter>
            <DSButton variant="secondary" onClick={() => setRejecting(null)}>
              Anulează
            </DSButton>
            <DSButton
              variant="danger"
              disabled={!note.trim() || busy === rejecting?.id}
              onClick={() => verify(rejecting, "reject", note)}
              data-testid="radacini-reject-confirm"
            >
              Respinge terenul
            </DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
