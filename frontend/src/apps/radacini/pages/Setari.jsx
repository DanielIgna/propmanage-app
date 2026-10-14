import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Download, Trash2 } from "lucide-react";
import { useAuth } from "../../../auth";
import { CARD, DSButton } from "../../../design-system";
import { useConfirm } from "../components/ConfirmDialog";
import { radaciniApi, errMsg } from "../api";
import { s8Api, ONBOARDING_OPEN_EVENT } from "../api_s8";

export default function Setari() {
  const { user } = useAuth();
  const [confirm, confirmDialog] = useConfirm();
  const [exporting, setExporting] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [requested, setRequested] = useState(false);

  const [accepted, setAccepted] = useState(null);
  useEffect(() => {
    s8Api.legalMe().then((d) => setAccepted(d?.accepted || [])).catch(() => setAccepted([]));
  }, []);
  const restartGuide = async () => {
    try {
      await s8Api.onboardingReset();
      window.dispatchEvent(new Event(ONBOARDING_OPEN_EVENT));
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut relua ghidul"));
    }
  };

  const downloadData = async () => {
    setExporting(true);
    try {
      const d = await radaciniApi.exportMyData();
      const blob = new Blob([JSON.stringify(d, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `radacini-datele-mele-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast.success("Datele tale au fost descărcate");
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut descărca datele"));
    } finally {
      setExporting(false);
    }
  };

  const requestDeletion = async () => {
    if (
      !(await confirm({
        title: "Ceri ștergerea datelor?",
        description:
          "Trimitem o cerere de ștergere a datelor tale din Rădăcini. Cererea e analizată de echipă; anumite date (de ex. acordurile semnate) pot fi păstrate cât cere legea.",
        confirmLabel: "Trimite cererea",
        danger: true,
      }))
    )
      return;
    setRequesting(true);
    try {
      await radaciniApi.requestDataDeletion();
      setRequested(true);
      toast.success("Cererea de ștergere a fost înregistrată");
    } catch (e) {
      if (e?.response?.status === 409) {
        setRequested(true);
        toast.info("Ai deja o cerere în curs.");
      } else {
        toast.error(errMsg(e, "Nu am putut trimite cererea"));
      }
    } finally {
      setRequesting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      {confirmDialog}
      <div className={`${CARD} p-5 space-y-2`}>
        <h2 className="text-base font-bold text-slate-900 dark:text-white">Cont</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">Nume: {user?.full_name || user?.name || "—"}</p>
        <p className="text-sm text-slate-600 dark:text-slate-300">Email: {user?.email || "—"}</p>
      </div>

      <section className={`${CARD} p-5 space-y-3`} data-testid="radacini-setari-termeni">
        <h2 className="text-base font-bold text-slate-900 dark:text-white">Termeni și ghid</h2>
        {accepted && accepted.length === 0 && <p className="text-sm text-slate-600 dark:text-slate-300">Nu ai acceptat încă termenii.</p>}
        {accepted?.map((a, i) => (
          <p key={`${a.type}-${i}`} className="text-sm text-slate-600 dark:text-slate-300">
            {a.type === "privacy" ? "Confidențialitate" : "Termeni"} · versiunea {a.version}
            {a.accepted_at ? ` · acceptat la ${new Date(a.accepted_at).toLocaleDateString("ro-RO")}` : ""}
          </p>
        ))}
        <div className="flex flex-wrap gap-2">
          <a href="/radacini/termeni" target="_blank" rel="noopener noreferrer" className="text-sm text-emerald-700 underline self-center">Citește termenii</a>
          <DSButton variant="secondary" onClick={restartGuide} data-testid="radacini-reia-ghid">Reia ghidul</DSButton>
        </div>
      </section>

      <section className={`${CARD} p-5 space-y-4`} data-testid="radacini-gdpr">
        <div className="space-y-1">
          <h2 className="text-base font-bold text-slate-900 dark:text-white">Datele mele (GDPR)</h2>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Poți descărca o copie a datelor tale din Rădăcini sau poți cere ștergerea lor.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <DSButton variant="secondary" icon={Download} disabled={exporting} onClick={downloadData} data-testid="radacini-btn-export-date">
            {exporting ? "Se pregătește…" : "Descarcă datele mele"}
          </DSButton>
          <DSButton variant="danger" icon={Trash2} disabled={requesting} onClick={requestDeletion} data-testid="radacini-btn-cere-stergere">
            Cere ștergerea datelor
          </DSButton>
        </div>
        {requested && (
          <p className="text-xs text-slate-500 dark:text-slate-400" data-testid="radacini-stergere-in-curs">
            Ai o cerere de ștergere în curs. Echipa o va analiza.
          </p>
        )}
      </section>
    </div>
  );
}
