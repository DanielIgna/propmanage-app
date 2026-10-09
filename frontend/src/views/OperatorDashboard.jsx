// PropManage - Operator Dashboard (Digital Twin validation + maintenance logs)
// 4-zone bottom navigation: Twins | Logs | Notificări | Setări
import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  Building, Clock, AlertTriangle, FileCheck, Wrench, ArrowRight,
  Bell, Settings as SettingsIcon, Flag, Box,
} from "lucide-react";
import { TwinEditorModal, TWIN_STATUS_LABELS } from "./OperatorTwin";
import { API, DashLayout, Stat } from "./DashShared";
import { KpiCard, AIInsightCard, EmptyState, CARD, DSBadge } from "../design-system";
import { BottomNav } from "./BottomNav";
import { SettingsPanel } from "./SettingsPanel";
import { NonConformityFlagModal } from "./ActivityTimeline";
import { OperatorDigitalTwin } from "./OperatorDigitalTwin";

export const OperatorDashboard = () => {
  const [queue, setQueue] = useState([]);
  const [twins, setTwins] = useState([]);
  const [notifs, setNotifs] = useState([]);
  const [dtCounters, setDtCounters] = useState({ needs_setup: 0, in_progress: 0, delivered: 0, total: 0 });
  const [tab, setTab] = useState("twins");
  const [editingTwin, setEditingTwin] = useState(null);
  const [flagTarget, setFlagTarget] = useState(null); // {target_type, target_id, label}

  const load = () => {
    axios.get(`${API}/operator/queue`).then(r => setQueue(r.data)).catch(() => {});
    axios.get(`${API}/operator/twins`).then(r => setTwins(r.data)).catch(() => {});
    axios.get(`${API}/operator/digital-twin/clients-queue?status=all`).then(r => setDtCounters(r.data.counters || {})).catch(() => {});
  };
  const loadNotifs = () => axios.get(`${API}/notifications`).then(r => setNotifs(r.data)).catch(() => {});

  useEffect(() => {
    load();
    loadNotifs();
    const interval = setInterval(loadNotifs, 30000);
    return () => clearInterval(interval);
  }, []);

  const pendingTwins = twins.filter(t => t.status === "pending_validation");
  const approvedTwins = twins.filter(t => t.status === "approved");
  const revisionTwins = twins.filter(t => t.status === "needs_revision");
  const unreadNotifs = notifs.filter(n => !n.read).length;

  const tabs = [
    { id: "twins", label: "Twins", icon: Building, badge: pendingTwins.length },
    { id: "dt_pro", label: "DT Pro", icon: Box, badge: (dtCounters.needs_setup || 0) + (dtCounters.in_progress || 0) },
    { id: "logs", label: "Logs", icon: FileCheck, badge: queue.length },
    { id: "notifications", label: "Notificări", icon: Bell, badge: unreadNotifs },
    { id: "settings", label: "Setări", icon: SettingsIcon, badge: 0 },
  ];

  const title = {
    twins: "Validare Digital Twin",
    dt_pro: "Digital Twin Pro · Clienți 3D",
    logs: "Logs Mentenanță",
    notifications: "Notificări",
    settings: "Setări",
  }[tab];

  return (
    <DashLayout role="operator" title={title} bottomNav={<BottomNav tabs={tabs} active={tab} onChange={setTab} dataPrefix="op-tab" />}>
      {tab === "twins" && (
        <>
          {/* „Astăzi:" — workspace operațional (Hick: fiecare card = 1 click către rezolvare) */}
          <div className="mb-6" data-testid="op-today-summary">
            <h3 className="text-sm font-bold mb-3" style={{ color: "var(--pm-text-variant)" }}>Astăzi:</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard icon={Clock} label="Twins de validat" value={pendingTwins.length} accent="warning" onClick={() => document.querySelector('[data-testid="no-pending-twins"], [data-tour="operator-twin-queue"]')?.scrollIntoView({ behavior: "smooth" })} testid="op-pending-twins" />
              <KpiCard icon={Box} label="DT Pro de setat" value={dtCounters.needs_setup || 0} accent="info" onClick={() => setTab("dt_pro")} testid="op-dtpro-setup" />
              <KpiCard icon={FileCheck} label="Logs în coadă" value={queue.length} accent="critical" onClick={() => setTab("logs")} testid="op-logs" />
              <KpiCard icon={Bell} label="Notificări necitite" value={unreadNotifs} accent="neutral" onClick={() => setTab("notifications")} testid="op-notifs" />
            </div>
          </div>

          {/* AI Insights — obligatoriu după KPI (Design System §5) */}
          <div className="mb-6">
            <AIInsightCard
              bullets={[
                `${pendingTwins.length} ${pendingTwins.length === 1 ? "twin așteaptă" : "twins așteaptă"} validare · ${approvedTwins.length} aprobate în total.`,
                `${dtCounters.needs_setup || 0} clienți DT Pro de setat · ${dtCounters.in_progress || 0} în lucru · ${dtCounters.delivered || 0} livrați.`,
                `${queue.length} log-uri de mentenanță în coadă.`,
              ]}
              alerts={pendingTwins.length >= 5 ? [`Coadă mare de validare (${pendingTwins.length} twins) — prioritizează validările ca să nu blochezi clienții.`] : []}
              recommendations={(dtCounters.needs_setup || 0) > 0 ? [`Setează accesul 3D pentru ${dtCounters.needs_setup} ${dtCounters.needs_setup === 1 ? "client" : "clienți"} — tab DT Pro.`] : []}
              onAction={() => setTab("dt_pro")}
              actionLabel="Deschide DT Pro"
              testid="op-ai-insights"
            />
          </div>

          {/* Digital Twin Pro shortcut card (dublat — accesibil și aici și în tab-ul propriu) */}
          <button
            onClick={() => setTab("dt_pro")}
            className={`w-full text-left ${CARD} border-emerald-300 dark:border-emerald-500/40 hover:border-emerald-400 dark:hover:border-emerald-400/60 p-5 mb-6 transition-colors group`}
            data-testid="op-dt-pro-shortcut"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 dark:bg-emerald-500/15 flex items-center justify-center">
                <Box className="w-6 h-6 text-emerald-600 dark:text-emerald-300" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="text-[10px] uppercase tracking-[0.16em] font-semibold text-emerald-700 dark:text-emerald-300">Digital Twin Pro · Modulul 3D</div>
                  {(dtCounters.needs_setup || 0) > 0 && <DSBadge type="WARNING">{dtCounters.needs_setup} setup necesar</DSBadge>}
                </div>
                <div className="font-bold text-lg mt-0.5 text-slate-800 dark:text-slate-100">Clienți cu acces 3D</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  {dtCounters.total === 0
                    ? "Niciun client cu DT Pro încă. Click pentru a acorda primul acces."
                    : `${dtCounters.total} clienți · ${dtCounters.delivered} livrați · ${dtCounters.in_progress} în lucru · ${dtCounters.needs_setup} de setat`}
                </div>
              </div>
              <ArrowRight className="w-5 h-5 text-emerald-600 dark:text-emerald-300 group-hover:translate-x-1 transition-transform" />
            </div>
          </button>

          <div className="space-y-4">
            <div className={`${CARD} p-6`}>
              <h3 className="font-bold text-lg mb-4 flex items-center gap-2 text-slate-800 dark:text-slate-100"><Clock className="w-4 h-4 text-amber-500" />Twins în validare ({pendingTwins.length})</h3>
              {pendingTwins.length === 0 && <EmptyState icon={Building} title="Niciun twin în așteptare" hint="Twins noi apar aici când clienții trimit proprietăți spre validare." testid="no-pending-twins" />}
              <div className="grid sm:grid-cols-2 gap-3">
                {pendingTwins.map(t => <TwinCard key={t.id} t={t} onOpen={() => setEditingTwin(t.property_id)} />)}
              </div>
            </div>

            {(approvedTwins.length > 0 || revisionTwins.length > 0) && (
              <div className={`${CARD} p-6`}>
                <h3 className="font-bold text-lg mb-4 text-slate-800 dark:text-slate-100">Istoric ({approvedTwins.length + revisionTwins.length})</h3>
                <div className="grid sm:grid-cols-2 gap-3">
                  {[...approvedTwins, ...revisionTwins].slice(0, 10).map(t => (
                    <TwinCard key={t.id} t={t} onOpen={() => setEditingTwin(t.property_id)}
                      onFlag={() => setFlagTarget({ target_type: "twin", target_id: t.id, label: t.property_name || "Twin" })} />
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {tab === "dt_pro" && <OperatorDigitalTwin />}

      {tab === "logs" && (
        <div className={`${CARD} p-8 text-center`}>
          <Wrench className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
          <h3 className="font-bold text-2xl mb-2 text-slate-800 dark:text-slate-100">Coadă logs mentenanță</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            {queue.length === 0
              ? "Toate log-urile de mentenanță au fost validate. Noile log-uri vor apărea aici când specialiștii completează lucrări."
              : `${queue.length} log-uri în așteptare.`}
          </p>
        </div>
      )}

      {tab === "notifications" && (
        <div className="space-y-2 max-w-2xl mx-auto" data-testid="notifications-zone">
          {notifs.length === 0 && (
            <div className="text-center py-16">
              <Bell className="w-12 h-12 text-stone-700 mx-auto mb-3" />
              <div className="text-sm text-stone-400">Nicio notificare</div>
            </div>
          )}
          {notifs.map(n => (
            <button
              key={n.id}
              onClick={async () => { await axios.post(`${API}/notifications/${n.id}/read`).catch(() => {}); loadNotifs(); }}
              className={`w-full text-left bg-white/5 rounded-2xl p-4 hover:bg-white/[0.08] transition-colors ${!n.read ? "border border-[#d4ff3a]/30" : ""}`}
              data-testid={`notif-${n.id}`}
            >
              <div className="flex items-start gap-3">
                {!n.read && <div className="w-1.5 h-1.5 rounded-full bg-[#d4ff3a] mt-2 shrink-0" />}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{n.title}</div>
                  <div className="text-xs text-stone-400 mt-1">{n.message}</div>
                  <div className="text-[10px] text-stone-600 mt-2">{new Date(n.created_at).toLocaleString("ro-RO")}</div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {tab === "settings" && <SettingsPanel />}

      {editingTwin && <TwinEditorModal propertyId={editingTwin} onClose={() => setEditingTwin(null)} onSaved={load} />}
      {flagTarget && (
        <NonConformityFlagModal
          targetType={flagTarget.target_type}
          targetId={flagTarget.target_id}
          targetLabel={flagTarget.label}
          onClose={() => setFlagTarget(null)}
        />
      )}
    </DashLayout>
  );
};

const TwinCard = ({ t, onOpen, onFlag }) => {
  const statusInfo = TWIN_STATUS_LABELS[t.status] || TWIN_STATUS_LABELS.draft;
  return (
    <div className="text-left rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 hover:border-blue-300 dark:hover:border-blue-500/50 p-4 transition-colors" data-testid={`twin-card-${t.id || t.property_id}`}>
      <button onClick={onOpen} className="text-left w-full">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="min-w-0">
            <div className="font-medium text-sm truncate text-slate-800 dark:text-slate-100">{t.property_name || "Proprietate"}</div>
            <div className="text-[10px] text-slate-400 truncate">{t.property_address || "—"}</div>
          </div>
          <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded-full whitespace-nowrap ${statusInfo.color}`}>{statusInfo.label}</span>
        </div>
        <div className="text-[10px] text-slate-400 mb-3">
          Proprietar: {t.owner_name || "—"}
        </div>
        <div className="grid grid-cols-3 gap-2 text-xs">
          <Pill label="Camere" value={(t.rooms || []).length} />
          <Pill label="Asset-uri" value={(t.assets || []).length} />
          <Pill label="Suprafață" value={t.property_surface ? `${t.property_surface}m²` : "—"} />
        </div>
        <div className="mt-3 text-[11px] font-bold text-lime-600 dark:text-lime-400 flex items-center gap-1">
          Deschide editor <ArrowRight className="w-3 h-3" />
        </div>
      </button>
      {onFlag && t.status === "approved" && (
        <button
          onClick={(e) => { e.stopPropagation(); onFlag(); }}
          className="mt-3 w-full bg-orange-50 dark:bg-orange-500/10 hover:bg-orange-100 dark:hover:bg-orange-500/20 text-orange-600 dark:text-orange-300 border border-orange-200 dark:border-orange-500/30 py-1.5 rounded-lg text-[11px] flex items-center justify-center gap-1"
          data-testid={`flag-twin-${t.id}`}
        >
          <Flag className="w-3 h-3" />Raportează neconformitate
        </button>
      )}
    </div>
  );
};

const Pill = ({ label, value }) => (
  <div className="bg-white dark:bg-slate-900/50 border border-slate-100 dark:border-slate-700 rounded-lg p-2 text-center">
    <div className="text-[9px] uppercase tracking-wider text-slate-400">{label}</div>
    <div className="font-bold text-sm text-slate-800 dark:text-slate-100">{value}</div>
  </div>
);
