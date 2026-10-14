import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Gavel } from "lucide-react";
import { DSButton } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { Textarea } from "../../../components/ui/textarea";
import { errMsg } from "../api";
import { DISPUTE_SCOPE, s6aApi } from "../api_s6a";

// Buton „Deschide o dispută” pentru un obiect disputabil (scopeType: contribution|reservation|harvest|agreement).
export default function DisputeButton({ scopeType, scopeId, label = "Deschide o dispută", variant = "ghost", className = "", testid }) {
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const id = testid || `radacini-dispute-btn-${scopeType}-${scopeId}`;

  const submit = async () => {
    if (reason.trim().length < 10) return toast.error("Descrie motivul în cel puțin 10 caractere.");
    setBusy(true);
    try {
      const d = await s6aApi.openDispute({ scope_type: scopeType, scope_id: scopeId, reason: reason.trim() });
      toast.success("Disputa a fost deschisă");
      setOpen(false);
      setReason("");
      const did = d?.dispute?.id;
      if (did) nav(`/radacini/dispute/${did}`);
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut deschide disputa"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <DSButton variant={variant} icon={Gavel} className={className} onClick={() => setOpen(true)} data-testid={id}>
        {label}
      </DSButton>
      <Dialog open={open} onOpenChange={(o) => !busy && setOpen(o)}>
        <DialogContent data-testid="radacini-dispute-dialog">
          <DialogHeader>
            <DialogTitle>Deschide o dispută ({DISPUTE_SCOPE[scopeType] || scopeType})</DialogTitle>
            <DialogDescription>Un operator Rădăcini va media între părți. Descrie pe scurt problema (10–1000 de caractere).</DialogDescription>
          </DialogHeader>
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={1000}
            rows={5}
            placeholder="Ce s-a întâmplat?"
            data-testid="radacini-dispute-reason"
          />
          <DialogFooter>
            <DSButton variant="secondary" onClick={() => setOpen(false)} disabled={busy}>
              Renunță
            </DSButton>
            <DSButton onClick={submit} disabled={busy} data-testid="radacini-dispute-submit">
              {busy ? "Se trimite…" : "Deschide disputa"}
            </DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
