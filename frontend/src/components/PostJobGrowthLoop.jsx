import React, { useEffect, useState } from "react";
import axios from "axios";
import { Heart, CalendarClock, Share2, Check, Home, Copy } from "lucide-react";
import { API } from "../pages/DashShared";
import { GREEN, CTA, Sheet } from "../pages/clientv2/ui";
import { trackIntent } from "../lib/analytics";

const CAT_LABELS = {
  zugravit: "Zugrăvit", parchet: "Parchet", faianta: "Faianță / Gresie", handyman: "Handyman",
  gips_carton: "Gips-carton", hvac: "HVAC / Climatizare", electric: "Electric", plumbing: "Sanitar",
  interior_design: "Design Interior",
};

const Row = ({ icon: Icon, done, title, subtitle, action, testid }) => (
  <div className={`flex items-start gap-3 rounded-2xl border p-3.5 ${done ? "border-[#34C759]/30 bg-[#34C759]/5" : "border-slate-100 bg-white"}`} data-testid={testid}>
    <span className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${done ? "bg-[#34C759]/15" : "bg-slate-50"}`}>
      <Icon className="w-4 h-4" style={{ color: done ? GREEN : "#94a3b8" }} />
    </span>
    <div className="min-w-0 flex-1">
      <div className="text-sm font-bold text-slate-900">{title}</div>
      <div className="text-[11px] text-slate-400 leading-snug mt-0.5">{subtitle}</div>
      {action && <div className="mt-2">{action}</div>}
    </div>
    {done && <Check className="w-4 h-4 shrink-0 mt-1" style={{ color: GREEN }} />}
  </div>
);

// PM-001 lanțul canonic: recenzie → Specialiștii mei → plan mentenanță → recomandă → twin actualizat
export const PostJobGrowthLoop = ({ job, onClose }) => {
  const [templates, setTemplates] = useState([]);
  const [recSent, setRecSent] = useState(false);
  const [recReason, setRecReason] = useState("");
  const [recBusy, setRecBusy] = useState(false);

  const sendRec = async () => {
    setRecBusy(true);
    try {
      await axios.post(`${API}/benefits/recommendations`, {
        request_id: job?.id || job?._id, targets: ["specialist", "lucrare"], reason: recReason,
      });
      setRecSent(true);
    } catch { setRecSent(true); } finally { setRecBusy(false); }
  };

  const [added, setAdded] = useState(false);
  const [adding, setAdding] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    trackIntent("growth_loop_shown");
    axios.get(`${API}/maintenance/templates`).then(r => setTemplates(r.data?.templates || [])).catch(() => {});
  }, []);

  const firstName = (job.specialist_name || "Specialistul").split(" ")[0];
  const tpl = templates.find(t => t.category === job.category);
  const planTitle = tpl ? tpl.title : `Revizie ${CAT_LABELS[job.category] || job.category || "generală"}`;
  const shareUrl = `${window.location.origin}/specialists/${job.specialist_id}`;
  const shareText = `Am lucrat cu ${job.specialist_name} prin PropManage și îl recomand cu încredere. Profilul lui verificat: ${shareUrl}`;

  const addMaintenance = async () => {
    setAdding(true);
    try {
      await axios.post(`${API}/maintenance/tasks`, tpl
        ? { property_id: job.property_id, template_key: tpl.key }
        : { property_id: job.property_id, title: planTitle, category: job.category || "handyman", frequency_months: 12 });
      setAdded(true);
      trackIntent("growth_loop_maintenance_added");
    } catch (e) {
      if (e?.response?.status === 409) setAdded(true);
    } finally { setAdding(false); }
  };

  const copyLink = async () => {
    try { await navigator.clipboard.writeText(shareText); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch {}
    trackIntent("growth_loop_share_copied");
  };

  return (
    <Sheet title="Mulțumim! Ce urmează?" onClose={onClose} testid="pjl-sheet">
      <div className="space-y-2.5">
        <p className="text-xs text-slate-400 leading-relaxed px-1">
          Recenzia ta întărește rețeaua de încredere. Încă 3 pași care lucrează pentru tine:
        </p>
        <Row icon={Heart} done testid="pjl-trusted"
          title={`${firstName} e în „Specialiștii tăi de încredere"`}
          subtitle="Îl re-angajezi cu 1 click din tabul Lucrări — direct, fără licitație, iar taxa lui de lead e 0." />
        <Row icon={CalendarClock} done={added} testid="pjl-maintenance"
          title={added ? `„${planTitle}" e în calendar` : `Programează: ${planTitle}`}
          subtitle={added ? "Îți amintim automat când e scadentă — soliciți oferta în 1 click." : "Previi problemele scumpe — îți amintim automat când e scadentă."}
          action={!added && (
            <button onClick={addMaintenance} disabled={adding} data-testid="pjl-maintenance-add"
              className="px-4 py-2 rounded-full text-xs font-black text-white disabled:opacity-50" style={{ background: GREEN }}>
              {adding ? "..." : "Adaugă în calendar"}
            </button>
          )} />
        <Row icon={Heart} done={recSent} testid="pjl-recommend"
          title={recSent ? "Recomandarea ta e în comunitate 🤝" : `Recomandă lucrarea lui ${firstName} comunității`}
          subtitle={recSent
            ? "Când recomandarea produce o lucrare confirmată, primești un Beneficiu Comunitate în portofel."
            : "Spune de ce îl recomanzi — AI clasifică recomandarea, iar când produce o lucrare confirmată primești un Beneficiu Comunitate."}
          action={!recSent && (
            <div className="w-full space-y-2">
              <textarea value={recReason} onChange={e => setRecReason(e.target.value)} rows={2}
                placeholder="De ce îl recomanzi? (ex: punctual, lucrare de calitate, preț corect)"
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-xs text-slate-700"
                data-testid="pjl-recommend-reason" />
              <button onClick={sendRec} disabled={recBusy} data-testid="pjl-recommend-send"
                className="px-4 py-2 rounded-full text-xs font-black text-white disabled:opacity-50" style={{ background: GREEN }}>
                {recBusy ? "..." : "Trimite recomandarea"}
              </button>
            </div>
          )} />
        <Row icon={Share2} testid="pjl-share"
          title={`Recomandă-l pe ${firstName} unui vecin sau prieten`}
          subtitle="Specialiștii buni se găsesc greu — trimite-le profilul lui verificat."
          action={
            <div className="flex gap-2">
              <a href={`https://wa.me/?text=${encodeURIComponent(shareText)}`} target="_blank" rel="noreferrer"
                onClick={() => trackIntent("growth_loop_share_whatsapp")} data-testid="pjl-share-wa"
                className="px-4 py-2 rounded-full bg-[#25D366] text-white text-xs font-black">WhatsApp</a>
              <button onClick={copyLink} data-testid="pjl-share-copy"
                className="px-4 py-2 rounded-full bg-slate-50 text-slate-600 text-xs font-bold flex items-center gap-1">
                {copied ? <Check className="w-3.5 h-3.5" style={{ color: GREEN }} /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? "Copiat" : "Copiază"}
              </button>
            </div>
          } />
        <Row icon={Home} done testid="pjl-twin"
          title="Cartea casei s-a actualizat automat"
          subtitle="Garanția, factura și istoricul lucrării sunt salvate permanent în profilul proprietății." />
        <CTA testid="pjl-done" onClick={onClose}>Gata</CTA>
      </div>
    </Sheet>
  );
};
