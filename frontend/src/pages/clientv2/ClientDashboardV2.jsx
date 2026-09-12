import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Home, Plus, Wrench, Building2, Settings, Bell, ChevronDown, Shield, ChevronRight, Gift } from "lucide-react";
import { useAuth, formatApiError } from "../../auth";
import { API } from "../DashShared";
import { GREEN, Sheet } from "./ui";
import { ThemeSwitcher } from "../../components/ThemeSwitcher";
import { HomeV2, HomeSkeleton, HomeIntroTour } from "./HomeV2";
import { JobsV2 } from "./JobsV2";
import { PropertyHubV2, WalletSheet } from "./PropertyHubV2";
import { RequestWizard } from "./RequestWizard";
import { ChatPanel } from "../ChatPanel";
import { ReviewModal, PropertyManagerModal } from "../Components";
import { TwoFASetupModal, PropertyTimelineModal } from "../Marketplace";
import { OpenDisputeModal } from "../AdminModals";
import { ClientTwinViewerModal } from "../ClientTwinViewer";
import DigitalTwinViewer from "../../components/DigitalTwinViewer";
import { RequestTimelineModal } from "../ActivityTimeline";
import { SettingsPanel } from "../SettingsPanel";
import HouseHealthCard from "../HouseHealthCard";
import { HelpButton } from "../../components/HelpButton";
import { BetaFeedbackEntry } from "../../components/BetaFeedbackWidget";
import { SubscriptionNotice } from "../../components/SubscriptionNotice";
import { ReferralHub, claimPendingInvite } from "../../components/ReferralHub";
import { TrustedSpecialists } from "../../components/TrustedSpecialists";
import { useMobileDock } from "../../components/floating";
import { MaintenanceCalendar } from "../../components/MaintenanceCalendar";
import { BuildingHub } from "../../components/BuildingHub";
import { PostJobGrowthLoop } from "../../components/PostJobGrowthLoop";
import { PropBenefitsHub } from "../../components/PropBenefitsHub";

const NAV = [[Home, "Acasă", "home"], [Wrench, "Lucrări", "jobs"], [Plus, "Solicită", "request"], [Building2, "Propr.", "property"], [Settings, "Setări", "settings"]];
const TITLES = { home: null, jobs: "Lucrările mele", property: "Proprietatea mea", settings: "Setări", benefits: "Beneficiile mele" };

export default function ClientDashboardV2() {
  useMobileDock();
  const { user, refreshUser, logout } = useAuth();
  const flowOpenedRef = useRef(false);
  const [loaded, setLoaded] = useState(false);
  const [properties, setProperties] = useState([]);
  const [requests, setRequests] = useState([]);
  const [notifs, setNotifs] = useState([]);
  const [selectedPropId, setSelectedPropId] = useState(null);
  const [offersCount, setOffersCount] = useState(0);
  const [tab, setTab] = useState("home");
  // Deep-link secțiune în Cartea casei (CTA-uri de activare document din Acasă)
  const [propSection, setPropSection] = useState(null);
  const [propSectionNonce, setPropSectionNonce] = useState(0);
  // modale / sheets
  const [showWizard, setShowWizard] = useState(false);
  const [showNotifs, setShowNotifs] = useState(false);
  const [showWallet, setShowWallet] = useState(false);
  const [showHealth, setShowHealth] = useState(false);
  const [showPropManager, setShowPropManager] = useState(false);
  const [show2FA, setShow2FA] = useState(false);
  const [showTwin, setShowTwin] = useState(false);
  const [twinOverride, setTwinOverride] = useState(null);
  const [chatRequest, setChatRequest] = useState(null);
  const [reviewFor, setReviewFor] = useState(null);
  const [growthLoopFor, setGrowthLoopFor] = useState(null);
  const [disputeFor, setDisputeFor] = useState(null);
  const [timelineRequestId, setTimelineRequestId] = useState(null);
  const [propTimelineFor, setPropTimelineFor] = useState(null);

  const loadRequests = () => axios.get(`${API}/requests`).then(r => setRequests(r.data)).catch(() => {});
  const loadNotifs = () => axios.get(`${API}/notifications`).then(r => setNotifs(r.data)).catch(() => {});
  const loadProps = () => axios.get(`${API}/properties`).then(r => setProperties(r.data)).catch(() => {});

  // CTA-uri „Adaugă primul document" (banner Acasă + Copilot „Fă pasul acum") → direct în Cartea casei
  useEffect(() => {
    const openBook = () => {
      setPropSection("carte");
      setPropSectionNonce(n => n + 1);
      setTab("property");
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("propmanage:open-house-book", openBook);
    return () => window.removeEventListener("propmanage:open-house-book", openBook);
  }, []);

  useEffect(() => {
    if (!user || user === false) return;
    claimPendingInvite();
    // Funnel comercial (etapa 1): client a intrat pe /client — semnalul propriu (trackIntent), o dată/mount
    if (!flowOpenedRef.current) {
      flowOpenedRef.current = true;
      import("../../lib/analytics").then(({ trackIntent }) => trackIntent("client_flow_opened")).catch(() => {});
    }
    Promise.all([loadProps(), loadRequests(), loadNotifs()]).finally(() => setLoaded(true));
    const interval = setInterval(loadNotifs, 30000);
    // Deep-link taburi (onboarding checklist etc.): /client?tab=home|jobs|property|settings|request
    const params = new URLSearchParams(window.location.search);
    const wantedTab = params.get("tab");
    const bInvite = params.get("binvite");
    if (bInvite) {
      localStorage.setItem("pm_building_invite", bInvite);
      params.delete("binvite");
      setTab("property");
      const rest0 = params.toString();
      window.history.replaceState(null, "", `/client${rest0 ? `?${rest0}` : ""}`);
    }
    if (wantedTab) {
      if (wantedTab === "request") setShowWizard(true);
      else if (["home", "jobs", "property", "settings", "benefits"].includes(wantedTab)) setTab(wantedTab);
      params.delete("tab");
      const rest = params.toString();
      window.history.replaceState(null, "", `/client${rest ? `?${rest}` : ""}`);
    }
    // Stripe return polling (identic cu dashboardul clasic)
    const payParams = new URLSearchParams(window.location.search);
    if (payParams.get("payment") === "success" && payParams.get("session_id")) {
      const sessionId = payParams.get("session_id");
      let attempts = 0;
      const poll = async () => {
        if (attempts >= 6) { alert("Verificarea plății a expirat. Verifică în câteva minute."); window.history.replaceState(null, "", "/client"); return; }
        attempts++;
        try {
          const { data } = await axios.get(`${API}/payments/status/${sessionId}`);
          if (data.payment_status === "paid") {
            await loadRequests(); await refreshUser();
            alert(data.demo_mode ? "Plată confirmată (demo). Fondurile sunt în escrow." : "Plată confirmată! Fondurile sunt în escrow.");
            window.history.replaceState(null, "", "/client"); return;
          }
          if (data.status === "expired") { alert("Sesiunea de plată a expirat."); window.history.replaceState(null, "", "/client"); return; }
          setTimeout(poll, 2000);
        } catch { setTimeout(poll, 2500); }
      };
      poll();
    } else if (params.get("payment") === "cancelled") {
      alert("Plata a fost anulată."); window.history.replaceState(null, "", "/client");
    }
    return () => clearInterval(interval);
  }, [user]);

  const prop = properties.find(p => p.id === selectedPropId) || properties[0];
  const activeReq = requests.filter(r => r.status !== "confirmed")[0];
  const unread = notifs.filter(n => !n.read).length;
  // PPOS P3a-M8: while a payment/confirmation is pending, the hero owns the ONLY primary CTA
  const txActive = requests.some(r => (r.status === "assigned" && !r.escrow_amount) || r.status === "completed");

  useEffect(() => {
    if (activeReq?.status === "open") {
      axios.get(`${API}/requests/${activeReq.id}/offers`).then(r => setOffersCount((r.data?.offers || r.data || []).length)).catch(() => setOffersCount(0));
    } else setOffersCount(0);
  }, [activeReq?.id, activeReq?.status]);

  const payEscrow = async (reqId) => {
    try {
      const { data } = await axios.post(`${API}/payments/checkout-session?request_id=${reqId}`);
      window.location.href = data.checkout_url;
    } catch (e) { alert(formatApiError(e)); }
  };

  const confirmRequest = async (id, r) => {
    try {
      await axios.post(`${API}/requests/${id}/confirm`);
      // Funnel comercial (etapa 7): flux finalizat — clientul a confirmat lucrarea
      import("../../lib/analytics").then(({ trackIntent }) => trackIntent("flow_completed")).catch(() => {});
      const { data } = await axios.get(`${API}/requests`);
      setRequests(data);
      await refreshUser();
      if (r?.specialist_id) setReviewFor(data.find(x => x.id === id) || r);
    } catch (e) { alert(formatApiError(e)); }
  };

  const markRead = async (id) => { await axios.post(`${API}/notifications/${id}/read`).catch(() => {}); loadNotifs(); };

  const actions = {
    payEscrow, confirmRequest, setChatRequest, setReviewFor, setDisputeFor, setTimelineRequestId,
    reloadRequests: loadRequests,
    openWizard: () => {
      if (prop) {
        // Funnel comercial (etapa 2): proprietate aleasă pentru o cerere reală
        import("../../lib/analytics").then(({ trackIntent }) => trackIntent("client_property_selected")).catch(() => {});
        setShowWizard(true);
      } else setShowPropManager(true);
    },
    openPropManager: () => setShowPropManager(true),
    openNotifs: () => setShowNotifs(true),
    openWallet: () => setShowWallet(true),
    openHealth: () => setShowHealth(true),
    openTwin: () => (prop ? setShowTwin(true) : setShowPropManager(true)),
    openPropTimeline: () => prop && setPropTimelineFor(prop.id),
    openAI: () => window.dispatchEvent(new CustomEvent("pm-open-ai")),
  };

  return (
    <div className="min-h-screen bg-[#FAFBFA] cv2-scope" data-testid="client-dashboard-v2">
      <div className="max-w-md lg:max-w-6xl mx-auto min-h-screen sm:border-x sm:border-slate-100 lg:border-0 relative pb-24 lg:pb-28 lg:px-4">
        {/* Header slim */}
        <div className="flex items-center gap-2.5 px-5 pt-5 pb-3" data-testid="v2-header">
          <span className="w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-black shrink-0" style={{ background: GREEN }}>
            {(user?.name || "C")[0].toUpperCase()}
          </span>
          <div className="min-w-0">
            <div className="text-sm font-black text-slate-900 leading-none truncate">
              {(() => { const h = new Date().getHours(); return h < 12 ? "Bună dimineața" : h < 18 ? "Bună ziua" : "Bună seara"; })()}, {user?.name?.split(" ")[0] || ""}
            </div>
            {prop && (
              <button onClick={() => setTab("property")} className="mt-1 flex items-center gap-0.5 text-[11px] font-semibold text-slate-400">
                {prop.name} <ChevronDown className="w-3 h-3" />
              </button>
            )}
          </div>
          <button onClick={() => setShowNotifs(true)} aria-label="Notificări" className="ml-auto relative w-10 h-10 rounded-full bg-slate-50 border border-slate-100 flex items-center justify-center shrink-0" data-testid="v2-bell">
            <Bell style={{ width: 18, height: 18 }} className="text-slate-600" />
            {unread > 0 && <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full text-white text-[9px] font-black flex items-center justify-center" style={{ background: GREEN }} data-testid="v2-bell-badge">{unread}</span>}
          </button>
          <HelpButton light />
          <ThemeSwitcher />
        </div>
        {/* Desktop: taburi mari + CTA „Solicită ofertă" proeminent (Legea lui Hick) */}
        <div className="hidden lg:flex items-center gap-2 px-5 pb-4" data-testid="v2-desktop-nav">
          {NAV.filter(([, , id]) => id !== "request").map(([Icon, label, id]) => (
            <button key={id} onClick={() => { window.scrollTo({ top: 0 }); setTab(id); }} data-testid={`v2-desktop-nav-${id}`}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-bold transition-colors ${tab === id ? "bg-slate-900 text-white" : "bg-slate-50 text-slate-600 border border-slate-100 hover:bg-slate-100"}`}>
              <Icon style={{ width: 18, height: 18 }} /> {label === "Propr." ? "Proprietăți" : label}
            </button>
          ))}
          <button onClick={() => { window.scrollTo({ top: 0 }); setTab("benefits"); }} data-testid="v2-desktop-nav-benefits"
            className={`flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-bold transition-colors ${tab === "benefits" ? "bg-slate-900 text-white" : "bg-slate-50 text-slate-600 border border-slate-100 hover:bg-slate-100"}`}>
            <Gift style={{ width: 18, height: 18 }} /> Beneficii
          </button>
          {!(tab === "home" && properties.length === 0) && (
          <button onClick={() => actions.openWizard()} data-testid="v2-desktop-cta"
            className={`ml-auto flex items-center gap-2 px-6 py-3 rounded-full text-sm font-black transition-transform ${txActive
              ? "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50"
              : "text-black shadow-[0_12px_36px_-12px_rgba(204,255,0,0.55)] hover:scale-[1.02]"}`}
            style={txActive ? undefined : { background: "#ccff00" }}>
            <Plus style={{ width: 18, height: 18 }} strokeWidth={2.6} /> {prop ? "Solicită ofertă" : "Adaugă proprietatea"}
          </button>
          )}
        </div>

        {TITLES[tab] && <h1 className="px-5 pb-3 xos-display text-2xl lg:text-[38px] font-medium lg:font-bold tracking-tight text-slate-900">{TITLES[tab]}</h1>}

        {/* Subscription lifecycle notice (expired / cancelled_grace) — reused across tabs */}
        <div className="px-5 pb-3 lg:max-w-3xl"><SubscriptionNotice /></div>

        {tab === "home" && (!loaded ? <HomeSkeleton /> : <HomeV2 user={user} prop={prop} properties={properties} requests={requests} notifs={notifs} offersCount={offersCount} go={setTab} actions={actions} />)}
        {tab === "home" && loaded && <HomeIntroTour />}
        {tab === "jobs" && <div className="lg:max-w-3xl"><JobsV2 requests={requests} actions={actions} /><TrustedSpecialists properties={properties} onRebooked={loadRequests} /></div>}
        {/* PPOS P3d: Property Hub folosește tot spațiul pe desktop (record page) */}
        {tab === "property" && (<>
          <PropertyHubV2 user={user} prop={prop} properties={properties} setSelectedPropId={setSelectedPropId} actions={actions} initialSection={propSection} sectionNonce={propSectionNonce} />
          <MaintenanceCalendar properties={properties} prop={prop} onRequestCreated={loadRequests} />
          <BuildingHub properties={properties} onRequestsChanged={loadRequests} />
        </>)}
        {tab === "benefits" && <PropBenefitsHub />}
        {tab === "settings" && (
          <div className="px-5 pb-8 space-y-2 lg:max-w-3xl" data-testid="v2-settings-view">
            <button onClick={() => { window.scrollTo({ top: 0 }); setTab("benefits"); }} data-testid="v2-set-benefits"
              className="w-full flex items-center gap-3 rounded-2xl border border-slate-100 bg-white p-3.5 shadow-sm text-left lg:hidden">
              <span className="w-10 h-10 rounded-xl bg-[#ecfdf3] flex items-center justify-center"><Gift className="w-5 h-5 text-[#166534]" /></span>
              <span className="text-sm font-black text-slate-900 flex-1">Beneficiile mele</span>
              <ChevronRight className="w-4 h-4 text-slate-300" />
            </button>
            <ReferralHub variant="light" />
            <BetaFeedbackEntry light />
            <button onClick={() => setShow2FA(true)} data-testid="v2-set-2fa"
              className="w-full flex items-center gap-3 rounded-2xl border border-slate-100 bg-white p-3.5 shadow-sm text-left">
              <span className="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center"><Shield className="w-5 h-5 text-slate-500" /></span>
              <span className="text-sm font-black text-slate-900 flex-1">Securitate (2FA)</span>
              <ChevronRight className="w-4 h-4 text-slate-300" />
            </button>
            <div className="pt-2 rounded-3xl bg-stone-900 p-4" data-testid="v2-settings-legacy-panel"><SettingsPanel /></div>
            <button onClick={async () => { await logout(); window.location.href = "/login"; }} data-testid="v2-logout"
              className="w-full py-3.5 rounded-full border-2 border-rose-100 text-sm font-bold text-rose-500 bg-white active:scale-[0.98] transition-transform">
              Deconectare
            </button>
            <p className="text-center text-[10px] text-slate-300 pt-1">PropManage · Client dashboard V2</p>
          </div>
        )}

        {/* Mobile: spațiu rezervat cât timp cookie banner-ul e deschis (nu acoperă CTA-uri) */}
        <div aria-hidden style={{ height: "var(--pm-cookie-h, 0px)" }} className="lg:hidden" data-testid="v2-cookie-spacer" />

        {/* Bottom nav — 5, FAB accent central (doar mobil; desktop are taburile de sus) */}
        <div className="lg:hidden fixed bottom-0 left-0 right-0 z-40 xos-dock" data-testid="v2-bottom-nav">
          <div className="max-w-md mx-auto grid grid-cols-5">
            {NAV.map(([Icon, label, id]) => (
              <button key={id} onClick={() => { window.scrollTo({ top: 0 }); (id === "request" ? actions.openWizard() : setTab(id)); }} data-testid={`v2-nav-${id}`} className="flex flex-col items-center gap-1 pt-2.5 pb-3">
                {id === "request" ? (
                  <span className="w-[52px] h-[52px] -mt-7 rounded-full flex items-center justify-center shadow-[0_10px_32px_-10px_rgba(204,255,0,0.6)]" style={{ background: "#ccff00" }}>
                    <Icon className="w-6 h-6 text-black" strokeWidth={2.5} />
                  </span>
                ) : (
                  <Icon className={`w-6 h-6 ${tab === id ? "text-[#166534]" : "text-slate-300"}`} strokeWidth={tab === id ? 2.4 : 2} />
                )}
                <span className={`text-[10px] font-bold ${tab === id ? "text-[#166534]" : "text-slate-400"}`}>{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Sheets & modale */}
        {showNotifs && (
          <Sheet title="Notificări" onClose={() => setShowNotifs(false)} testid="v2-notifs-sheet">
            {notifs.length === 0 && <p className="text-center text-sm text-slate-400 py-8">Nicio notificare încă.</p>}
            <div className="space-y-2">
              {notifs.map(n => (
                <button key={n.id} onClick={() => markRead(n.id)} data-testid={`v2-notif-${n.id}`}
                  className={`w-full text-left rounded-2xl p-3.5 border ${n.read ? "border-slate-100 bg-white" : "border-[#34C759]/40 bg-[#34C759]/5"}`}>
                  <div className="text-xs font-black text-slate-900">{n.title}</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">{n.message}</div>
                  <div className="text-[9px] text-slate-400 mt-1">{new Date(n.created_at).toLocaleString("ro-RO")}</div>
                </button>
              ))}
            </div>
          </Sheet>
        )}
        {showWallet && <WalletSheet user={user} onClose={() => setShowWallet(false)} />}
        {showHealth && (
          <Sheet title="House Health" onClose={() => setShowHealth(false)} testid="v2-health-sheet">
            <HouseHealthCard />
          </Sheet>
        )}
        {showWizard && <RequestWizard property={prop} onCreated={(r) => setRequests(prev => [r, ...prev])} onClose={(dest) => { setShowWizard(false); if (dest === "jobs") setTab("jobs"); }} />}
        {showPropManager && <PropertyManagerModal properties={properties} onClose={() => setShowPropManager(false)} onChange={setProperties}
          onOpenTwin={(twinInfo) => { setTwinOverride(twinInfo); setShowPropManager(false); setShowTwin(true); }} />}
        {showTwin && (twinOverride || prop) && (() => {
          const t = twinOverride || { property_id: prop.id, property_name: prop.name };
          if (t.dt_project_id && t.model_url) {
            return <DigitalTwinViewer projectId={t.dt_project_id} modelUrl={t.model_url} projectName={t.property_name || t.dt_project_name}
              onClose={() => { setShowTwin(false); setTwinOverride(null); }} />;
          }
          return <ClientTwinViewerModal propertyId={t.property_id} propertyName={t.property_name} onClose={() => { setShowTwin(false); setTwinOverride(null); }} />;
        })()}
        {chatRequest && <ChatPanel requestId={chatRequest} onClose={() => setChatRequest(null)} />}
        {reviewFor && <ReviewModal requestId={reviewFor.id} specialistName={reviewFor.specialist_name} onClose={() => setReviewFor(null)}
          onSubmitted={async () => { await refreshUser(); loadRequests(); if (reviewFor?.specialist_id) setGrowthLoopFor(reviewFor); }} />}
        {growthLoopFor && <PostJobGrowthLoop job={growthLoopFor} onClose={() => setGrowthLoopFor(null)} />}
        {disputeFor && <OpenDisputeModal requestId={disputeFor.id} requestTitle={disputeFor.title} onClose={() => setDisputeFor(null)} onOpened={() => loadRequests()} />}
        {timelineRequestId && <RequestTimelineModal requestId={timelineRequestId} onClose={() => setTimelineRequestId(null)} />}
        {propTimelineFor && <PropertyTimelineModal propertyId={propTimelineFor} onClose={() => setPropTimelineFor(null)} />}
        {show2FA && <TwoFASetupModal onClose={() => setShow2FA(false)} currentlyEnabled={false} />}
      </div>
    </div>
  );
}
