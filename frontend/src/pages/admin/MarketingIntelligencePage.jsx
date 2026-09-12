// MarketingIntelligencePage — Board 007 / GI-3: recomandări executive + Opportunity Queue
// + AI Contact Playbook (AI recomandă, omul aprobă: Trimite / Editează / Ignoră).
import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import {
  Megaphone, RefreshCw, AlertTriangle, MessageCircle, Target, TrendingUp,
  Flame, Sparkles, Copy, Check, X, Pencil, Wallet,
} from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, DSButton, DSSkeleton, EmptyState } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const CONF = {
  confirmed_real:      "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  partially_confirmed: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  ai_hypothesis:       "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300",
  rejected:            "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
};
const URG = { high: "bg-rose-500 text-white", medium: "bg-amber-400 text-slate-900", low: "bg-slate-200 text-slate-600" };
const lei = (v) => `${(v ?? 0).toLocaleString("ro-RO", { maximumFractionDigits: 0 })} lei`;

const PlaybookPanel = ({ item, onClose }) => {
  const [pb, setPb] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [msg, setMsg] = useState("");
  const [decided, setDecided] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    ax.post("/admin/marketing-intel/playbook", { target_type: item.type, ref_id: item.ref_id })
      .then((r) => { setPb(r.data); setMsg(r.data.content?.whatsapp_message || ""); })
      .catch(() => setPb(false))
      .finally(() => setLoading(false));
  }, [item]);

  const decide = async (action) => {
    try {
      await ax.post(`/admin/marketing-intel/playbook/${pb.id}/decision`, { action, final_message: editing ? msg : "" });
      setDecided(action);
    } catch (e) {
      toast.error("Decizia nu a putut fi salvată — încearcă din nou.");
    }
  };
  const copy = () => { navigator.clipboard?.writeText(msg).catch(() => {}); setCopied(true); setTimeout(() => setCopied(false), 1500); };

  return (
    <div className="mt-2 p-4 rounded-xl bg-slate-900 text-white" data-testid="mi-playbook-panel">
      {loading ? <div className="text-sm text-slate-300">Claude pregătește playbook-ul…</div> : !pb ? (
        <div className="text-sm text-rose-300">Nu s-a putut genera playbook-ul.</div>
      ) : decided ? (
        <div className="flex items-center gap-2 text-sm font-bold text-lime-300" data-testid="mi-playbook-decided">
          <Check className="w-4 h-4" /> Decizie memorată în AI Decision Ledger: {decided === "sent" ? "TRIMIS" : decided === "edited" ? "EDITAT & TRIMIS" : "IGNORAT"}
          <button onClick={onClose} className="ml-auto text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="text-[10px] font-black uppercase tracking-wide text-lime-400">De ce contează acest lead</div>
              <ul className="mt-1 space-y-0.5">
                {(pb.why || []).map((w, i) => <li key={i} className="text-xs text-slate-300">• {w}</li>)}
              </ul>
            </div>
            <button onClick={onClose} className="text-slate-400 hover:text-white shrink-0" data-testid="mi-playbook-close"><X className="w-4 h-4" /></button>
          </div>
          <div className="mt-3">
            <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Mesaj WhatsApp propus {pb.ai_generated ? "(Claude)" : "(șablon)"}</div>
            {editing ? (
              <textarea value={msg} onChange={(e) => setMsg(e.target.value)} rows={4}
                className="mt-1 w-full rounded-lg bg-slate-800 border border-slate-700 p-2 text-sm text-white" data-testid="mi-playbook-textarea" />
            ) : (
              <div className="mt-1 p-2.5 rounded-lg bg-slate-800 text-sm text-slate-100 whitespace-pre-wrap" data-testid="mi-playbook-message">{msg}</div>
            )}
            {pb.content?.email_subject && (
              <div className="mt-2 text-[11px] text-slate-400">Email: <b className="text-slate-200">{pb.content.email_subject}</b> · Notificare: {pb.content.notification_text}</div>
            )}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button onClick={copy} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-black bg-slate-700 hover:bg-slate-600" data-testid="mi-playbook-copy">
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />} {copied ? "Copiat" : "Copiază"}
            </button>
            <button onClick={() => decide(editing ? "edited" : "sent")} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-black bg-lime-400 text-slate-900 hover:bg-lime-300" data-testid="mi-playbook-send">
              <Check className="w-3.5 h-3.5" /> Trimite (marchează)
            </button>
            <button onClick={() => setEditing(!editing)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-black bg-slate-700 hover:bg-slate-600" data-testid="mi-playbook-edit">
              <Pencil className="w-3.5 h-3.5" /> {editing ? "Previzualizare" : "Editează"}
            </button>
            <button onClick={() => decide("ignored")} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-black bg-slate-800 text-slate-400 hover:text-rose-300" data-testid="mi-playbook-ignore">
              <X className="w-3.5 h-3.5" /> Ignoră
            </button>
          </div>
          <div className="mt-2 text-[10px] text-slate-500">AI recomandă, omul aprobă (Board 007) — nimic nu se trimite automat; decizia ta intră în AI Decision Ledger.</div>
        </>
      )}
    </div>
  );
};

export default function MarketingIntelligencePage() {
  const [data, setData] = useState(null);
  const [queue, setQueue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState(null);
  const [openPb, setOpenPb] = useState(null);

  const load = async () => {
    try {
      const [m, q] = await Promise.all([
        ax.get("/admin/marketing-intel/latest"),
        ax.get("/admin/marketing-intel/opportunity-queue"),
      ]);
      setData(m.data);
      setQueue(q.data);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Eroare la încărcare.");
    }
    setLoading(false);
  };
  const runScan = async () => {
    setRunning(true);
    try {
      const r = await ax.post("/admin/marketing-intel/run");
      setData(r.data);
      const q = await ax.get("/admin/marketing-intel/opportunity-queue");
      setQueue(q.data);
      toast.success("Analiza de marketing a fost actualizată.");
    } catch (e) {
      toast.error("Analiza a eșuat — încearcă din nou.");
    }
    setRunning(false);
  };
  useEffect(() => { load(); }, []);

  const com = data?.commercial || {};
  const wa = data?.send_windows?.whatsapp || {};

  return (
    <AdminLayoutMetronic
      title="Marketing Intelligence+"
      subtitle="Recomandări executive din date reale + Opportunity Queue + Contact Playbook — AI recomandă, tu aprobi (Board 007)"
    >
      {loading ? <DSSkeleton kpis={4} blocks={3} /> : err ? (
        <div className="p-4 rounded-xl bg-rose-50 text-rose-700 text-sm" data-testid="mi-error"><AlertTriangle className="w-4 h-4 inline mr-1.5" />{err}</div>
      ) : (
        <div className="space-y-6" data-testid="mi-root">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard icon={Flame} label="Oportunități în coadă" value={queue?.count ?? 0} accent="danger" testid="mi-kpi-queue" />
            <KpiCard icon={Wallet} label="Valoare pipeline" value={lei(queue?.total_value_ron)} accent="success" testid="mi-kpi-value" />
            <KpiCard icon={Sparkles} label="Recomandări executive" value={(data?.recommendations || []).length} accent="ai" testid="mi-kpi-recos" />
            <KpiCard icon={TrendingUp} label="Conversie medie" value={`${data?.send_windows?.avg_conversion_pct ?? 0}%`} accent="info" testid="mi-kpi-conv" />
          </div>

          <AdminCard
            title={<span className="flex items-center gap-2"><MessageCircle className="w-4 h-4 text-lime-500" /> WhatsApp Intelligence</span>}
            action={<DSButton variant="primary" icon={RefreshCw} disabled={running} onClick={runScan} data-testid="mi-run-btn">{running ? "Analizează…" : "Rulează analiza"}</DSButton>}
            testid="mi-whatsapp-card"
          >
            <div className="p-3 rounded-xl bg-slate-900 text-white">
              <div className="text-sm font-bold" data-testid="mi-whatsapp-text">{wa.text || "—"}</div>
              <span className={`inline-block mt-1.5 text-[9px] font-black uppercase px-1.5 py-0.5 rounded ${CONF[wa.validation] || CONF.ai_hypothesis}`}>
                {wa.validation === "confirmed_real" ? "Confirmată de date reale" : wa.validation === "partially_confirmed" ? "Confirmată parțial" : "Ipoteză AI"}
              </span>
            </div>
          </AdminCard>

          <div className="grid lg:grid-cols-2 gap-4">
            <AdminCard title={<span className="flex items-center gap-2"><Sparkles className="w-4 h-4 text-lime-500" /> Recomandări executive</span>} testid="mi-exec-recos">
              <div className="space-y-2">
                {(data?.recommendations || []).map((r, i) => (
                  <div key={r.id || i} className="p-3 rounded-xl border border-slate-200 dark:border-slate-700" data-testid={`mi-reco-${i}`}>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded ${CONF[r.confidence] || CONF.ai_hypothesis}`}>{r.confidence_label}</span>
                      <span className="text-[10px] font-bold text-slate-400 uppercase">{r.category}</span>
                      <span className="text-[10px] font-bold text-slate-400 ml-auto">KPI: {r.kpi}</span>
                    </div>
                    <div className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{r.title}</div>
                    <div className="text-xs text-slate-500">{r.reason}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Impact: {r.impact_estimate}</div>
                  </div>
                ))}
              </div>
            </AdminCard>

            <AdminCard title={<span className="flex items-center gap-2"><Target className="w-4 h-4 text-lime-500" /> Commercial Intelligence — răspunsuri directe</span>} testid="mi-commercial">
              <div className="space-y-2">
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid="mi-com-revenue">
                  <div className="text-[10px] font-black uppercase text-slate-400">Cei mai mulți bani</div>
                  <div className="text-sm font-bold text-slate-900 dark:text-white">{com.top_revenue ? `«${com.top_revenue.category}» — ${lei(com.top_revenue.revenue_ron)} confirmați (${com.period_days}z)` : "Fără venituri confirmate în fereastră"}</div>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid="mi-com-converting">
                  <div className="text-[10px] font-black uppercase text-slate-400">Cea mai bună conversie (oportunități)</div>
                  <div className="text-sm font-bold text-slate-900 dark:text-white">{com.best_converting ? `«${com.best_converting.service}» — ${com.best_converting.conv_pct}% (${com.best_converting.accepted}/${com.best_converting.created})` : "Prea puține oportunități pentru comparație"}</div>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid="mi-com-promote">
                  <div className="text-[10px] font-black uppercase text-slate-400">De promovat luna aceasta</div>
                  <div className="text-sm font-bold text-slate-900 dark:text-white">{com.promote_now ? `«${com.promote_now.category}» — ${com.promote_now.recent} cereri în 30z${com.promote_now.trend_pct != null ? ` (${com.promote_now.trend_pct > 0 ? "+" : ""}${com.promote_now.trend_pct}%)` : ""}` : "Fără trend clar încă"}</div>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800" data-testid="mi-com-losing">
                  <div className="text-[10px] font-black uppercase text-slate-400">Pierde clienți</div>
                  <div className="text-sm font-bold text-slate-900 dark:text-white">{com.losing_clients ? `«${com.losing_clients.category}» — ${com.losing_clients.disputes} dispute` : "Nicio categorie cu dispute"}</div>
                </div>
              </div>
            </AdminCard>
          </div>

          <AdminCard title={<span className="flex items-center gap-2"><Flame className="w-4 h-4 text-rose-500" /> Opportunity Queue — ordonată după probabilitate × valoare × urgență</span>} testid="mi-queue">
            {!(queue?.items || []).length ? (
              <EmptyState icon={Target} title="Coadă goală" hint="Se populează din lead-urile fierbinți și oportunitățile Revenue Hunter." />
            ) : (
              <div className="space-y-2">
                {queue.items.map((it, i) => (
                  <div key={`${it.type}-${it.ref_id}`} data-testid={`mi-queue-item-${i}`}>
                    <div className="flex items-center gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700 flex-wrap">
                      <span className="xos-num text-lg font-black text-slate-900 dark:text-white w-14 shrink-0">{it.probability_pct}%</span>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-bold text-slate-900 dark:text-white truncate">{it.name} — {it.service_label}</div>
                        <div className="text-[11px] text-slate-400 truncate">{(it.signals || []).slice(0, 3).join(" · ") || "Oportunitate Revenue Hunter"}</div>
                      </div>
                      <span className="text-sm font-black text-slate-700 dark:text-slate-200 shrink-0">{lei(it.value_ron)}</span>
                      <span className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded shrink-0 ${URG[it.urgency]}`}>{it.urgency === "high" ? "URGENT" : it.urgency === "medium" ? "MEDIU" : "SCĂZUT"}</span>
                      <DSButton variant="ghost" icon={MessageCircle} onClick={() => setOpenPb(openPb === i ? null : i)} data-testid={`mi-playbook-btn-${i}`}>Playbook</DSButton>
                    </div>
                    {openPb === i && <PlaybookPanel item={it} onClose={() => setOpenPb(null)} />}
                  </div>
                ))}
              </div>
            )}
          </AdminCard>

          <div className="text-[10px] text-slate-400" data-testid="mi-meta">
            Ultima analiză: {data?.generated_at && new Date(data.generated_at).toLocaleString("ro-RO")} · rulare automată zilnică 06:55 ·
            fiecare recomandare are motiv + încredere + impact + KPI (Board 007) · deciziile playbook intră în AI Decision Ledger (GI-4)
          </div>
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
