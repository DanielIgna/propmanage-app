import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Flag } from "lucide-react";
import { DSButton } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { Textarea } from "../../../components/ui/textarea";
import { errMsg } from "../api";
import { betaApi, REPORT_REASONS, REPORT_TARGETS } from "../api_beta";
import { Field } from "../shared";

const selectCls = "w-full rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm dark:border-white/15 dark:bg-white/5";

// Buton „Raportează” (notificare DSA) pentru un anunț, teren, comunitate sau utilizator.
export default function ReportButton({ targetType, targetId, className = "" }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [details, setDetails] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!reason) return toast.error("Alege motivul.");
    setBusy(true);
    try {
      await betaApi.report({ target_type: targetType, target_id: targetId, reason, details: details.trim() });
      toast.success("Raportare trimisă. Îți comunicăm decizia.");
      setOpen(false);
      setReason("");
      setDetails("");
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut trimite raportarea"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-red-700 dark:text-slate-400 dark:hover:text-red-300 ${className}`}
        data-testid={`radacini-report-${targetType}`}
      >
        <Flag className="h-3.5 w-3.5" aria-hidden /> Raportează
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="radacini-report-dialog">
          <DialogHeader>
            <DialogTitle>Raportează {(REPORT_TARGETS[targetType] || "conținutul").toLowerCase()}</DialogTitle>
            <DialogDescription>
              Personalul Rădăcini analizează raportarea și îți comunică decizia. Pentru urgențe sau pericol, sună la 112.
            </DialogDescription>
          </DialogHeader>
          <Field label="Motiv" htmlFor="rep-reason">
            <select id="rep-reason" value={reason} onChange={(e) => setReason(e.target.value)} className={selectCls} data-testid="radacini-report-reason">
              <option value="">— alege —</option>
              {REPORT_REASONS.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
            </select>
          </Field>
          <Field label="Detalii" htmlFor="rep-details" hint="Opțional. Ce anume e problema? (cel mult 1000 de caractere)">
            <Textarea id="rep-details" rows={4} maxLength={1000} value={details} onChange={(e) => setDetails(e.target.value)} data-testid="radacini-report-details" />
          </Field>
          <p className="text-xs text-slate-500">
            Raportările tale și deciziile le găsești în <Link to="/radacini/raportari" className="underline">Raportări</Link>.
          </p>
          <DialogFooter>
            <DSButton variant="secondary" onClick={() => setOpen(false)}>Renunță</DSButton>
            <DSButton onClick={submit} disabled={busy} data-testid="radacini-report-submit">{busy ? "Se trimite…" : "Trimite raportarea"}</DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
