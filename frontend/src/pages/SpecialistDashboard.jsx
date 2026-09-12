// PropManage - Specialist Dashboard with 4-zone bottom navigation
// Tabs: Oportunități | Lucrările mele | Notificări | Setări
import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  Wallet, Star, Briefcase, Award, Sparkles, FileCheck, MessageSquare, AlertTriangle,
  Palette, Plus, Image as ImageIcon, Target, ClipboardCheck, Bell,
  Settings as SettingsIcon, Search, RefreshCw, Clock, Crown, MapPin, Flame,
  CheckCircle2, ShieldCheck, ChevronRight, Inbox, TrendingUp, Layers,
} from "lucide-react";
import { useAuth, formatApiError } from "../auth";
import { ChatPanel } from "./ChatPanel";
import { OpenDisputeModal, SpecialistDocumentsModal } from "./AdminModals";
import { ProposePhaseModal } from "./InteriorDesign";
import { PortfolioManagerModal } from "./Portfolio";
import { ProjectListSection } from "./ProjectWorkspace";
import { API, DashLayout, StatusBadge, NavigateButtons } from "./DashShared";
import { BottomNav } from "./BottomNav";
import { SettingsPanel } from "./SettingsPanel";
import { ReferralHub, claimPendingInvite } from "../components/ReferralHub";import { RequestTimelineModal, ScheduleProposalModal, LastActionBanner } from "./ActivityTimeline";
import { TierCelebrationBanner } from "../lib/TierCelebrationBanner";
import { QuestPanel } from "../lib/QuestPanel";
import { SpecialistCockpit } from "./SpecialistCockpit";
import { useTier } from "../lib/useTier";
import {
  PMCard, PMCardPrimary, PMStatCard, PMPillButton, PMChip,
  PMSectionHeader, PMEmptyState,
} from "../components/pm";
import { SpecialistProgressCard } from "../components/SpecialistProgressCard";
import { SpecialistBenefitsCard } from "../components/pb/PbEverywhere";
import { SpecialistCampaigns } from "../components/SpecialistCampaigns";
import { BetaFeedbackEntry } from "../components/BetaFeedbackWidget";
import { SpecialistEntryHome } from "./dashboard/SpecialistEntryHome";

export const SpecialistDashboard = () => {
  const { user, refreshUser } = useAuth();
  const tierInfo = useTier();
  const [requests, setRequests] = useState([]);
  const [notifs, setNotifs] = useState([]);
  const [chatRequest, setChatRequest] = useState(null);
  const [showDocs, setShowDocs] = useState(false);
  const [disputeFor, setDisputeFor] = useState(null);
  const [proposePhaseFor, setProposePhaseFor] = useState(null);
  const [showPortfolio, setShowPortfolio] = useState(false);
  const [showNewProject, setShowNewProject] = useState(false);
  const [tab, setTab] = useState(() => {
    const t = new URLSearchParams(window.location.search).get("tab");
    return ["opportunities", "jobs", "notifications", "settings"].includes(t) ? t : "opportunities";
  });
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("tab")) {
      window.history.replaceState(null, "", "/specialist");
    }
  }, []);
  const [searchQ, setSearchQ] = useState("");
  const [urgentOnly, setUrgentOnly] = useState(false);
  const [acceptingReq, setAcceptingReq] = useState(null);  // {id, title} for ScheduleProposalModal
  const [timelineRequestId, setTimelineRequestId] = useState(null);
  const [entryFull, setEntryFull] = useState(() => localStorage.getItem("pm_spec_full") === "1");
  const entryMode = tierInfo.tier === "ENTRY" && !entryFull;

  const [xosLayout, setXosLayout] = useState(null);
  const [xosHidden, setXosHidden] = useState([]);
  useEffect(() => {
    axios.get(`${API}/xos/layout/specialist_home`).then(r => setXosLayout(r.data.items || null)).catch(() => {});
    axios.get(`${API}/ui-rules/my`).then(r => setXosHidden(r.data.hidden || [])).catch(() => {});
  }, []);

  const specOpenedRef = useRef(false);
  const load = () => axios.get(`${API}/requests`).then(r => setRequests(r.data)).catch(() => {});
  const loadNotifs = () => axios.get(`${API}/notifications`).then(r => setNotifs(r.data)).catch(() => {});
  useEffect(() => {
    if (user) {
      claimPendingInvite();
      // Funnel comercial (etapa 5): specialistul a deschis zona de leads
      if (!specOpenedRef.current) {
        specOpenedRef.current = true;
        import("../lib/analytics").then(({ trackIntent }) => trackIntent("specialist_flow_opened")).catch(() => {});
      }
      load();
      loadNotifs();
      const interval = setInterval(loadNotifs, 30000);
      return () => clearInterval(interval);
    }
  }, [user]);

  const openAccept = (r) => setAcceptingReq({ id: r.id, title: r.title, feeWaived: !!r.lead_fee_waived && r.direct_specialist_id === user?.id });
  const start = async (id) => { try { await axios.post(`${API}/requests/${id}/start`); load(); } catch (e) { alert(formatApiError(e)); } };
  const complete = async (id) => { try { await axios.post(`${API}/requests/${id}/complete`); load(); } catch (e) { alert(formatApiError(e)); } };

  const open = requests.filter(r => r.status === "open").sort((a, b) => (b.direct_specialist_id === user?.id ? 1 : 0) - (a.direct_specialist_id === user?.id ? 1 : 0));
  const mine = requests.filter(r => r.specialist_id === user?.id);
  const filtered = (list) => {
    let out = list;
    if (urgentOnly) out = out.filter(r => r.priority === "urgent");
    if (searchQ) out = out.filter(r => (r.title + r.description + (r.category || "")).toLowerCase().includes(searchQ.toLowerCase()));
    // Auto-sort: urgent first, then newest
    return [...out].sort((a, b) => {
      const ua = a.priority === "urgent" ? 1 : 0;
      const ub = b.priority === "urgent" ? 1 : 0;
      if (ua !== ub) return ub - ua;
      return (b.created_at || "").localeCompare(a.created_at || "");
    });
  };
  const unreadNotifs = notifs.filter(n => !n.read).length;
  const now = new Date();
  const monthlyEarnings = mine
    .filter(r => r.status === "confirmed" && String(r.confirmed_at || r.updated_at || r.created_at || "").slice(0, 7) === now.toISOString().slice(0, 7))
    .reduce((s, r) => s + (Number(r.final_price ?? r.price ?? r.budget_estimate) || 0), 0);

  const allTabs = [
    { id: "opportunities", label: "Oportunități", icon: Target, badge: open.length, minTier: "ENTRY" },
    { id: "jobs", label: "Lucrările mele", icon: ClipboardCheck, badge: mine.filter(r => r.status !== "confirmed").length, minTier: "ENTRY" },
    { id: "notifications", label: "Notificări", icon: Bell, badge: unreadNotifs, minTier: "JUNIOR" },
    { id: "settings", label: "Setări", icon: SettingsIcon, badge: 0, minTier: "ENTRY" },
  ];
  // Progressive disclosure: hide tabs the specialist hasn't unlocked yet
  const tabs = allTabs.filter(t => tierInfo.isAtLeast(t.minTier));

  const title = {
    opportunities: "Oportunități",
    jobs: "Lucrările mele",
    notifications: "Notificări",
    settings: "Setări",
  }[tab];

  return (
    <DashLayout role="specialist" title={title} bottomNav={<BottomNav tabs={tabs} active={tab} onChange={setTab} dataPrefix="spec-tab" />}>
      {entryMode && tab === "opportunities" && (
        <SpecialistEntryHome user={user} open={filtered(open)} mine={mine} onAccept={openAccept}
          onVerify={() => setShowDocs(true)} onGoJobs={() => setTab("jobs")}
          onSwitchFull={() => { localStorage.setItem("pm_spec_full", "1"); setEntryFull(true); }} />
      )}
      {/* PPOS P3a-M4: MaturityCard eliminat — al doilea sistem de progres; unicul e SpecialistProgressCard */}
      <TierCelebrationBanner />
      {!entryMode && !user?.verified && (
        <PMCard accent="warning" className="mb-6 !bg-amber-500/5 !border-amber-500/30 pm-fade-in" testid="verify-banner">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <div className="text-sm font-semibold">Verifică-ți contul</div>
                <div className="text-xs text-stone-400">Încarcă documentele pentru badge &quot;VERIFIED&quot; și acces complet.</div>
              </div>
            </div>
            <PMPillButton variant="primary" size="sm" onClick={() => setShowDocs(true)} testid="upload-docs-cta">
              Începe
            </PMPillButton>
          </div>
        </PMCard>
      )}

      {/* PPOS P3c — Mission Control: Main Workspace (8) + Right Context Panel (4) */}
      {!entryMode && tab === "opportunities" && (() => {
        const xosWidgets = {
          today_summary: (
            <div className="mb-6 pm-fade-in" data-testid="spec-today-summary">
              <h3 className="text-[11px] font-bold uppercase tracking-[0.22em] mb-3" style={{ color: "var(--pm-text-muted)" }}>Astăzi ai</h3>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Cereri noi", value: open.length, onClick: () => document.querySelector('[data-tour="specialist-leads"]')?.scrollIntoView({ behavior: "smooth" }), testid: "spec-today-open" },
                  { label: "Lucrări în lucru", value: mine.filter(r => r.status !== "confirmed").length, onClick: () => setTab("jobs"), testid: "spec-today-active" },
                  { label: "Notificări necitite", value: unreadNotifs, onClick: () => setTab("notifications"), testid: "spec-today-notifs" },
                  { label: "Încasări luna aceasta", value: monthlyEarnings.toLocaleString("ro"), suffix: "RON", accent: true, onClick: () => setTab("jobs"), testid: "spec-today-earnings" },
                ].map(({ label, value, suffix, accent, onClick, testid }) => (
                  <button key={testid} onClick={onClick} data-testid={testid}
                    className="text-left rounded-2xl border p-4 lg:p-5 transition-transform duration-300 hover:-translate-y-1"
                    style={{
                      background: accent ? "rgba(204,255,0,0.07)" : "var(--pm-surface)",
                      borderColor: accent ? "rgba(204,255,0,0.3)" : "var(--pm-outline)",
                    }}>
                    <div className="text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--pm-text-muted)" }}>{label}</div>
                    <div className="mt-2 xos-num text-3xl lg:text-4xl leading-none" style={{ color: accent ? "var(--pm-accent-ink)" : "var(--pm-text)" }}>
                      {value}{suffix && <span className="text-sm font-semibold ml-1.5 align-baseline" style={{ color: "var(--pm-text-variant)" }}>{suffix}</span>}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ),
          // PPOS: Cockpit-ul de pipeline se deblochează la ADVANCED+ (progressive disclosure)
          cockpit: ["ADVANCED", "PREMIUM", "TOP"].includes(user?.tier) ? <SpecialistCockpit onGo={(dest) => (dest === "opportunities" ? window.scrollTo({ top: 0 }) : setTab(dest))} /> : null,
          quests: tierInfo.canSeeQuests ? <QuestPanel hideActive={mine.length > 0 || (user?.jobs_completed || 0) > 0} /> : null,
          pb_benefits: <SpecialistBenefitsCard />,
          tier_tools: null,
          tier_progress: (
            <SpecialistProgressCard
              user={user}
              mine={mine}
              onGoLeads={() => document.querySelector('[data-tour="specialist-leads"]')?.scrollIntoView({ behavior: "smooth" })}
              className="mb-4"
            />
          ),
        };
        const defaultOrder = [
          { id: "today_summary", enabled: true }, { id: "cockpit", enabled: true },
          { id: "pb_benefits", enabled: true },
          { id: "quests", enabled: true }, { id: "tier_tools", enabled: true }, { id: "tier_progress", enabled: true },
        ];
        // layout-urile stocate primesc automat widget-urile noi din default (altfel rămân invizibile)
        const order = xosLayout
          ? [...xosLayout, ...defaultOrder.filter(d => !xosLayout.some(w => w.id === d.id))]
          : defaultOrder;
        const rail = order
          .filter(w => w.enabled && !xosHidden.includes(`widget:${w.id}`))
          .map(w => <React.Fragment key={w.id}>{xosWidgets[w.id] || null}</React.Fragment>);
        return (
        <div className="lg:grid lg:grid-cols-12 lg:gap-8 lg:items-start" data-testid="spec-workspace">
          {/* Mobil: KPI-urile „Astăzi ai" primele (task-first). Desktop: rail dreapta sticky. */}
          <aside className="lg:col-span-4 lg:col-start-9 lg:row-start-1 lg:sticky lg:top-6" data-testid="spec-context-panel">{rail}</aside>
          <div className="lg:col-span-8 lg:col-start-1 lg:row-start-1 min-w-0">
          {/* Welcome hero (only ADVANCED+) */}
          {user?.verified && tierInfo.canSeeBentoHero && user?.tier && user.tier !== "ENTRY" && (
            <PMCardPrimary className="mb-6 pm-fade-in">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                  <PMChip variant="primary" className="!bg-[var(--pm-on-primary-container)] !text-[var(--pm-primary-container)] !border-transparent mb-2">
                    {user.tier} SPECIALIST
                  </PMChip>
                  <h2 className="text-2xl md:text-3xl font-bold text-[var(--pm-on-primary-container)] mb-1">
                    Salut, {user.name?.split(" ")[0] || "specialist"}!
                  </h2>
                  <div className="flex items-center gap-3 text-sm text-[var(--pm-on-primary-container)] opacity-80">
                    <span className="flex items-center gap-1"><Star className="w-4 h-4 fill-current" /> {user?.rating || "—"}</span>
                    <span className="w-1 h-1 rounded-full bg-current opacity-50" />
                    <span>{user?.reviews_count || 0} recenzii</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <Link to="/specialist/capabilities" data-testid="link-capabilities">
                    <PMPillButton variant="on-container" icon={Layers}>Capabilitățile mele</PMPillButton>
                  </Link>
                  {user?.tier === "PREMIUM" && (
                    <Link to="/specialist/premium-profile" data-testid="link-premium-profile">
                      <PMPillButton variant="on-container" icon={Crown}>Editează Profil Premium</PMPillButton>
                    </Link>
                  )}
                </div>
              </div>
            </PMCardPrimary>
          )}

          {/* Capability Engine — punct de acces permanent, indiferent de tier */}
          {!(user?.verified && tierInfo.canSeeBentoHero && user?.tier && user.tier !== "ENTRY") && (
            <PMCard className="mb-6 pm-fade-in" testid="spec-capabilities-banner">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-2xl bg-[var(--pm-primary-container)] flex items-center justify-center shrink-0">
                    <Layers className="w-5 h-5 text-[var(--pm-primary)]" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-semibold text-sm">Capabilitățile tale</div>
                    <div className="text-xs text-stone-400">Alege serviciile pe care le stăpânești — clienții și AI-ul te găsesc pe compatibilitate.</div>
                  </div>
                </div>
                <Link to="/specialist/capabilities" data-testid="link-capabilities-banner">
                  <PMPillButton variant="primary" icon={Layers}>Configurează</PMPillButton>
                </Link>
              </div>
            </PMCard>
          )}

          {/* ENTRY/JUNIOR: friendly intro card for newcomers */}
          {!tierInfo.canSeeStats && (
            <PMCard className="mb-6 pm-fade-in" testid="spec-newcomer-intro">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-2xl bg-[var(--pm-primary-container)] flex items-center justify-center shrink-0">
                  <Target className="w-6 h-6 text-[var(--pm-primary)]" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-base mb-1">Bun venit, {user?.name?.split(" ")[0] || "specialist"}!</h3>
                  <p className="text-sm text-stone-400 mb-3">
                    Mai jos găsești oportunități noi. Acceptă-ți primul job ca să debloci ratings, stats și recompense.
                  </p>
                  <div className="flex gap-2 flex-wrap">
                    {!user?.verified && (
                      <PMPillButton variant="primary" size="sm" icon={FileCheck} onClick={() => setShowDocs(true)} testid="newcomer-upload-docs">
                        Verifică-mi contul
                      </PMPillButton>
                    )}
                    <PMPillButton variant="ghost" size="sm" onClick={() => document.querySelector('[data-tour="specialist-leads"]')?.scrollIntoView({behavior:"smooth"})}>
                      Vezi oportunități
                    </PMPillButton>
                  </div>
                </div>
              </div>
            </PMCard>
          )}

          <FilterBar searchQ={searchQ} setSearchQ={setSearchQ} urgentOnly={urgentOnly} setUrgentOnly={setUrgentOnly} urgentCount={open.filter(r => r.priority === "urgent").length} />

          <SpecialistCampaigns />

          <div className="space-y-3 mt-4 max-w-3xl pm-fade-in-delay-2" data-tour="specialist-leads">
            <PMSectionHeader title={`${filtered(open).length} oportunități`} />
            {filtered(open).length === 0 && (
              <PMEmptyState
                icon={Target}
                title="Niciun lead disponibil"
                description="Verifică din nou în câteva minute sau ajustează filtrele."
              />
            )}
            {filtered(open).map(r => (
              <PMCard
                key={r.id}
                accent={r.priority === "urgent" ? "urgent" : "default"}
                className={r.priority === "urgent" ? "animate-pulse-soft" : ""}
                testid={`open-${r.id}`}
              >
                <div className="flex justify-between items-start mb-2 gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      {r.priority === "urgent" && <PMChip variant="error" icon={Flame}>URGENT</PMChip>}
                      {r.direct_specialist_id === user?.id && <PMChip variant="success" icon={Star} testid={`direct-chip-${r.id}`}>Re-angajare directă · 0 RON</PMChip>}
                      <span className="text-[11px] text-stone-500">{r.client_name} · {r.property_name}</span>
                    </div>
                    <div className="font-semibold text-sm md:text-base">{r.title}</div>
                  </div>
                </div>
                <p className="text-xs md:text-sm text-stone-400 mb-3 line-clamp-2">{r.description}</p>
                {r.concept_render_url && (
                  <div className="mb-3" data-testid={`lead-concept-render-${r.id}`}>
                    <img src={`${process.env.REACT_APP_BACKEND_URL}${r.concept_render_url}`} alt="Concept validat" className="w-full h-32 object-cover rounded-xl border border-white/10" />
                    <div className="mt-1 text-[10px] text-emerald-300 flex items-center gap-1"><ImageIcon className="w-3 h-3" /> Concept de design validat atașat</div>
                  </div>
                )}
                <div className="flex justify-between items-center gap-2 flex-wrap">
                  <div className="text-xs text-stone-400">Estimat: <span className="text-white font-semibold">{r.budget_estimate} RON</span></div>
                  <PMPillButton variant="primary" size="sm" onClick={() => openAccept(r)} testid={`accept-${r.id}`}>
                    {r.direct_specialist_id === user?.id ? "Acceptă · GRATUIT" : "Acceptă · 45 RON"}
                  </PMPillButton>
                </div>
              </PMCard>
            ))}
          </div>
          </div>
        </div>
        );
      })()}

      {tab === "jobs" && (
        <>
          {user?.verified && (
            <div className="mb-4 flex justify-end gap-2 flex-wrap">
              {tierInfo.canSeePortfolio && (user?.service_categories || []).includes("interior_design") && (
                <PMPillButton variant="primary" size="sm" icon={Plus} onClick={() => setShowNewProject(true)} testid="new-project-btn">
                  Proiect coordonare
                </PMPillButton>
              )}
              {tierInfo.canSeePortfolio && (
                <PMPillButton variant="ghost" size="sm" icon={ImageIcon} onClick={() => setShowPortfolio(true)} testid="manage-portfolio-btn">
                  Portofoliu
                </PMPillButton>
              )}
              <PMPillButton variant="ghost" size="sm" icon={FileCheck} onClick={() => setShowDocs(true)} testid="manage-docs-btn">
                Documentele mele
              </PMPillButton>
            </div>
          )}
          {(user?.service_categories || []).includes("interior_design") && (
            <div className="mb-4">
              <ProjectListSection title="Proiectele tale de coordonare" />
            </div>
          )}
          <FilterBar searchQ={searchQ} setSearchQ={setSearchQ} urgentOnly={urgentOnly} setUrgentOnly={setUrgentOnly} urgentCount={open.filter(r => r.priority === "urgent").length} placeholder="Caută în lucrările tale..." />
          {/* PPOS Desktop Polish: densitate — 2 coloane pe desktop, stivă pe mobil */}
          <div className="mt-4 max-w-3xl mx-auto lg:max-w-none lg:mx-0">
            <PMSectionHeader title={`${filtered(mine).length} lucrări`} />
            {filtered(mine).length === 0 && (
              <PMEmptyState
                icon={ClipboardCheck}
                title="Niciun job acceptat"
                description="Acceptă o oportunitate pentru a începe."
              />
            )}
            <div className="space-y-3 mt-3 lg:grid lg:grid-cols-2 lg:gap-4 lg:space-y-0 lg:items-start">
            {filtered(mine).map(r => (
              <PMCard key={r.id} accent={r.disputed ? "warning" : r.status === "in_progress" ? "primary" : "default"} testid={`mine-${r.id}`}>
                <div className="flex justify-between items-start mb-2 gap-3">
                  <div className="font-semibold text-sm md:text-base flex-1 min-w-0">{r.title}</div>
                  <StatusBadge status={r.status} />
                </div>
                <div className="text-[11px] text-stone-500 mb-3">{r.client_name} · {r.escrow_amount ? `${r.escrow_amount} RON escrow` : "—"}</div>
                {r.property_address && (
                  <div className="mb-3"><NavigateButtons address={r.property_address} compact /></div>
                )}
                <LastActionBanner event={r.last_event} onClick={() => setTimelineRequestId(r.id)} />
                <div className="flex gap-2 flex-wrap">
                  <button onClick={() => setTimelineRequestId(r.id)} className="bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 py-2 px-3 rounded-full text-xs flex items-center gap-1" data-testid={`spec-timeline-${r.id}`} title="Vezi timeline complet">
                    <Clock className="w-3 h-3" /> Timeline
                  </button>
                  {r.status === "assigned" && (
                    <PMPillButton variant="ghost" size="sm" onClick={() => start(r.id)} testid={`start-${r.id}`}>
                      Pornește
                    </PMPillButton>
                  )}
                  {r.status === "in_progress" && (
                    <PMPillButton variant="primary" size="sm" icon={CheckCircle2} onClick={() => complete(r.id)} testid={`complete-${r.id}`}>
                      Marchează completă
                    </PMPillButton>
                  )}
                  {["assigned","in_progress","completed"].includes(r.status) && (
                    <PMPillButton variant="ghost" size="sm" icon={MessageSquare} onClick={() => setChatRequest(r.id)} testid={`spec-chat-${r.id}`}>
                      Chat
                    </PMPillButton>
                  )}
                  {["assigned","in_progress","completed"].includes(r.status) && !r.disputed && (
                    <button onClick={() => setDisputeFor(r)} className="bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 py-2 px-3 rounded-full text-xs flex items-center gap-1" data-testid={`spec-dispute-${r.id}`} title="Deschide dispută">
                      <AlertTriangle className="w-3 h-3" /> Dispută
                    </button>
                  )}
                </div>
                {r.disputed && <div className="mt-3 w-full bg-amber-500/15 border border-amber-500/40 text-amber-300 py-2 rounded-xl text-xs text-center font-medium">⚠ Dispută în analiză</div>}
                {r.category === "interior_design" && ["in_progress","completed","confirmed"].includes(r.status) && (
                  <button onClick={() => setProposePhaseFor(r.id)}
                    className="mt-3 w-full bg-purple-500/15 hover:bg-purple-500/25 text-purple-300 border border-purple-500/30 py-2 rounded-xl text-xs flex items-center justify-center gap-1"
                    data-testid={`propose-phase-${r.id}`}>
                    <Plus className="w-3.5 h-3.5" />Propune fază nouă
                  </button>
                )}
              </PMCard>
            ))}
            </div>
          </div>
        </>
      )}

      {tab === "notifications" && (
        <div className="space-y-2 max-w-2xl mx-auto" data-testid="notifications-zone">
          {notifs.length === 0 && (
            <PMEmptyState
              icon={Bell}
              title="Nicio notificare"
              description="Aici vor apărea actualizările pentru lucrările tale."
            />
          )}
          {notifs.map(n => (
            <button
              key={n.id}
              onClick={async () => { await axios.post(`${API}/notifications/${n.id}/read`).catch(() => {}); loadNotifs(); }}
              className={`w-full text-left bg-white/5 hover:bg-white/[0.08] transition-colors rounded-2xl p-4 ${!n.read ? "border border-[var(--pm-primary)]/40" : "border border-white/5"}`}
              data-testid={`notif-${n.id}`}
            >
              <div className="flex items-start gap-3">
                {!n.read && <div className="w-2 h-2 rounded-full bg-[var(--pm-primary)] mt-2 shrink-0" />}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold">{n.title}</div>
                  <div className="text-xs text-stone-400 mt-1">{n.message}</div>
                  <div className="text-[10px] text-stone-600 mt-2">{new Date(n.created_at).toLocaleString("ro-RO")}</div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {tab === "settings" && (
        <>
          <div className="max-w-2xl mx-auto mb-4 space-y-4">
            <ReferralHub variant="dark" />
            <BetaFeedbackEntry />
          </div>
          <SettingsPanel />
        </>
      )}

      {chatRequest && <ChatPanel requestId={chatRequest} onClose={() => setChatRequest(null)} />}
      {showDocs && <SpecialistDocumentsModal onClose={() => setShowDocs(false)} />}
      {disputeFor && <OpenDisputeModal requestId={disputeFor.id} requestTitle={disputeFor.title} onClose={() => setDisputeFor(null)} onOpened={() => load()} />}
      {proposePhaseFor && <ProposePhaseModal requestId={proposePhaseFor} onClose={() => setProposePhaseFor(null)} onProposed={() => load()} />}
      {showPortfolio && <PortfolioManagerModal onClose={() => setShowPortfolio(false)} />}
      {acceptingReq && <ScheduleProposalModal requestId={acceptingReq.id} requestTitle={acceptingReq.title} feeWaived={acceptingReq.feeWaived} onClose={() => setAcceptingReq(null)} onAccepted={async () => { import("../lib/analytics").then(({ trackIntent }) => trackIntent("specialist_action_taken")).catch(() => {}); await refreshUser(); load(); }} />}
      {timelineRequestId && <RequestTimelineModal requestId={timelineRequestId} onClose={() => setTimelineRequestId(null)} />}
      {showNewProject && <NewProjectModal onClose={() => setShowNewProject(false)} />}
    </DashLayout>
  );
};

// ============= NEW PROJECT MODAL (Designer creates coordination project) =============
const NewProjectModal = ({ onClose }) => {
  const [clients, setClients] = useState([]);
  const [form, setForm] = useState({ name: "", description: "", client_id: "", style: "modern", budget_estimate: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // Load past clients (clients who interacted with this specialist)
    axios.get(`${API}/requests`).then(r => {
      const seen = new Map();
      (r.data || []).forEach(req => {
        if (req.client_id && !seen.has(req.client_id)) {
          seen.set(req.client_id, { id: req.client_id, name: req.client_name });
        }
      });
      setClients([...seen.values()]);
    }).catch(() => setClients([]));
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.client_id) { alert("Selectează clientul."); return; }
    setBusy(true);
    try {
      const payload = { ...form, budget_estimate: form.budget_estimate ? parseFloat(form.budget_estimate) : null };
      const { data } = await axios.post(`${API}/projects`, payload);
      onClose();
      // Navigate to the newly created project workspace
      window.location.href = `/projects/${data.id}`;
    } catch (e) {
      alert(e?.response?.data?.detail || "Eroare creare proiect");
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-end sm:items-center justify-center p-3" onClick={onClose}>
      <form onSubmit={submit} onClick={e => e.stopPropagation()}
        className="bg-stone-950 border border-white/10 rounded-3xl p-5 w-full max-w-md space-y-3" data-testid="new-project-modal">
        <h3 className="font-serif text-xl">Proiect nou de coordonare</h3>
        <p className="text-xs text-stone-400">Creezi un workspace ClickUp-style unde adaugi clientul + specialiști (parchet, zugrăvit, faianță etc.) și aloci task-uri.</p>
        <input required placeholder="Nume proiect (ex: Renovare apartament Pipera)" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="new-proj-name" />
        <textarea rows={3} placeholder="Descriere (opțional)" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" />
        <select required value={form.client_id} onChange={e => setForm({ ...form, client_id: e.target.value })}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="new-proj-client">
          <option value="">— Selectează client —</option>
          {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        {clients.length === 0 && (
          <div className="text-[11px] text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded-xl p-2">
            Nu ai clienți încă. Acceptă mai întâi o lucrare ca să apară clienții aici.
          </div>
        )}
        <div className="grid grid-cols-2 gap-2">
          <select value={form.style} onChange={e => setForm({ ...form, style: e.target.value })}
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm">
            <option value="modern">Modern</option>
            <option value="scandinavian">Scandinavian</option>
            <option value="minimalist">Minimalist</option>
            <option value="industrial">Industrial</option>
            <option value="boho">Boho</option>
            <option value="classic">Clasic</option>
          </select>
          <input type="number" placeholder="Buget (RON)" value={form.budget_estimate} onChange={e => setForm({ ...form, budget_estimate: e.target.value })}
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" />
        </div>
        <div className="flex gap-2 pt-2">
          <button type="button" onClick={onClose} className="flex-1 py-2 bg-white/5 rounded-full text-sm">Anulează</button>
          <button type="submit" disabled={busy || !form.client_id} className="pm-btn pm-btn-primary flex-1" data-testid="new-proj-submit">
            {busy ? "..." : "Creează proiect"}
          </button>
        </div>
      </form>
    </div>
  );
};

const FilterBar = ({ searchQ, setSearchQ, urgentOnly, setUrgentOnly, urgentCount = 0, placeholder = "Caută oportunități..." }) => (
  <div className="max-w-3xl mx-auto sticky top-[72px] z-10">
    <div className="pm-card-glass !p-3">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
          <input
            type="text" placeholder={placeholder} value={searchQ} onChange={e => setSearchQ(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-full pl-10 pr-3 py-2.5 text-sm focus:outline-none focus:border-[var(--pm-primary)]/50 transition-colors"
            data-testid="spec-search"
          />
        </div>
        <button
          onClick={() => setUrgentOnly?.(!urgentOnly)}
          className={`shrink-0 px-4 py-2.5 rounded-full text-xs font-semibold border transition-all flex items-center gap-1.5 ${urgentOnly ? "bg-red-500/20 border-red-500/50 text-red-300 shadow-[0_0_24px_-8px_rgba(239,68,68,0.5)]" : "bg-white/5 border-white/10 text-stone-400 hover:text-white"}`}
          data-testid="spec-urgent-toggle"
          title={urgentOnly ? "Click pentru a vedea toate joburile" : "Click pentru a vedea doar joburile urgente"}
        >
          <Flame className="w-3.5 h-3.5" /> Urgent {urgentCount > 0 && <span className="ml-0.5 text-[10px] bg-red-500 text-white rounded-full px-1.5">{urgentCount}</span>}
        </button>
      </div>
    </div>
  </div>
);
