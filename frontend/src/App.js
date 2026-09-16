import React, { useState, useEffect, useRef, lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Link, Navigate, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Home, Wrench, Shield, Wallet, Box, Users, AlertTriangle, CheckCircle2,
  ArrowRight, ArrowUpRight, Zap, Droplet, Wind, Building2, Coins, TrendingUp,
  Eye, Lock, Star, Sparkles, FileCheck, Gavel, ChevronRight, Play, Pause,
  Activity, Layers, Cpu, Award, MessageSquare, Camera, Bell, Plus, Minus, Languages, LogIn, LogOut, LayoutDashboard, ShieldCheck
} from "lucide-react";
import { AuthProvider, useAuth } from "./auth";
import { ServiceGate } from "./components/ServiceGate";
import { Toaster } from "sonner";
import { EntitlementToast } from "./components/EntitlementToast";
import { I18nProvider, useI18n } from "./i18n";
import { ThemeProvider } from "./contexts/ThemeContext";
import { DesignTokensProvider } from "./contexts/DesignTokensProvider";
import { useABTest } from "./ab";
import { LoginPage, RegisterPage } from "./pages/Auth";
import { EmailVerifyPage } from "./pages/EmailVerifyPage";
const ClientRequestOffersPage = lazy(() => import("./pages/ClientRequestOffersPage").then(m => ({ default: m.ClientRequestOffersPage })));
const PremiumProfileEditorPage = lazy(() => import("./pages/PremiumProfileEditorPage").then(m => ({ default: m.PremiumProfileEditorPage })));
import { CookieBanner } from "./components/CookieBanner";
import { BetaFeedbackWidget } from "./components/BetaFeedbackWidget";
import { AssistantDock } from "./components/AssistantDock";
import { ThemeToggle } from "./pages/DashShared";
const SpecialistDashboard = lazy(() => import("./pages/Dashboards").then(m => ({ default: m.SpecialistDashboard })));
const AdminDashboard = lazy(() => import("./pages/Dashboards").then(m => ({ default: m.AdminDashboard })));
const OperatorDashboard = lazy(() => import("./pages/Dashboards").then(m => ({ default: m.OperatorDashboard })));
import { AuthCallback } from "./pages/AuthCallback";
import { SpecialistProfile } from "./pages/SpecialistProfile";
import { PublicMarketplace } from "./pages/Marketplace";
import { MarketplaceLanding } from "./pages/MarketplaceLanding";
import { GhiduriIndex } from "./pages/GhiduriIndex";
import { GhidPage } from "./pages/GhidPage";
import { ProblemeIndex } from "./pages/ProblemeIndex";
import { ProblemaPage } from "./pages/ProblemaPage";
import { DesignInteriorPage } from "./pages/DesignInteriorPage";
import { HelpPage } from "./pages/HelpPage";
import { ProjectWorkspace } from "./pages/ProjectWorkspace";
import { PaymentSuccess } from "./pages/PaymentSuccess";
import { TutorialOverlay } from "./pages/TutorialOverlay";
import { RoleTour } from "./pages/RoleTour";
import { AIConciergeBubble } from "./components/AIConciergeBubble";
import { BookDemoModal } from "./pages/BookDemoModal";
import { LandingDemo3D } from "./components/LandingDemo3D";
const PublicDemoPage = lazy(() => import("./pages/PublicDemoPage").then(m => ({ default: m.PublicDemoPage })));
const AdminAuthHealthPage = lazy(() => import("./pages/admin/AdminAuthHealthPage").then(m => ({ default: m.AdminAuthHealthPage })));
const ResearchCoveragePage = lazy(() => import("./pages/admin/ResearchCoveragePage"));
const AdminSupportInboxPage = lazy(() => import("./pages/admin/AdminSupportInboxPage").then(m => ({ default: m.AdminSupportInboxPage })));
import { PrivacyPage, TermsPage, CookiePolicyPage } from "./pages/LegalPages";
const TrustCenterPage = lazy(() => import("./pages/TrustCenterPage").then(m => ({ default: m.TrustCenterPage })));
const PrivacyNoticesPage = lazy(() => import("./pages/PrivacyNoticesPage").then(m => ({ default: m.PrivacyNoticesPage })));
const StatusPage = lazy(() => import("./pages/StatusPage").then(m => ({ default: m.StatusPage })));
const DesignSystemShowcase = lazy(() => import("./pages/DesignSystemShowcase"));
const CommunityPage = lazy(() => import("./pages/CommunityPage"));
import { GDPRAuditBadge } from "./components/GDPRAuditBadge";
import { TrustStrip } from "./components/TrustStrip";
const DigitalTwinPage = lazy(() => import("./pages/DigitalTwinPage"));
const ReportApprovalPage = lazy(() => import("./pages/ReportApprovalPage"));
const KYCPage = lazy(() => import("./pages/KYCPage"));
const EstateBrowse = lazy(() => import("./pages/verified-estate/EstateBrowse").then(m => ({ default: m.EstateBrowse })));
const EstateDetail = lazy(() => import("./pages/verified-estate/EstateDetail").then(m => ({ default: m.EstateDetail })));
const SellMyProperty = lazy(() => import("./pages/verified-estate/SellMyProperty").then(m => ({ default: m.SellMyProperty })));
const VerifiedEstateAdmin = lazy(() => import("./pages/verified-estate/VerifiedEstateAdmin").then(m => ({ default: m.VerifiedEstateAdmin })));
const WhyUsPage = lazy(() => import("./pages/WhyUsPage"));
const AdminSettingsControl = lazy(() => import("./pages/admin/AdminSettingsControl"));
const AdminDocumentation = lazy(() => import("./pages/admin/AdminDocumentation"));
const QACopilotPage = lazy(() => import("./pages/admin/QACopilotPage"));
const AIControlCenterPage = lazy(() => import("./pages/admin/AIControlCenterPage"));
const DocsAIPage = lazy(() => import("./pages/DocsAIPage"));
const AIDevTeamPage = lazy(() => import("./pages/admin/AIDevTeamPage"));
const AISecurityCenterPage = lazy(() => import("./pages/admin/AISecurityCenterPage"));
const AutonomyEnginePage = lazy(() => import("./pages/admin/AutonomyEnginePage"));
const AutonomyOrchestratorPage = lazy(() => import("./pages/admin/AutonomyOrchestratorPage"));
const ConstructionIntelligencePage = lazy(() => import("./pages/admin/ConstructionIntelligencePage"));
const ControlTowerPage = lazy(() => import("./pages/admin/ControlTowerPage"));
const TwinPage = lazy(() => import("./pages/admin/TwinPage"));
const AdminHouseHealthPage = lazy(() => import("./pages/admin/AdminHouseHealthPage"));
const ManualTesterPage = lazy(() => import("./pages/admin/ManualTesterPage"));
const HouseHealthPage = lazy(() => import("./pages/HouseHealthPage"));
const HouseHealthUpgradeLazy = lazy(() => import("./pages/HouseHealthUpgradePage"));
const PricingPageLazy = lazy(() => import("./pages/PricingPage"));
const HouseHealthUpgradeSuccessLazy = lazy(() => import("./pages/HouseHealthUpgradePage").then(m => ({ default: m.HouseHealthUpgradeSuccess })));
const AdminTodoBoard = lazy(() => import("./pages/admin/AdminTodoBoard"));
const ExperienceSpacesPage = lazy(() => import("./pages/admin/ExperienceSpacesPage"));
const FutureIdeasVault = lazy(() => import("./pages/admin/FutureIdeasVault"));
const FounderGatePage = lazy(() => import("./pages/admin/FounderGatePage"));
const AIGovernancePage = lazy(() => import("./pages/admin/AIGovernancePage"));
const DesignAuditPage = lazy(() => import("./pages/admin/DesignAuditPage"));
const DesignStudioPage = lazy(() => import("./pages/admin/DesignStudioPage"));
const DesignIntelligencePage = lazy(() => import("./pages/admin/DesignIntelligencePage"));
const PlatformRoadmapPage = lazy(() => import("./pages/admin/PlatformRoadmapPage"));
const CommandCenterPage = lazy(() => import("./pages/admin/CommandCenterPage"));
const BusinessHealthPage = lazy(() => import("./pages/admin/BusinessHealthPage"));
const MarketplaceIntelPage = lazy(() => import("./pages/admin/MarketplaceIntelPage"));
const FinancialCockpitPage = lazy(() => import("./pages/admin/FinancialCockpitPage"));
const AutomationCenterPage = lazy(() => import("./pages/admin/AutomationCenterPage"));
const CEODashboardPage = lazy(() => import("./pages/admin/CEODashboardPage"));
const FirstRevenueWarRoom = lazy(() => import("./pages/admin/FirstRevenueWarRoom"));
const BetaCockpitPage = lazy(() => import("./pages/admin/BetaCockpitPage"));
const BetaIssuesPage = lazy(() => import("./pages/admin/BetaIssuesPage"));
const CapabilityEditorPage = lazy(() => import("./pages/CapabilityEditorPage"));
const OperationsCenter = lazy(() => import("./pages/admin/OperationsCenter"));
const KnowledgeCenter = lazy(() => import("./pages/admin/KnowledgeCenter"));
const EnterpriseExplorer = lazy(() => import("./pages/admin/EnterpriseExplorer"));
const ArchitectureNavigator = lazy(() => import("./pages/admin/ArchitectureNavigator"));
const EnterpriseHealthPage = lazy(() => import("./pages/admin/EnterpriseHealthPage"));
const RepairCenterPage = lazy(() => import("./pages/admin/RepairCenterPage"));
const AIBrainPage = lazy(() => import("./pages/admin/AIBrainPage"));
const PropBenefitsAdminPage = lazy(() => import("./pages/admin/PropBenefitsAdminPage"));
const StorageAdminPage = lazy(() => import("./pages/admin/StorageAdminPage"));
const ServiceProvidersPage = lazy(() => import("./pages/ServiceProvidersPage"));
const CeoBriefingPage = lazy(() => import("./pages/admin/CeoBriefingPage"));
const EvolutionCouncilPage = lazy(() => import("./pages/admin/EvolutionCouncilPage"));
const HealthScorePage = lazy(() => import("./pages/growth/HealthScorePage"));
const PublicPassportPage = lazy(() => import("./pages/PublicPassportPage"));
const BuyingChecklistPage = lazy(() => import("./pages/growth/BuyingChecklistPage"));
const NotificationCenterPage = lazy(() => import("./pages/admin/NotificationCenterPage"));
const UserTimelinePage = lazy(() => import("./pages/admin/UserTimelinePage"));
const AISearchPage = lazy(() => import("./pages/admin/AISearchPage"));
const InteriorDesignLanding = lazy(() => import("./pages/InteriorDesignLanding"));
const InteriorDesignAdminPage = lazy(() => import("./pages/admin/InteriorDesignAdminPage"));
const MenuManagerPage = lazy(() => import("./pages/admin/MenuManagerPage"));
const PageRegistryPage = lazy(() => import("./pages/admin/PageRegistryPage"));
const ConfigIOPage = lazy(() => import("./pages/admin/ConfigIOPage"));
const XOSBuilderPage = lazy(() => import("./pages/admin/XOSBuilderPage"));
const ServiceHubLanding = lazy(() => import("./pages/ServiceHubLanding"));
const FranchiseDashboard = lazy(() => import("./pages/FranchiseDashboard"));
const FranchiseApplyPage = lazy(() => import("./pages/FranchiseApplyPage"));
const SpecialistApplyPage = lazy(() => import("./pages/SpecialistApplyPage"));
const UIRulesPage = lazy(() => import("./pages/admin/UIRulesPage"));
const ContentManagerPage = lazy(() => import("./pages/admin/ContentManagerPage"));
const BugMemoryAggregatorPage = lazy(() => import("./pages/admin/BugMemoryAggregatorPage"));
const ArchitectureBoardPage = lazy(() => import("./pages/admin/ArchitectureBoardPage"));
const AIProductManagerPage = lazy(() => import("./pages/admin/AIProductManagerPage"));
const OperatingManualPage = lazy(() => import("./pages/admin/OperatingManualPage"));
const ExperienceTiersPage = lazy(() => import("./pages/admin/ExperienceTiersPage"));
const FeatureConfiguratorPage = lazy(() => import("./pages/admin/FeatureConfiguratorPage"));
const SpecialistProgressionPage = lazy(() => import("./pages/admin/SpecialistProgressionPage"));
const BIMoePage = lazy(() => import("./pages/admin/BIMoePage"));
const AnalyticsGrowthPage = lazy(() => import("./pages/admin/AnalyticsGrowthPage"));
const FunctionMap = lazy(() => import("./pages/admin/FunctionMap"));
const GrowthIntelligencePage = lazy(() => import("./pages/admin/GrowthIntelligencePage"));
const LeadIntelligencePage = lazy(() => import("./pages/admin/LeadIntelligencePage"));
const MarketingIntelligencePage = lazy(() => import("./pages/admin/MarketingIntelligencePage"));
const LearningEnginePage = lazy(() => import("./pages/admin/LearningEnginePage"));
const ITCollaboratorsHubPage = lazy(() => import("./pages/admin/ITCollaboratorsHubPage"));
const ITCopilotPage = lazy(() => import("./pages/admin/ITCopilotPage"));
const LegalAuditPage = lazy(() => import("./pages/admin/LegalAuditPage"));
const LegalSignPage = lazy(() => import("./pages/LegalSignPage"));
import LegalGate from "./components/LegalGate";
const CityPartnersPage = lazy(() => import("./pages/admin/CityPartnersPage"));
const CityPartnerProductsPage = lazy(() => import("./pages/admin/CityPartnerProductsPage"));
const CityPartnerDetailPage = lazy(() => import("./pages/admin/CityPartnerDetailPage"));
const MarketplacePartnersPage = lazy(() => import("./pages/admin/MarketplacePartnersPage"));
const StrategicPartnersDashboard = lazy(() => import("./pages/admin/StrategicPartnersDashboard"));
const MarketingDepartmentPage = lazy(() => import("./pages/admin/MarketingDepartmentPage"));
const DemoAccountsPage = lazy(() => import("./pages/admin/DemoAccountsPage"));
const AdminAccountsPage = lazy(() => import("./pages/admin/AdminAccountsPage"));
const DemoActivityPage = lazy(() => import("./pages/admin/DemoActivityPage"));
const PartnerDashboard = lazy(() => import("./pages/partner/PartnerDashboard"));
const MarketplacePartnerPortal = lazy(() => import("./pages/partner/MarketplacePartnerPortal"));
const ClientJuniorDashboard = lazy(() => import("./pages/dashboard/ClientJuniorDashboard"));
const ClientDashboardV2 = lazy(() => import("./pages/clientv2/ClientDashboardV2"));
const AdministratorWorkspace = lazy(() => import("./pages/AdministratorWorkspace"));
const ContractPage = lazy(() => import("./pages/ContractPage"));
const PreturiIndex = lazy(() => import("./pages/PreturiIndex"));
const PreturiPage = lazy(() => import("./pages/PreturiPage"));
import { trackPageView } from "@/lib/analytics";
import { useDynamicSEO } from "@/lib/useDynamicSEO";
import { HOUSE_HEALTH_AXIS, AXIS_DISCLAIMER } from "@/lib/houseHealthAxis";

const AnalyticsRouteTracker = () => {
  const location = useLocation();
  React.useEffect(() => {
    trackPageView(location.pathname + location.search);
    // AI Brain · Navigation Context (doar utilizatori autentificați, fire-and-forget)
    if (localStorage.getItem("pm_session_hint")) {
      fetch(`${process.env.REACT_APP_BACKEND_URL}/api/ai-brain/navigation`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: location.pathname }),
      }).catch(() => {});
    }
  }, [location.pathname, location.search]);
  React.useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);
  return null;
};
import { ImpersonationBanner } from "./components/ImpersonationBanner";
import { ExplainThis } from "./components/ExplainThis";
import { RoleThemeApplier } from "./components/RoleThemeApplier";
import { ErrorBoundary } from "./components/ErrorBoundary";
import SiteNav from "./components/SiteNav";
import AnnouncementBanner from "./components/AnnouncementBanner";
import { useSiteContent } from "./lib/siteContent";
import "./App.css";

const Nav = () => <SiteNav />;

// ============= HERO =============
const Hero = () => {
  const { t } = useI18n();
  const siteContent = useSiteContent();
  const heroOv = siteContent?.hero || {};
  const { variant, trackClick } = useABTest("hero_cta1");
  const { variant: variant2, trackClick: trackClick2 } = useABTest("hero_cta2");
  const ctaText = t(`hero.cta1.variant_${variant}`) || t("hero.cta1");
  const cta2Text = t(`hero.cta2.variant_${variant2}`) || t("hero.cta2");
  return (
  <section id="top" className="relative min-h-screen flex items-center pt-32 pb-20 px-6 overflow-hidden">
    <div className="absolute inset-0 dotted-bg opacity-30" />
    <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-[#d4ff3a] blur-[150px] opacity-10" />
    
    <div className="max-w-7xl mx-auto w-full relative">
      <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="inline-flex items-center gap-2 px-4 py-2 glass rounded-full" data-testid="hero-badge">
            <div className="w-2 h-2 rounded-full bg-[#d4ff3a] pulse-dot" />
            <span className="text-xs tracking-wide text-stone-300">{t("hero.badge")}</span>
          </div>
        </div>
        <TrustStrip className="mb-8" />
        
        <h1 className="font-serif text-6xl md:text-8xl lg:text-9xl leading-[0.95] tracking-tight mb-8 max-w-5xl" data-testid="hero-title">
          {heroOv.title1 || t("hero.title1")}<br/>
          <span className="italic gradient-text">{heroOv.title2 || t("hero.title2")}</span> {heroOv.title3 || t("hero.title3")}
        </h1>
        
        <p className="text-lg md:text-xl text-stone-400 max-w-2xl mb-10 leading-relaxed">
          {heroOv.subtitle || t("hero.subtitle")}
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4">
          <Link to="/register" onClick={trackClick} className="btn-accent px-8 py-4 rounded-full font-medium inline-flex items-center justify-center gap-2 group" data-testid="hero-start-btn" data-ab-variant={variant}>
            {ctaText}
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
          <a href="#journey" onClick={trackClick2} className="glass px-8 py-4 rounded-full font-medium inline-flex items-center justify-center gap-2 hover:bg-white/10 transition-colors" data-testid="hero-journey-btn" data-ab-variant={variant2}>
            <Play className="w-4 h-4" />
            {cta2Text}
          </a>
        </div>
      </motion.div>

      {/* Stats strip */}
      <motion.div 
        initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.3 }}
        className="mt-24 grid grid-cols-2 md:grid-cols-4 gap-8 pt-12 border-t border-white/5"
      >
        {[
          { v: "Plăți protejate", l: t("hero.stat1") },
          { v: "Specialiști verificați", l: t("hero.stat2") },
          { v: "Garanție inclusă", l: t("hero.stat3") },
          { v: "Istoric permanent", l: t("hero.stat4") },
        ].map((s, i) => (
          <div key={i} data-testid={`hero-stat-${i}`}>
            <div className="font-serif text-2xl md:text-3xl font-medium">{s.v}</div>
            <div className="text-xs text-stone-500 mt-2 leading-relaxed">{s.l}</div>
          </div>
        ))}
      </motion.div>
    </div>
  </section>
  );
};

// ============= SECTION HEADER =============
const SectionTag = ({ num, label }) => (
  <div className="inline-flex items-center gap-3 mb-6">
    <span className="font-mono text-xs text-[#d4ff3a]">{num}</span>
    <div className="w-12 h-px bg-[#d4ff3a]" />
    <span className="text-xs uppercase tracking-[0.2em] text-stone-400">{label}</span>
  </div>
);

// ============= PROBLEM =============
const Problem = () => {
  const { t } = useI18n();
  const problems = [
    { icon: Eye, title: t("problem.p1.t"), desc: t("problem.p1.d") },
    { icon: Activity, title: t("problem.p2.t"), desc: t("problem.p2.d") },
    { icon: Shield, title: t("problem.p3.t"), desc: t("problem.p3.d") },
    { icon: TrendingUp, title: t("problem.p4.t"), desc: t("problem.p4.d") },
  ];

  return (
    <section id="problem" className="py-32 px-6 relative">
      <div className="max-w-7xl mx-auto">
        <SectionTag num="01" label={t("sec.problem")} />
        <h2 className="font-serif text-5xl md:text-7xl tracking-tight mb-6 max-w-4xl" data-testid="problem-title">
          {t("problem.title1")} <span className="italic">{t("problem.title2")}</span>
        </h2>
        <p className="text-lg text-stone-400 max-w-2xl mb-16">
          {t("problem.intro")}
        </p>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {problems.map((p, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="glass p-8 rounded-3xl hover:bg-white/[0.06] transition-colors"
              data-testid={`problem-card-${i}`}
            >
              <div className="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-6">
                <p.icon className="w-5 h-5 text-red-400" />
              </div>
              <h3 className="font-serif text-2xl mb-3">{p.title}</h3>
              <p className="text-sm text-stone-400 leading-relaxed">{p.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ============= SOLUTION =============
const Solution = () => {
  const { t } = useI18n();
  const pillars = [
    { icon: Box, title: t("sol.p1.t"), desc: t("sol.p1.d") },
    { icon: Users, title: t("sol.p2.t"), desc: t("sol.p2.d") },
    { icon: Lock, title: t("sol.p3.t"), desc: t("sol.p3.d") },
    { icon: FileCheck, title: t("sol.p4.t"), desc: t("sol.p4.d") },
  ];

  return (
    <section id="solution" className="py-32 px-6 relative">
      <div className="absolute inset-0 dotted-bg opacity-20" />
      <div className="max-w-7xl mx-auto relative">
        <SectionTag num="02" label={t("sec.solution")} />
        <div className="grid lg:grid-cols-2 gap-16 items-start mb-20">
          <div>
            <h2 className="font-serif text-5xl md:text-7xl tracking-tight" data-testid="solution-title">
              {t("sol.title1")} <span className="italic">{t("sol.title2")}</span>
            </h2>
          </div>
          <div className="lg:pt-12">
            <p className="text-lg text-stone-400 leading-relaxed">
              {t("sol.intro")}
            </p>
            <div className="mt-8 flex items-center gap-3 text-sm text-stone-300">
              <CheckCircle2 className="w-5 h-5 text-[#d4ff3a]" />
              <span className="text-white font-medium">{t("sol.tagline")}</span>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {pillars.map((p, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="glass-strong p-8 rounded-3xl group hover:border-[#d4ff3a]/30 transition-all"
              data-testid={`solution-pillar-${i}`}
            >
              <div className="w-14 h-14 rounded-2xl bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 flex items-center justify-center mb-6 group-hover:bg-[#d4ff3a]/20 transition-colors">
                <p.icon className="w-6 h-6 text-[#d4ff3a]" strokeWidth={1.5} />
              </div>
              <h3 className="font-serif text-2xl mb-3">{p.title}</h3>
              <p className="text-sm text-stone-400 leading-relaxed">{p.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ============= HOUSE HEALTH A→G (Harta casei) =============
const HouseHealthAxisLanding = () => {
  return (
    <section id="house-health-axis" className="py-32 px-6 relative">
      <div className="absolute inset-0 dotted-bg opacity-10" />
      <div className="max-w-7xl mx-auto relative">
        <SectionTag num="A→G" label="Harta casei" />
        <div className="grid lg:grid-cols-2 gap-16 items-start mb-16">
          <div>
            <h2 className="font-serif text-5xl md:text-7xl tracking-tight" data-testid="hh-axis-landing-title">
              Sănătatea casei tale, <span className="italic">de la A la G.</span>
            </h2>
          </div>
          <div className="lg:pt-10">
            <p className="text-lg text-stone-400 leading-relaxed">
              PropManage organizează sănătatea și starea locuinței tale în 7 capitole, de la A la G.
              Adaugi casa, îi înțelegi starea, vezi ce lipsește, o documentezi, o îmbunătățești prin
              specialiști verificați și vezi progresul — pas cu pas, în aceeași poveste.
            </p>
          </div>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {HOUSE_HEALTH_AXIS.map((c, i) => (
            <motion.div
              key={c.code}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: (i % 3) * 0.08 }}
              className="glass-strong p-7 rounded-3xl group hover:border-[#d4ff3a]/30 transition-all"
              data-testid={`hh-axis-landing-${c.code}`}
            >
              <div className="flex items-center gap-3 mb-5">
                <span className="w-12 h-12 rounded-2xl bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 flex items-center justify-center text-[#d4ff3a] font-serif text-2xl group-hover:bg-[#d4ff3a]/20 transition-colors">
                  {c.code}
                </span>
                <span className="text-xs uppercase tracking-[0.18em] text-stone-500">{c.homepageVerb}</span>
              </div>
              <h3 className="font-serif text-2xl mb-2">{c.title}</h3>
              <p className="text-sm text-stone-400 leading-relaxed">{c.why}</p>
            </motion.div>
          ))}
        </div>

        <div className="mt-10 flex flex-col sm:flex-row items-start sm:items-center gap-6">
          <a href="/register" data-testid="hh-axis-landing-cta"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-full bg-[#d4ff3a] text-black font-medium hover:scale-[1.02] transition-transform">
            Începe cu casa ta <ChevronRight className="w-4 h-4" />
          </a>
          <p className="text-xs text-stone-500 leading-relaxed max-w-2xl" data-testid="hh-axis-landing-disclaimer">
            {AXIS_DISCLAIMER}
          </p>
        </div>
      </div>
    </section>
  );
};

// ============= USER JOURNEY (Interactive) =============
const UserJourney = () => {
  const steps = [
    { id: "A", title: "Creează cont", desc: "Înregistrare rapidă cu email, Google sau Apple. Verificare telefon în 30 secunde.", visual: "auth" },
    { id: "B", title: "Adaugă proprietatea", desc: "Introdu detaliile imobilului. Sistemul inițiază procesul de digitalizare.", visual: "property" },
    { id: "C", title: "Vezi Digital Twin", desc: "Explorează modelul 3D al proprietății cu toate sistemele mapate (HVAC, Electric, Sanitar).", visual: "twin" },
    { id: "D", title: "Detectează problema", desc: "Senzori IoT sau utilizatorul identifică o anomalie. Sistemul propune intervenție.", visual: "alert" },
    { id: "E", title: "System match", desc: "Algoritmul găsește specialiștii potriviți: distanță, rating, preț, disponibilitate.", visual: "match" },
    { id: "F", title: "Alege specialist", desc: "Compară oferte, vezi recenzii, verifică certificările. Confirmă selecția.", visual: "select" },
    { id: "G", title: "Execuție lucrare", desc: "Chat în timp real, apel video de verificare, tracking GPS specialist.", visual: "work" },
    { id: "H", title: "Plată în Escrow", desc: "Suma e securizată în portofelul PropManage. Specialistul vede că banii sunt acolo.", visual: "escrow" },
    { id: "I", title: "Confirmă finalizarea", desc: "Verifici lucrarea, eliberezi plata, primești +100 tokens recompensă.", visual: "confirm" },
    { id: "J", title: "Update Digital Twin", desc: "Istoricul proprietății se actualizează automat. Scorul de sănătate crește.", visual: "update" },
  ];

  const [active, setActive] = useState(0);
  const [autoplay, setAutoplay] = useState(true);
  
  useEffect(() => {
    if (!autoplay) return;
    const timer = setInterval(() => {
      setActive(prev => (prev + 1) % steps.length);
    }, 3500);
    return () => clearInterval(timer);
  }, [autoplay, steps.length]);

  return (
    <section id="journey" className="py-32 px-6 relative">
      <div className="max-w-7xl mx-auto">
        <SectionTag num="03" label="Experiență Utilizator" />
        <div className="flex items-start justify-between mb-6 flex-wrap gap-4">
          <h2 className="font-serif text-5xl md:text-7xl tracking-tight max-w-3xl" data-testid="journey-title">
            Călătoria de la <span className="italic">A la J</span>.
          </h2>
          <button onClick={() => setAutoplay(!autoplay)} className="glass px-4 py-2.5 rounded-full flex items-center gap-2 text-sm hover:bg-white/10 transition-colors" data-testid="journey-autoplay">
            {autoplay ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            {autoplay ? "Pauză auto-play" : "Pornește auto-play"}
          </button>
        </div>
        <p className="text-lg text-stone-400 max-w-2xl mb-16">
          Click pe oricare pas sau lasă să ruleze automat. Un flux complet, transparent, fără surprize.
        </p>

        <div className="grid lg:grid-cols-[1fr_1.2fr] gap-12">
          {/* Steps list */}
          <div className="space-y-2">
            {steps.map((s, i) => (
              <button
                key={s.id}
                onClick={() => { setActive(i); setAutoplay(false); }}
                className={`w-full text-left p-5 rounded-2xl transition-all border ${
                  active === i 
                    ? "bg-[#d4ff3a]/10 border-[#d4ff3a]/30" 
                    : "glass border-white/5 hover:bg-white/[0.04]"
                }`}
                data-testid={`journey-step-${s.id}`}
              >
                <div className="flex items-center gap-4">
                  <div className={`relative w-10 h-10 rounded-full flex items-center justify-center font-serif text-lg shrink-0 ${
                    active === i ? "bg-[#d4ff3a] text-black" : "bg-white/10 text-stone-400"
                  }`}>
                    {s.id}
                    {active === i && autoplay && (
                      <svg className="absolute inset-0 -m-0.5" viewBox="0 0 44 44">
                        <circle cx="22" cy="22" r="20" fill="none" stroke="#d4ff3a" strokeWidth="1.5" strokeDasharray="125.6" strokeDashoffset="125.6" opacity="0.6">
                          <animate attributeName="stroke-dashoffset" from="125.6" to="0" dur="3.5s" repeatCount="1" />
                        </circle>
                      </svg>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium">{s.title}</div>
                    {active === i && (
                      <motion.p 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        className="text-sm text-stone-400 mt-2"
                      >
                        {s.desc}
                      </motion.p>
                    )}
                  </div>
                  <ChevronRight className={`w-4 h-4 shrink-0 transition-transform ${active === i ? "rotate-90 text-[#d4ff3a]" : "text-stone-500"}`} />
                </div>
              </button>
            ))}
          </div>

          {/* Visual preview */}
          <div className="lg:sticky lg:top-32 h-fit">
            <PhoneMockup step={steps[active]} />
          </div>
        </div>
      </div>
    </section>
  );
};

// ============= PHONE MOCKUP =============
const PhoneMockup = ({ step }) => {
  const renderContent = () => {
    switch (step.visual) {
      case "auth":
        return (
          <div className="space-y-3">
            <div className="text-center mb-6">
              <h4 className="font-serif text-xl mb-1">Bine ai venit</h4>
              <p className="text-xs text-stone-400">Introduceți datele pentru a accesa contul</p>
            </div>
            <button className="w-full bg-white text-black py-3 rounded-xl text-sm font-medium">Continuă cu Google</button>
            <button className="w-full bg-black border border-white/20 py-3 rounded-xl text-sm font-medium">Continuă cu Apple</button>
            <div className="text-center text-xs text-stone-500 py-2">SAU EMAIL</div>
            <div className="bg-white/5 rounded-xl px-4 py-3 text-xs text-stone-400">name@example.com</div>
            <div className="bg-white/5 rounded-xl px-4 py-3 text-xs text-stone-400">••••••••</div>
            <button className="w-full bg-[#d4ff3a] text-black py-3 rounded-xl text-sm font-medium">Conectează-te</button>
          </div>
        );
      case "property":
        return (
          <div className="space-y-4">
            <div className="aspect-video rounded-xl bg-gradient-to-br from-emerald-500/20 to-blue-500/20 border border-white/10 flex items-center justify-center">
              <Building2 className="w-12 h-12 text-white/40" strokeWidth={1} />
            </div>
            <h4 className="font-serif text-xl">Skyline Loft A4</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-stone-400">Tip</span><span>Apartament 3 cam.</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Suprafață</span><span>92 m²</span></div>
              <div className="flex justify-between"><span className="text-stone-400">Etaj</span><span>4 / 8</span></div>
            </div>
            <button className="w-full bg-[#d4ff3a] text-black py-3 rounded-xl text-sm font-medium mt-4">Inițiază Digitalizare</button>
          </div>
        );
      case "twin":
        return (
          <div className="space-y-3">
            <div className="aspect-square rounded-xl bg-gradient-to-br from-cyan-500/30 via-emerald-500/20 to-purple-500/20 border border-white/10 relative overflow-hidden flex items-center justify-center">
              <div className="absolute top-3 left-3 inline-flex items-center gap-1.5 bg-black/40 backdrop-blur px-2 py-1 rounded-full text-[10px]">
                <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" /> LIVE 3D
              </div>
              <Box className="w-20 h-20 text-white/30" strokeWidth={0.8} />
            </div>
            <div className="text-xs text-stone-400">Subsisteme · 4 active</div>
            {[
              { i: Zap, n: "Sistem Electric", s: "Optim", c: "emerald" },
              { i: Droplet, n: "Sistem Hidraulic", s: "Atenție", c: "red" },
              { i: Wind, n: "HVAC", s: "92% eficient", c: "emerald" },
            ].map((it, idx) => (
              <div key={idx} className="flex items-center gap-3 bg-white/5 rounded-xl p-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center bg-${it.c}-500/15`}>
                  <it.i className={`w-4 h-4 text-${it.c}-400`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium">{it.n}</div>
                  <div className={`text-[10px] text-${it.c}-400`}>{it.s}</div>
                </div>
                <CheckCircle2 className={`w-4 h-4 text-${it.c}-400`} />
              </div>
            ))}
          </div>
        );
      case "alert":
        return (
          <div className="space-y-3">
            <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-5">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium text-red-400">Anomalie detectată</div>
                  <p className="text-xs text-stone-300 mt-1">Sistem hidraulic — debit neregulat în Sector B. Inspecție urgentă necesară.</p>
                </div>
              </div>
            </div>
            <div className="bg-white/5 rounded-xl p-4 space-y-2">
              <div className="text-xs text-stone-400 uppercase tracking-wider">Recomandare AI</div>
              <p className="text-sm">Specialist Instalator Sanitar · ETA &lt; 2h · Cost estimat: 180-250 RON</p>
            </div>
            <button className="w-full bg-[#d4ff3a] text-black py-3 rounded-xl text-sm font-medium">Solicită Mentenanță</button>
          </div>
        );
      case "match":
      case "select":
        return (
          <div className="space-y-3">
            <div className="text-xs text-stone-400">3 specialiști disponibili</div>
            {[
              { n: "Andrei Popescu", r: "4.9", p: "180-250", d: "1.2 km", v: true, a: "Disponibil acum" },
              { n: "Mihai Ionescu", r: "4.7", p: "150-220", d: "3.5 km", v: true, a: "În 2h" },
              { n: "Cristian Vasile", r: "4.5", p: "200-280", d: "0.8 km", v: false, a: "Mâine" },
            ].map((s, i) => (
              <div key={i} className={`bg-white/5 rounded-xl p-3 ${i === 0 && step.visual === "select" ? "ring-2 ring-[#d4ff3a]" : ""}`}>
                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-stone-600 to-stone-800 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-medium truncate">{s.n}</span>
                      {s.v && <CheckCircle2 className="w-3 h-3 text-[#d4ff3a]" />}
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-stone-400 mt-0.5">
                      <span className="flex items-center gap-0.5"><Star className="w-2.5 h-2.5 fill-yellow-400 text-yellow-400" />{s.r}</span>
                      <span>·</span><span>{s.p} RON</span><span>·</span><span>{s.d}</span>
                    </div>
                    <div className={`text-[10px] mt-1 ${s.a.includes("acum") ? "text-emerald-400" : "text-stone-500"}`}>{s.a}</div>
                  </div>
                </div>
              </div>
            ))}
            {step.visual === "select" && <button className="w-full bg-[#d4ff3a] text-black py-3 rounded-xl text-sm font-medium">Confirmă Specialist</button>}
          </div>
        );
      case "work":
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-3 bg-white/5 rounded-xl p-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-stone-600 to-stone-800" />
              <div className="flex-1">
                <div className="text-sm font-medium flex items-center gap-1">
                  Andrei Popescu <CheckCircle2 className="w-3 h-3 text-[#d4ff3a]" />
                </div>
                <div className="text-[10px] text-stone-400">Expert HVAC · 4.9/5</div>
              </div>
              <button className="bg-white/10 p-2 rounded-lg"><MessageSquare className="w-3.5 h-3.5" /></button>
            </div>
            <div className="space-y-2">
              {[
                { s: "Pe drum", t: "10:15", a: true },
                { s: "În lucru", t: "10:45", a: true, current: true },
                { s: "Verificare", t: "—", a: false },
                { s: "Finalizat", t: "—", a: false },
              ].map((t, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${t.current ? "bg-[#d4ff3a] pulse-dot" : t.a ? "bg-emerald-400" : "bg-stone-700"}`} />
                  <div className="text-xs flex-1">{t.s}</div>
                  <div className="text-[10px] text-stone-500">{t.t}</div>
                </div>
              ))}
            </div>
            <div className="bg-white/5 rounded-xl p-3">
              <div className="text-[10px] text-stone-400 uppercase mb-2">Ultim mesaj</div>
              <p className="text-xs">"Am identificat scurgerea la valva de expansiune. Înlocuiesc piesa acum."</p>
            </div>
          </div>
        );
      case "escrow":
        return (
          <div className="space-y-4">
            <div className="bg-gradient-to-br from-[#d4ff3a]/20 to-emerald-500/10 border border-[#d4ff3a]/30 rounded-2xl p-6 text-center">
              <Lock className="w-8 h-8 text-[#d4ff3a] mx-auto mb-3" />
              <div className="text-xs text-stone-400 uppercase tracking-wider mb-1">Suma în Escrow</div>
              <div className="font-serif text-4xl">1,200 <span className="text-lg">RON</span></div>
              <div className="inline-flex items-center gap-1.5 mt-3 bg-emerald-500/10 px-3 py-1 rounded-full">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span className="text-[10px] text-emerald-400 uppercase tracking-wider">Securizat</span>
              </div>
            </div>
            <div className="text-xs text-stone-400 text-center">Banii sunt eliberați doar după confirmarea ta.</div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between bg-white/5 rounded-lg p-2"><span>Comision PropManage</span><span>3%</span></div>
              <div className="flex justify-between bg-white/5 rounded-lg p-2"><span>Protecție Escrow</span><span className="text-emerald-400">Inclusă</span></div>
            </div>
          </div>
        );
      case "confirm":
        return (
          <div className="space-y-4 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
            </div>
            <h4 className="font-serif text-2xl">Lucrare Confirmată!</h4>
            <p className="text-xs text-stone-400">Toate detaliile au fost salvate în jurnalul digital al proprietății.</p>
            <div className="bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 rounded-2xl p-4 flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-[#d4ff3a]" />
              <div className="text-left flex-1">
                <div className="text-[10px] text-stone-400 uppercase">Bonus Recompensă</div>
                <div className="text-sm font-medium">Ai primit +100 Tokeni</div>
              </div>
            </div>
            <button className="w-full bg-white text-black py-3 rounded-xl text-sm font-medium">Eliberează Plata</button>
          </div>
        );
      case "update":
        return (
          <div className="space-y-4">
            <div className="text-xs text-stone-400 uppercase tracking-wider">Digital Twin actualizat</div>
            <div className="bg-white/5 rounded-2xl p-5">
              <div className="text-xs text-stone-400 mb-1">Scor Sănătate</div>
              <div className="flex items-baseline gap-2">
                <div className="font-serif text-5xl">98</div>
                <div className="text-sm text-stone-500">/100</div>
                <div className="ml-auto text-xs text-emerald-400 flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" /> +12
                </div>
              </div>
              <div className="h-2 bg-white/5 rounded-full mt-3 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#d4ff3a] to-emerald-400 rounded-full" style={{ width: "98%" }} />
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-xs text-stone-400 uppercase tracking-wider">Istoric mentenanță</div>
              {[
                { d: "Azi", t: "Reparație HVAC", w: "Andrei Popescu", s: "FINALIZAT" },
                { d: "12 Oct", t: "Înlocuire filtre", w: "Mihai Ionescu", s: "FINALIZAT" },
              ].map((h, i) => (
                <div key={i} className="bg-white/5 rounded-xl p-3">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium">{h.t}</span>
                    <span className="text-[10px] text-emerald-400">{h.s}</span>
                  </div>
                  <div className="text-[10px] text-stone-500 mt-0.5">{h.d} · {h.w}</div>
                </div>
              ))}
            </div>
          </div>
        );
      default: return null;
    }
  };

  return (
    <div className="relative">
      <div className="absolute inset-0 phone-glow" />
      <div className="relative mx-auto max-w-[340px] bg-black border border-white/10 rounded-[3rem] p-3 shadow-2xl">
        <div className="bg-[#0a0a0b] rounded-[2.5rem] overflow-hidden">
          <div className="h-6 bg-black flex items-center justify-center">
            <div className="w-20 h-4 bg-black rounded-full" />
          </div>
          <div className="p-5 min-h-[520px]">
            <AnimatePresence mode="wait">
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
              >
                {renderContent()}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============= SPECIALIST JOURNEY =============
const SpecialistJourney = () => {
  const tiers = [
    {
      name: "ENTRY",
      color: "stone",
      price: "Gratuit",
      desc: "Înregistrare nouă",
      features: ["Acces lead-uri standard", "Profil de bază", "Comision standard 15%", "0-9 recenzii"]
    },
    {
      name: "VERIFIED",
      color: "lime",
      price: "După 10+ joburi",
      desc: "Specialist Verificat",
      features: ["Lead-uri prioritare", "Insignă VERIFIED", "Comision redus -15%", "Rating min 4.8", "Profil extins"],
      highlight: true
    },
    {
      name: "PREMIUM",
      color: "amber",
      price: "Elite Network",
      desc: "PropManage Elite",
      features: ["Acces Wallet Users (50K+)", "Comisioane preferențiale", "Top 3 în căutări", "Account manager dedicat", "Acces beta features"]
    },
  ];

  return (
    <section className="py-32 px-6 relative">
      <div className="max-w-7xl mx-auto">
        <SectionTag num="04" label="Experiență Specialist" />
        <div className="grid lg:grid-cols-2 gap-12 items-end mb-16">
          <h2 className="font-serif text-5xl md:text-7xl tracking-tight" data-testid="specialist-title">
            De la <span className="italic">Entry</span> la <span className="italic">Premium</span>.
          </h2>
          <p className="text-lg text-stone-400 max-w-md">
            Specialiștii cresc în reputație, accesează lead-uri mai bune și câștigă mai mult — toate transparent, măsurabil, meritocratic.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-4">
          {tiers.map((t, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className={`relative p-8 rounded-3xl ${
                t.highlight
                  ? "bg-gradient-to-br from-[#d4ff3a]/20 to-emerald-500/5 border-2 border-[#d4ff3a]/40 glow-lime"
                  : "glass border border-white/10"
              }`}
              data-testid={`tier-${t.name}`}
            >
              {t.highlight && (
                <div className="absolute -top-3 left-8 bg-[#d4ff3a] text-black text-[10px] font-bold tracking-wider px-3 py-1 rounded-full">
                  RECOMANDAT
                </div>
              )}
              <div className="text-xs tracking-[0.2em] text-stone-400 mb-2">{t.name}</div>
              <div className="font-serif text-3xl mb-1">{t.desc}</div>
              <div className="text-sm text-stone-400 mb-6">{t.price}</div>
              <div className="space-y-3">
                {t.features.map((f, j) => (
                  <div key={j} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className={`w-4 h-4 mt-0.5 shrink-0 ${t.highlight ? "text-[#d4ff3a]" : "text-stone-500"}`} />
                    <span className={t.highlight ? "text-white" : "text-stone-300"}>{f}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Specialist flow */}
        <div className="mt-20 glass-strong rounded-3xl p-10">
          <h3 className="font-serif text-3xl mb-8">Flux specialist · 6 pași</h3>
          <div className="grid md:grid-cols-3 lg:grid-cols-6 gap-4">
            {[
              { i: Bell, t: "Primește lead" },
              { i: Coins, t: "Plătește 40-50 RON" },
              { i: FileCheck, t: "Trimite ofertă" },
              { i: Wrench, t: "Execută jobul" },
              { i: Star, t: "Primește rating" },
              { i: Award, t: "Devine Verified" },
            ].map((s, i) => (
              <div key={i} className="text-center" data-testid={`spec-step-${i}`}>
                <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-3">
                  <s.i className="w-5 h-5 text-[#d4ff3a]" strokeWidth={1.5} />
                </div>
                <div className="text-xs text-stone-400 mb-1">PAS {i + 1}</div>
                <div className="text-sm font-medium">{s.t}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

// ============= WALLET ECOSYSTEM =============
const WalletEcosystem = () => {
  const items = [
    {
      icon: Wallet, color: "emerald", label: "WALLET",
      title: "Bani reali",
      desc: "Plăți, escrow, retrageri automate. Securizat prin PropManage Pay.",
      stats: [{ k: "Sold curent", v: "2,450.80 RON" }, { k: "Săptămâna", v: "+12%" }]
    },
    {
      icon: Sparkles, color: "lime", label: "TOKENS",
      title: "Recompense",
      desc: "Câștigi tokens pentru joburi, recenzii și referrals. Folosește-le în ecosistem.",
      stats: [{ k: "+100", v: "per job" }, { k: "+500", v: "per referral" }, { k: "+20", v: "per review" }]
    },
    {
      icon: Coins, color: "amber", label: "CREDITS",
      title: "Pentru specialiști",
      desc: "Cumperi lead-uri și unlock-uri. Alimentezi din Wallet sau bancar direct.",
      stats: [{ k: "Per lead", v: "40-50 RON" }, { k: "Rambursare", v: "Da, în 7 zile" }]
    },
  ];

  return (
    <section className="py-32 px-6 relative">
      <div className="max-w-7xl mx-auto">
        <SectionTag num="05" label="Wallet & Ecosistem" />
        <h2 className="font-serif text-5xl md:text-7xl tracking-tight mb-6 max-w-4xl" data-testid="wallet-title">
          Trei monede. <span className="italic">Un singur ecosistem.</span>
        </h2>
        <p className="text-lg text-stone-400 max-w-2xl mb-16">
          Wallet pentru valoare reală. Tokens pentru engagement. Credits pentru specialiști. Totul interconectat, totul transparent.
        </p>

        <div className="grid md:grid-cols-3 gap-4">
          {items.map((it, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="glass-strong rounded-3xl p-8 relative overflow-hidden"
              data-testid={`wallet-${it.label}`}
            >
              <div className={`absolute -top-20 -right-20 w-40 h-40 rounded-full bg-${it.color}-500 opacity-10 blur-3xl`} />
              <div className="relative">
                <div className={`w-14 h-14 rounded-2xl bg-${it.color}-500/15 border border-${it.color}-500/30 flex items-center justify-center mb-6`}>
                  <it.icon className={`w-6 h-6 text-${it.color}-400`} strokeWidth={1.5} />
                </div>
                <div className="text-xs tracking-[0.2em] text-stone-400 mb-2">{it.label}</div>
                <h3 className="font-serif text-3xl mb-3">{it.title}</h3>
                <p className="text-sm text-stone-400 leading-relaxed mb-6">{it.desc}</p>
                <div className="space-y-2 pt-6 border-t border-white/5">
                  {it.stats.map((s, j) => (
                    <div key={j} className="flex justify-between text-sm">
                      <span className="text-stone-400">{s.k}</span>
                      <span className="font-medium">{s.v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Escrow flow */}
        <div className="mt-16 glass-strong rounded-3xl p-10">
          <div className="flex items-center gap-3 mb-8">
            <Lock className="w-5 h-5 text-[#d4ff3a]" />
            <h3 className="font-serif text-3xl">Logică Escrow</h3>
          </div>
          <div className="grid md:grid-cols-5 gap-4 items-center">
            {[
              { t: "Client plătește", d: "Suma intră în escrow", c: "white" },
              { i: ArrowRight, sep: true },
              { t: "Specialist lucrează", d: "Vede că banii sunt securizați", c: "lime" },
              { i: ArrowRight, sep: true },
              { t: "Client confirmă", d: "Plata eliberată instant", c: "emerald" },
            ].map((s, i) => s.sep ? (
              <s.i key={i} className="w-5 h-5 text-stone-600 mx-auto hidden md:block" />
            ) : (
              <div key={i} className="text-center md:text-left">
                <div className={`font-serif text-xl mb-1 ${s.c === "lime" ? "text-[#d4ff3a]" : s.c === "emerald" ? "text-emerald-400" : ""}`}>{s.t}</div>
                <div className="text-xs text-stone-400">{s.d}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

// ============= DIGITAL TWIN =============
const DigitalTwin = () => {
  const [hovered, setHovered] = useState(null);
  const systems = [
    { id: "hvac", name: "HVAC", health: 98, status: "Excelent", icon: Wind, color: "emerald" },
    { id: "elec", name: "Sistem Electric", health: 94, status: "Optim", icon: Zap, color: "emerald" },
    { id: "plumb", name: "Instalații Sanitare", health: 62, status: "Atenție", icon: Droplet, color: "red" },
    { id: "struct", name: "Structură", health: 90, status: "Excelent", icon: Layers, color: "emerald" },
  ];

  return (
    <section id="twin" className="py-32 px-6 relative">
      <div className="absolute inset-0 dotted-bg opacity-20" />
      <div className="max-w-7xl mx-auto relative">
        <SectionTag num="06" label="Digital Twin · Element diferențiator" />
        <h2 className="font-serif text-5xl md:text-7xl tracking-tight mb-6 max-w-4xl" data-testid="twin-title">
          Casa ta, în <span className="italic">3D real-time</span>.
        </h2>
        <p className="text-lg text-stone-400 max-w-2xl mb-16">
          LiDAR + termografie + senzori IoT. Fiecare echipament mapat, fiecare intervenție documentată, fiecare anomalie detectată automat.
        </p>

        <div className="grid lg:grid-cols-[1.3fr_1fr] gap-8">
          {/* 3D Building Visualization */}
          <div className="glass-strong rounded-3xl p-8 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 via-transparent to-purple-500/10" />
            <div className="relative">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <div className="text-xs text-stone-400 uppercase tracking-wider mb-1">Previzualizare Live</div>
                  <h3 className="font-serif text-2xl">Vila Horizon · TW-09 Alpha</h3>
                </div>
                <div className="inline-flex items-center gap-2 bg-emerald-500/10 px-3 py-1.5 rounded-full">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs text-emerald-400">LIVE 3D</span>
                </div>
              </div>

              {/* Building */}
              <div className="aspect-[4/3] rounded-2xl bg-gradient-to-br from-slate-900 via-cyan-950 to-slate-900 border border-white/10 relative overflow-hidden flex items-center justify-center">
                <svg viewBox="0 0 400 300" className="w-full h-full p-8">
                  {/* Building outline */}
                  <g fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="1">
                    <path d="M80 250 L80 100 L200 50 L320 100 L320 250 Z" />
                    <path d="M80 100 L200 150 L320 100" />
                    <path d="M200 50 L200 150 L200 250" />
                  </g>
                  {/* Floors */}
                  {[140, 180, 220].map((y, i) => (
                    <line key={i} x1="80" y1={y} x2="320" y2={y} stroke="rgba(255,255,255,0.1)" strokeDasharray="2 4" />
                  ))}
                  {/* System dots */}
                  {systems.map((s, i) => {
                    const positions = [[140, 130], [260, 170], [140, 210], [260, 230]];
                    return (
                      <g key={s.id} onMouseEnter={() => setHovered(s.id)} onMouseLeave={() => setHovered(null)} style={{ cursor: "pointer" }}>
                        <circle 
                          cx={positions[i][0]} 
                          cy={positions[i][1]} 
                          r={hovered === s.id ? "12" : "6"} 
                          fill={s.color === "red" ? "#f87171" : "#d4ff3a"} 
                          className="transition-all"
                        />
                        <circle 
                          cx={positions[i][0]} 
                          cy={positions[i][1]} 
                          r="14" 
                          fill={s.color === "red" ? "#f87171" : "#d4ff3a"} 
                          opacity="0.2"
                        >
                          <animate attributeName="r" values="14;22;14" dur="2s" repeatCount="indefinite" />
                          <animate attributeName="opacity" values="0.2;0;0.2" dur="2s" repeatCount="indefinite" />
                        </circle>
                      </g>
                    );
                  })}
                </svg>
                <div className="absolute bottom-4 left-4 right-4 flex gap-3 text-xs">
                  <div className="bg-black/40 backdrop-blur px-3 py-2 rounded-lg">
                    <div className="text-stone-400 text-[10px]">Temp</div>
                    <div className="text-white">22.4°C</div>
                  </div>
                  <div className="bg-black/40 backdrop-blur px-3 py-2 rounded-lg">
                    <div className="text-stone-400 text-[10px]">Umiditate</div>
                    <div className="text-white">48%</div>
                  </div>
                  <div className="bg-black/40 backdrop-blur px-3 py-2 rounded-lg">
                    <div className="text-stone-400 text-[10px]">Senzori</div>
                    <div className="text-emerald-400">98.2%</div>
                  </div>
                </div>
              </div>

              {/* Health score */}
              <div className="mt-6 flex items-center gap-6">
                <div>
                  <div className="text-xs text-stone-400 uppercase tracking-wider mb-1">Scor Sănătate</div>
                  <div className="font-serif text-5xl">94<span className="text-2xl text-stone-500">/100</span></div>
                </div>
                <div className="flex-1">
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <motion.div initial={{ width: 0 }} whileInView={{ width: "94%" }} transition={{ duration: 1.5, ease: "easeOut" }} className="h-full bg-gradient-to-r from-[#d4ff3a] to-emerald-400" />
                  </div>
                  <div className="flex justify-between text-[10px] text-stone-500 mt-2">
                    <span>0</span><span>50</span><span>100</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Systems list */}
          <div className="space-y-3">
            {systems.map((s, i) => (
              <motion.div
                key={s.id}
                onMouseEnter={() => setHovered(s.id)}
                onMouseLeave={() => setHovered(null)}
                initial={{ opacity: 0, x: 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className={`glass rounded-2xl p-5 cursor-pointer transition-all ${hovered === s.id ? "bg-white/[0.08] border-[#d4ff3a]/30" : ""}`}
                data-testid={`twin-system-${s.id}`}
              >
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-${s.color}-500/15 border border-${s.color}-500/30`}>
                    <s.icon className={`w-5 h-5 text-${s.color}-400`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium">{s.name}</div>
                    <div className={`text-xs text-${s.color}-400 mt-0.5`}>{s.status}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-serif text-2xl">{s.health}</div>
                    <div className="text-[10px] text-stone-500">/100</div>
                  </div>
                </div>
              </motion.div>
            ))}
            <div className="glass-strong rounded-2xl p-5 mt-6 border-[#d4ff3a]/30">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-[#d4ff3a]" />
                <div className="text-xs text-[#d4ff3a] uppercase tracking-wider">AI Insight</div>
              </div>
              <p className="text-sm text-stone-300">Sistemul hidraulic necesită inspecție în max 7 zile. Recomandare: Instalator verificat în zonă.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

// ============= ADMIN TRUST =============
const AdminTrust = () => {
  const items = [
    { icon: FileCheck, t: "Verificare specialiști", d: "Asigurări, certificări, documente legale — totul scanat și validat manual." },
    { icon: Gavel, t: "Mediere dispute", d: "Sistem de arbitraj imparțial. Refund, release sau request more info." },
    { icon: Award, t: "Quality control", d: "Audit lunar al lucrărilor, validare 3D model, rating real timp." },
    { icon: Shield, t: "Audit certificat extern", d: "Standard de audit verificat extern pentru fiecare proprietate premium." },
  ];

  return (
    <section className="py-32 px-6 relative">
      <div className="max-w-7xl mx-auto">
        <SectionTag num="07" label="Administrare & Încredere" />
        <div className="grid lg:grid-cols-2 gap-16 mb-16">
          <h2 className="font-serif text-5xl md:text-7xl tracking-tight" data-testid="admin-title">
            Trust este <span className="italic">infrastructură</span>.
          </h2>
          <p className="text-lg text-stone-400 lg:pt-8 max-w-md">
            Fiecare specialist verificat. Fiecare dispută rezolvată. Fiecare lucrare validată. PropAdmin este layer-ul invizibil care face platforma de încredere.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-4 mb-12">
          {items.map((it, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              className="glass p-8 rounded-3xl flex gap-5"
              data-testid={`admin-item-${i}`}
            >
              <div className="w-12 h-12 rounded-2xl bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 flex items-center justify-center shrink-0">
                <it.icon className="w-5 h-5 text-[#d4ff3a]" />
              </div>
              <div>
                <h3 className="font-serif text-2xl mb-2">{it.t}</h3>
                <p className="text-sm text-stone-400 leading-relaxed">{it.d}</p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Admin dashboard preview */}
        <div className="glass-strong rounded-3xl p-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <div className="text-xs text-stone-400 uppercase tracking-wider mb-1">PropAdmin · Control Center</div>
              <h3 className="font-serif text-2xl">Metrici Live</h3>
            </div>
            <div className="text-xs text-stone-400">real-time · last 24h</div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { v: "24", l: "Total cereri", c: "+12%" },
              { v: "08", l: "În așteptare", c: "PRIORITATE", warn: true },
              { v: "05", l: "Documente incomplete", c: "Acțiune necesară", err: true },
              { v: "11", l: "Verificați azi", c: "✓", ok: true },
            ].map((s, i) => (
              <div key={i} className="bg-white/[0.03] rounded-2xl p-5">
                <div className="font-serif text-4xl mb-1">{s.v}</div>
                <div className="text-xs text-stone-400 mb-2">{s.l}</div>
                <div className={`text-[10px] uppercase tracking-wider ${s.warn ? "text-amber-400" : s.err ? "text-red-400" : s.ok ? "text-emerald-400" : "text-stone-500"}`}>{s.c}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

// ============= BUSINESS MODEL =============
const BusinessModel = () => {
  const { showSection } = useI18n();
  return (
    <BusinessModelInner showUnitEconomics={showSection("landing_show_unit_economics", false)} />
  );
};

const BusinessModelInner = ({ showUnitEconomics }) => {
  const streams = [
    { icon: Coins, name: "Lead Fees", desc: "Specialiști plătesc 40-50 RON per lead acceptat.", n: "01" },
    { icon: TrendingUp, name: "Service Commissions", desc: "3% comision pe fiecare tranzacție escrow.", n: "02" },
    { icon: Sparkles, name: "Activare Wallet", desc: "750€ licență pe viață pentru utilizatorii premium.", n: "03" },
    { icon: Activity, name: "Abonament (în pregătire)", desc: "59€/lună pentru planuri complete de mentenanță.", n: "04" },
  ];

  return (
    <section id="business" className="py-32 px-6 relative">
      <div className="max-w-7xl mx-auto">
        <SectionTag num="08" label="Model de business" />
        <h2 className="font-serif text-5xl md:text-7xl tracking-tight mb-6 max-w-4xl" data-testid="business-title">
          Patru fluxuri de <span className="italic">venit</span>.
        </h2>
        <p className="text-lg text-stone-400 max-w-2xl mb-16">
          Marketplace economics + SaaS recurring + Premium licensing. Un model diversificat, scalabil, cu margini sănătoase.
        </p>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {streams.map((s, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="glass-strong rounded-3xl p-8 group hover:bg-white/[0.06] transition-colors"
              data-testid={`stream-${i}`}
            >
              <div className="flex items-center justify-between mb-8">
                <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center">
                  <s.icon className="w-5 h-5 text-[#d4ff3a]" />
                </div>
                <span className="font-mono text-xs text-stone-500">{s.n}</span>
              </div>
              <h3 className="font-serif text-2xl mb-2">{s.name}</h3>
              <p className="text-sm text-stone-400 leading-relaxed">{s.desc}</p>
            </motion.div>
          ))}
        </div>

        {/* Projection */}
        {showUnitEconomics && (
          <div className="mt-16 glass-strong rounded-3xl p-10">
            <h3 className="font-serif text-3xl mb-8">Indicatori economici</h3>
            <div className="grid md:grid-cols-3 gap-8">
              {[
                { l: "ARPU lunar (proprietar premium)", v: "~64€" },
                { l: "Take-rate marketplace", v: "8-12%" },
                { l: "LTV / CAC (target)", v: "4.2x" },
              ].map((s, i) => (
                <div key={i} className="border-l-2 border-[#d4ff3a]/30 pl-6">
                  <div className="text-xs uppercase tracking-wider text-stone-400 mb-2">{s.l}</div>
                  <div className="font-serif text-4xl">{s.v}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

// ============= VALUE PROPOSITION =============
const ValueProp = () => {
  const actors = [
    {
      role: "Client",
      icon: Home,
      color: "lime",
      benefits: [
        { t: "Transparență totală", d: "Vezi exact ce se întâmplă în casa ta — costuri, intervenții, istoric." },
        { t: "Control absolut", d: "Decizi când, cum, cu cine. Plăți securizate, recenzii reale." },
        { t: "Valoare crescută", d: "Casă digitalizată = casă mai valoroasă pe piață cu 8-15%." },
      ]
    },
    {
      role: "Specialist",
      icon: Wrench,
      color: "amber",
      benefits: [
        { t: "Lead-uri calificate", d: "Clienți cu intent real, briefing detaliat, budget definit." },
        { t: "Workflow structurat", d: "Plata garantată prin escrow. Fără negocieri, fără risc." },
        { t: "Sistem de reputație", d: "Rating real, badge VERIFIED, acces la elite network." },
      ]
    },
    {
      role: "Platformă",
      icon: Cpu,
      color: "cyan",
      benefits: [
        { t: "Ecosistem scalabil", d: "Network effects: mai mulți clienți → mai mulți specialiști." },
        { t: "Venituri recurente", d: "Abonamente + comisioane + licențe premium." },
        { t: "Avantaj de date", d: "Cel mai mare dataset de mentenanță rezidențială din regiune." },
      ]
    },
  ];

  return (
    <section className="py-32 px-6 relative">
      <div className="max-w-7xl mx-auto">
        <SectionTag num="09" label="Propunere de valoare" />
        <h2 className="font-serif text-5xl md:text-7xl tracking-tight mb-6 max-w-4xl" data-testid="value-title">
          Toată lumea <span className="italic">câștigă</span>.
        </h2>
        <p className="text-lg text-stone-400 max-w-2xl mb-16">
          Marketplace-urile reale funcționează când toți cei trei actori — client, furnizor, platformă — au incentive aliniate.
        </p>

        <div className="grid md:grid-cols-3 gap-4">
          {actors.map((a, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="glass-strong rounded-3xl p-8"
              data-testid={`value-actor-${i}`}
            >
              <div className="flex items-center gap-3 mb-8 pb-6 border-b border-white/5">
                <div className={`w-12 h-12 rounded-2xl bg-${a.color}-500/15 border border-${a.color}-500/30 flex items-center justify-center`}>
                  <a.icon className={`w-5 h-5 text-${a.color}-400`} />
                </div>
                <h3 className="font-serif text-2xl">{a.role}</h3>
              </div>
              <div className="space-y-6">
                {a.benefits.map((b, j) => (
                  <div key={j}>
                    <div className="flex items-start gap-2 mb-1">
                      <CheckCircle2 className={`w-4 h-4 text-${a.color}-400 mt-0.5 shrink-0`} />
                      <div className="font-medium">{b.t}</div>
                    </div>
                    <p className="text-sm text-stone-400 leading-relaxed pl-6">{b.d}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ============= GOLDEN PATH =============
const GoldenPath = () => {
  const path = [
    { i: Users, t: "Cont", c: "Andrei creează cont" },
    { i: AlertTriangle, t: "Solicitare", c: "Alertă: scurgere baie" },
    { i: Wrench, t: "Specialist", c: "Match cu Mihai 4.9★" },
    { i: Camera, t: "Lucrare", c: "Lucrare 1h 45min" },
    { i: Lock, t: "Plată", c: "Escrow 450 RON" },
    { i: FileCheck, t: "Istoric", c: "Actualizare jurnal digital" },
    { i: TrendingUp, t: "Twin actualizat", c: "+5% sănătate" },
  ];

  return (
    <section className="py-32 px-6 relative">
      <div className="absolute inset-0 dotted-bg opacity-30" />
      <div className="max-w-7xl mx-auto relative">
        <SectionTag num="10" label="Drumul ideal" />
        <h2 className="font-serif text-5xl md:text-7xl tracking-tight mb-6 max-w-4xl" data-testid="golden-title">
          De la <span className="italic">click</span> la <span className="italic">finalizare</span>.
        </h2>
        <p className="text-lg text-stone-400 max-w-2xl mb-16">
          Un singur flux. Șapte pași. Sub 24 de ore de la problemă la rezolvare documentată.
        </p>

        <div className="relative">
          {/* Connecting line */}
          <div className="absolute top-10 left-0 right-0 h-px hidden lg:block divider-line" />
          
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            {path.map((p, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className="relative text-center"
                data-testid={`golden-${i}`}
              >
                <div className="relative w-20 h-20 mx-auto mb-4">
                  <div className="absolute inset-0 rounded-full bg-[#d4ff3a]/20 blur-xl" />
                  <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
                    <p.i className="w-7 h-7 text-black" strokeWidth={2} />
                  </div>
                  <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-black border-2 border-[#d4ff3a] flex items-center justify-center text-[10px] font-mono">
                    {i + 1}
                  </div>
                </div>
                <div className="font-serif text-xl mb-1">{p.t}</div>
                <div className="text-xs text-stone-400">{p.c}</div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Time savings */}
        <div className="mt-20 grid md:grid-cols-3 gap-4">
          {[
            { v: "23h", l: "Average resolution time", before: "Înainte: 7-14 zile" },
            { v: "100%", l: "Documented interventions", before: "Înainte: 0%" },
            { v: "+15%", l: "Creștere valoare proprietate", before: "După 12 luni utilizare" },
          ].map((s, i) => (
            <div key={i} className="glass-strong rounded-3xl p-8">
              <div className="font-serif text-6xl mb-2 text-[#d4ff3a]">{s.v}</div>
              <div className="text-sm font-medium mb-2">{s.l}</div>
              <div className="text-xs text-stone-500">{s.before}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ============= CTA + FOOTER =============
const CTA = () => {
  const { t } = useI18n();
  const { variant: ctaVariant, trackClick: trackCtaClick } = useABTest("cta_btn1");
  const ctaBtn1Text = t(`cta.btn1.variant_${ctaVariant}`) || t("cta.btn1");
  return (
  <section id="cta" className="py-32 px-6 relative">
    <div className="max-w-7xl mx-auto">
      <div className="relative glass-strong rounded-[3rem] p-12 md:p-20 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-[#d4ff3a] blur-[120px] opacity-20" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full bg-emerald-500 blur-[120px] opacity-10" />
        
        <div className="relative max-w-3xl">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 rounded-full mb-8">
            <div className="w-2 h-2 rounded-full bg-[#d4ff3a] pulse-dot" />
            <span className="text-xs tracking-wide text-stone-300">{t("cta.badge")}</span>
          </div>
          <h2 className="font-serif text-5xl md:text-7xl tracking-tight mb-6" data-testid="cta-title">
            {t("cta.title1")} <span className="italic">{t("cta.title2")}</span>
          </h2>
          <p className="text-lg text-stone-400 mb-10 max-w-xl">
            {t("cta.intro")}
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Link to="/register" onClick={trackCtaClick} className="btn-accent px-8 py-4 rounded-full font-medium inline-flex items-center gap-2 group" data-testid="cta-primary" data-ab-variant={ctaVariant}>
              {ctaBtn1Text}
              <ArrowUpRight className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </Link>
            <Link to="/login" className="glass px-8 py-4 rounded-full font-medium inline-flex items-center gap-2 hover:bg-white/10 transition-colors" data-testid="cta-secondary">
              {t("cta.btn2")}
            </Link>
          </div>
          <div className="text-xs text-stone-500 mt-6">{t("cta.footer")}</div>
        </div>
      </div>
    </div>
  </section>
  );
};

const SocialIcon = ({ icon }) => {
  const common = "w-4 h-4";
  if (icon === "facebook") return (
    <svg className={common} viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
  );
  if (icon === "instagram") return (
    <svg className={common} viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
  );
  if (icon === "youtube") return (
    <svg className={common} viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
  );
  if (icon === "linkedin") return (
    <svg className={common} viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
  );
  return null;
};

const Footer = () => {
  const [settings, setSettings] = React.useState(null);
  React.useEffect(() => {
    let active = true;
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/app-settings/public`)
      .then(r => r.json())
      .then(d => { if (active) setSettings(d); })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  const social = settings?.social || {};
  const links = [
    { url: social.facebook_main, label: "Facebook · PropManage", icon: "facebook" },
    { url: social.facebook_estate, label: "Facebook · Imobile Verificate", icon: "facebook" },
    { url: social.instagram_main, label: "Instagram · PropManage", icon: "instagram" },
    { url: social.instagram_estate, label: "Instagram · Imobile Verificate", icon: "instagram" },
    { url: social.youtube, label: "YouTube", icon: "youtube" },
    { url: social.linkedin, label: "LinkedIn", icon: "linkedin" },
  ];

  const companyName = settings?.company?.name || "PropManage";
  const companyTagline = settings?.company?.tagline || "Property Operating System";
  const contactEmail = settings?.contact?.email || "contact@propmanage.ro";

  return (
    <footer className="border-t border-white/5 py-12 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between gap-6 mb-8">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg">{companyName}</span>
            <span className="text-xs text-stone-500 ml-2">© 2026 · {companyTagline}</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 text-xs text-stone-500">
            <Link to="/terms" className="hover:text-white transition-colors" data-testid="footer-terms">Termeni</Link>
            <Link to="/privacy" className="hover:text-white transition-colors" data-testid="footer-privacy">Confidențialitate</Link>
            <Link to="/cookies" className="hover:text-white transition-colors" data-testid="footer-cookies">Cookies</Link>
            <Link to="/trust" className="hover:text-white transition-colors" data-testid="footer-trust">Trust Center</Link>
            <Link to="/ghiduri" className="hover:text-white transition-colors" data-testid="footer-ghiduri">Ghiduri</Link>
            <Link to="/probleme-casa" className="hover:text-white transition-colors" data-testid="footer-probleme">Probleme casă</Link>
            <Link to="/devino-francizat" className="hover:text-[#d4ff3a] transition-colors" data-testid="footer-franchise">Devino francizat</Link>
            <Link to="/devino-specialist" className="hover:text-[#d4ff3a] transition-colors" data-testid="footer-specialist-apply">Devino specialist</Link>
            <Link to="/status" className="hover:text-white transition-colors inline-flex items-center gap-1" data-testid="footer-status">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Status
            </Link>
            <GDPRAuditBadge variant="footer" />
            <a href={`mailto:${contactEmail}`} className="hover:text-white transition-colors">Contact</a>
          </div>
        </div>
        <div className="border-t border-white/5 pt-6 pb-2" data-testid="footer-explore">
          <div className="text-[11px] text-stone-500 uppercase tracking-wider mb-3">Explorează</div>
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-stone-400">
            <Link to="/design-interior" className="hover:text-[#d4ff3a] transition-colors" data-testid="footer-explore-design">Design interior</Link>
            <Link to="/imobile-verificate" className="hover:text-[#d4ff3a] transition-colors" data-testid="footer-explore-estate">Imobile Verificate</Link>
            <Link to="/digital-twin" className="hover:text-[#d4ff3a] transition-colors" data-testid="footer-explore-twin">Digital Twin</Link>
            <Link to="/marketplace" className="hover:text-[#d4ff3a] transition-colors" data-testid="footer-explore-marketplace">Marketplace specialiști</Link>
            <Link to="/scorul-casei" className="hover:text-[#d4ff3a] transition-colors" data-testid="footer-explore-audit">Scorul Casei</Link>
            <Link to="/preturi" className="hover:text-[#d4ff3a] transition-colors" data-testid="footer-explore-preturi">Prețuri lucrări</Link>
          </div>
        </div>
        <div className="border-t border-white/5 pt-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="text-[11px] text-stone-500 uppercase tracking-wider">Urmărește-ne</div>
          <div className="flex flex-wrap gap-2" data-testid="footer-socials">
            {links.map((s, i) => {
              const active = !!s.url;
              return (
                <a
                  key={i}
                  href={active ? s.url : "#"}
                  target={active ? "_blank" : undefined}
                  rel={active ? "noopener noreferrer" : undefined}
                  onClick={active ? undefined : (e) => e.preventDefault()}
                  className={`inline-flex items-center gap-2 px-3 py-2 rounded-xl text-xs transition-colors ${active ? "bg-white/5 text-stone-300 hover:bg-white/10 hover:text-white" : "bg-white/[0.03] text-stone-500 cursor-not-allowed"}`}
                  title={active ? s.label : "Link în curând"}
                  data-testid={`social-${s.icon}-${i}`}
                >
                  <SocialIcon icon={s.icon} />
                  <span className="hidden sm:inline">{s.label}</span>
                  {!active && <span className="text-[10px] text-stone-500 italic ml-1">(în curând)</span>}
                </a>
              );
            })}
          </div>
        </div>
        <div className="border-t border-white/5 mt-6 pt-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-2" data-testid="footer-legal">
          <p className="text-[10px] text-stone-600 leading-relaxed">
            PropManage este un brand operat de <strong className="text-stone-500">VINTAGE FURNITURE S.R.L.</strong> · CUI 35250247 · Nr. Reg. Com. J12/3534/2015 · Aleea Negoiu nr. 8D, Ap. 25, Cluj-Napoca, jud. Cluj, 400676
          </p>
          <div className="flex items-center gap-4 text-[10px] text-stone-600 shrink-0">
            <a href="https://anpc.ro/ce-este-sal/" target="_blank" rel="noopener noreferrer" className="hover:text-stone-400 transition-colors" data-testid="footer-anpc-sal">ANPC — SAL</a>
            <a href="https://ec.europa.eu/consumers/odr" target="_blank" rel="noopener noreferrer" className="hover:text-stone-400 transition-colors" data-testid="footer-anpc-sol">SOL — Litigii online</a>
          </div>
        </div>
      </div>
    </footer>
  );
};

// ============= PROMO BANNER (CMS-driven) =============
const PromoBanner = () => {
  const { t } = useI18n();
  const [dismissed, setDismissed] = useState(() => sessionStorage.getItem("pm_promo_dismissed") === "1");
  const text = t("landing.promo_banner");
  if (dismissed || !text || text === "landing.promo_banner") return null;
  const close = () => { sessionStorage.setItem("pm_promo_dismissed", "1"); setDismissed(true); };
  return (
    <div className="fixed top-0 left-0 right-0 z-[60] bg-gradient-to-r from-[#d4ff3a] via-[#a8e028] to-[#d4ff3a] text-black text-center text-xs sm:text-sm font-medium py-2 px-12 flex items-center justify-center gap-2" data-testid="promo-banner">
      <Sparkles className="w-3.5 h-3.5" />
      <span className="truncate max-w-[80vw]">{text}</span>
      <button onClick={close} className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-black/10 rounded-full" data-testid="promo-banner-close" aria-label="Închide">
        <Minus className="w-3.5 h-3.5 rotate-45" />
      </button>
    </div>
  );
};

// ============= LANDING PAGE =============
const LandingPage = () => {
  useDynamicSEO("home", {
    title: "PropManage — Cartea Digitală a Casei Tale · Documente, istoric, specialiști",
    description: "Cartea Digitală a Casei Tale — documentele proprietății, istoricul lucrărilor, mentenanța și specialiștii verificați ai casei, într-un singur loc.",
  });
  const { t, showSection, isPreview } = useI18n();
  const promoText = t("landing.promo_banner");
  const hasPromo = !!promoText && promoText !== "landing.promo_banner" && sessionStorage.getItem("pm_promo_dismissed") !== "1";
  const [demoOpen, setDemoOpen] = useState(false);

  React.useEffect(() => {
    const handler = () => setDemoOpen(true);
    window.addEventListener("propmanage:book-demo", handler);
    return () => window.removeEventListener("propmanage:book-demo", handler);
  }, []);

  return (
    <div className={`grain min-h-screen bg-[#0a0a0b] text-stone-100 ${(hasPromo || isPreview) ? "pt-9 sm:pt-10" : ""}`}>
      {isPreview && <PreviewBanner />}
      {!isPreview && <PromoBanner />}
      <AnnouncementBanner />
      <Nav />
      <Hero />
      <Problem />
      <Solution />
      <HouseHealthAxisLanding />
      <UserJourney />
      <SpecialistJourney />
      <WalletEcosystem />
      <DigitalTwin />
      <LandingDemo3D onBookDemo={() => setDemoOpen(true)} />
      {showSection("landing_show_admin_trust", false) && <AdminTrust />}
      {showSection("landing_show_business_model", false) && <BusinessModel />}
      {showSection("landing_show_value_proposition", true) && <ValueProp />}
      {showSection("landing_show_golden_path", true) && <GoldenPath />}
      <CTA />
      <Footer />
      <BookDemoModal open={demoOpen} onClose={() => setDemoOpen(false)} />
    </div>
  );
};

// ============= PREVIEW MODE BANNER =============
const PreviewBanner = () => (
  <div className="fixed top-0 left-0 right-0 z-[60] bg-gradient-to-r from-amber-500 via-amber-400 to-amber-500 text-black text-center text-xs sm:text-sm font-semibold py-2 px-12 flex items-center justify-center gap-2" data-testid="preview-banner">
    <span>👁 PREVIEW MODE — Modificările tale nesalvate sunt aplicate doar pentru tine</span>
    <a href="/" className="ml-3 underline hover:no-underline text-[11px] opacity-80 hover:opacity-100">Ieși din preview →</a>
  </div>
);

const ExplainThisMount = () => {
  const { user } = useAuth();
  if (!user) return null;
  return <ExplainThis role={user.role} />;
};

// ============= MAIN APP =============
function App() {
  return (
    <div className="App">
      <ThemeProvider>
      <DesignTokensProvider>
      <I18nProvider>
        <AuthProvider>
          <BrowserRouter>
            <ErrorBoundary>
              <ImpersonationBanner />
              <RoleThemeApplier />
              <AnalyticsRouteTracker />
              <ExplainThisMount />
              <Suspense fallback={<div className="min-h-[60vh] flex items-center justify-center"><div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" /></div>}>
              <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/design-interior" element={<InteriorDesignLanding />} />
              <Route path="/design-interior/stil/:slug" element={<DesignInteriorPage kind="style" />} />
              <Route path="/design-interior/:slug" element={<DesignInteriorPage kind="page" />} />
              <Route path="/design-exterior" element={<ServiceHubLanding slug="design-exterior" />} />
              <Route path="/arhitectura" element={<ServiceHubLanding slug="arhitectura" />} />
              <Route path="/franciza" element={<FranchiseDashboard />} />
              <Route path="/devino-francizat" element={<FranchiseApplyPage />} />
              <Route path="/devino-specialist" element={<SpecialistApplyPage />} />
              <Route path="/franchise_admin" element={<FranchiseDashboard />} />
              <Route path="/servicii/design-interior" element={<Navigate to="/design-interior" replace />} />
              <Route path="/demo" element={<PublicDemoPage />} />
              <Route path="/privacy" element={<PrivacyPage />} />
              <Route path="/privacy/notices" element={<PrivacyNoticesPage />} />
              <Route path="/digital-twin" element={<DigitalTwinPage />} />
              <Route path="/report-respond/:token" element={<ReportApprovalPage />} />
              <Route path="/terms" element={<TermsPage />} />
              <Route path="/cookies" element={<CookiePolicyPage />} />
              <Route path="/trust" element={<TrustCenterPage />} />
              <Route path="/status" element={<StatusPage />} />
              <Route path="/components-v2" element={<DesignSystemShowcase />} />
              <Route path="/community" element={<CommunityPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/auth" element={<Navigate to="/login" replace />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/verify-email" element={<EmailVerifyPage />} />
              <Route path="/client/requests/:requestId/offers" element={<ClientRequestOffersPage />} />
              <Route path="/specialist/premium-profile" element={<PremiumProfileEditorPage />} />
              <Route path="/specialist/capabilities" element={<CapabilityEditorPage />} />
              <Route path="/kyc" element={<KYCPage />} />
              <Route path="/auth/callback" element={<AuthCallback />} />
              <Route path="/marketplace" element={<ServiceGate serviceId="specialisti"><PublicMarketplace /></ServiceGate>} />
              <Route path="/marketplace/:slug" element={<ServiceGate serviceId="specialisti"><MarketplaceLanding /></ServiceGate>} />
              <Route path="/servicii/:id" element={<ServiceProvidersPage />} />
              <Route path="/imobile-verificate" element={<EstateBrowse />} />
              <Route path="/de-ce-noi" element={<WhyUsPage />} />
              <Route path="/imobile-verificate/sell" element={<SellMyProperty />} />
              <Route path="/admin/imobile-verificate" element={<VerifiedEstateAdmin />} />
              <Route path="/admin/settings-control" element={<AdminSettingsControl />} />
              <Route path="/admin/documentation" element={<AdminDocumentation />} />
              <Route path="/admin/qa-copilot" element={<QACopilotPage />} />
              <Route path="/admin/ai-control" element={<AIControlCenterPage />} />
              <Route path="/ai-docs" element={<DocsAIPage />} />
              <Route path="/admin/ai-dev-team" element={<AIDevTeamPage />} />
              <Route path="/admin/ai-security" element={<AISecurityCenterPage />} />
              <Route path="/admin/autonomy" element={<AutonomyEnginePage />} />
              <Route path="/admin/orchestrator" element={<AutonomyOrchestratorPage />} />
              <Route path="/admin/construction" element={<ConstructionIntelligencePage />} />
              <Route path="/admin/control-tower" element={<ControlTowerPage />} />
              <Route path="/admin/twin" element={<TwinPage />} />
              <Route path="/house-health/:twinId" element={<HouseHealthPage />} />
              <Route path="/house-health/upgrade" element={<HouseHealthUpgradeLazy />} />
              <Route path="/house-health/upgrade/success" element={<HouseHealthUpgradeSuccessLazy />} />
              <Route path="/pricing" element={<PricingPageLazy />} />
              <Route path="/admin/house-health" element={<AdminHouseHealthPage />} />
              <Route path="/admin/manual-tester" element={<ManualTesterPage />} />
              <Route path="/admin/todo" element={<AdminTodoBoard />} />
              <Route path="/admin/experience-spaces" element={<ExperienceSpacesPage />} />
              <Route path="/admin/future-ideas" element={<FutureIdeasVault />} />
              <Route path="/admin/founder-gate" element={<FounderGatePage />} />
              <Route path="/admin/ai-governance" element={<AIGovernancePage />} />
              <Route path="/admin/design-audit" element={<DesignAuditPage />} />
              <Route path="/admin/design-studio" element={<DesignStudioPage />} />
              <Route path="/admin/design-intelligence" element={<DesignIntelligencePage />} />
              <Route path="/admin/interior-design" element={<InteriorDesignAdminPage />} />
              <Route path="/admin/menu-manager" element={<MenuManagerPage />} />
              <Route path="/admin/page-registry" element={<PageRegistryPage />} />
              <Route path="/admin/design-tokens" element={<Navigate to="/admin/design-studio" replace />} />
              <Route path="/admin/config-io" element={<ConfigIOPage />} />
              <Route path="/admin/xos-builder" element={<XOSBuilderPage />} />
              <Route path="/admin/ui-rules" element={<UIRulesPage />} />
              <Route path="/admin/content-manager" element={<ContentManagerPage />} />
              <Route path="/admin/roadmap" element={<PlatformRoadmapPage />} />
              <Route path="/admin/command-center" element={<CommandCenterPage />} />
              <Route path="/admin/business-health" element={<BusinessHealthPage />} />
              <Route path="/admin/marketplace-intel" element={<MarketplaceIntelPage />} />
              <Route path="/admin/financial-cockpit" element={<FinancialCockpitPage />} />
              <Route path="/admin/automation" element={<AutomationCenterPage />} />
              <Route path="/admin/ceo" element={<CEODashboardPage />} />
              <Route path="/admin/war-room" element={<FirstRevenueWarRoom />} />
              <Route path="/admin/beta-cockpit" element={<BetaCockpitPage />} />
              <Route path="/admin/beta-issues" element={<BetaIssuesPage />} />
              <Route path="/admin/operations" element={<OperationsCenter />} />
              <Route path="/admin/knowledge-center" element={<KnowledgeCenter />} />
              <Route path="/admin/explorer" element={<EnterpriseExplorer />} />
              <Route path="/admin/architecture" element={<ArchitectureNavigator />} />
              <Route path="/admin/enterprise-health" element={<EnterpriseHealthPage />} />
              <Route path="/admin/repair-center" element={<RepairCenterPage />} />
              <Route path="/admin/ai-brain" element={<AIBrainPage />} />
              <Route path="/admin/prop-benefits" element={<PropBenefitsAdminPage />} />
              <Route path="/admin/storage" element={<StorageAdminPage />} />
              <Route path="/admin/ceo-briefing" element={<CeoBriefingPage />} />
              <Route path="/admin/evolution-council" element={<EvolutionCouncilPage />} />
              <Route path="/admin/notification-center" element={<NotificationCenterPage />} />
              <Route path="/admin/user-timeline" element={<UserTimelinePage />} />
              <Route path="/admin/ai-search" element={<AISearchPage />} />
              <Route path="/admin/bug-memory" element={<BugMemoryAggregatorPage />} />
              <Route path="/admin/architecture-board" element={<ArchitectureBoardPage />} />
              <Route path="/admin/ai-pm" element={<AIProductManagerPage />} />
              <Route path="/admin/operating-manual" element={<OperatingManualPage />} />
              <Route path="/admin/experience-tiers" element={<ExperienceTiersPage />} />
              <Route path="/admin/feature-configurator" element={<FeatureConfiguratorPage />} />
              <Route path="/admin/specialist-progression" element={<SpecialistProgressionPage />} />
              <Route path="/admin/bi-moe" element={<BIMoePage />} />
              <Route path="/admin/analytics-growth" element={<AnalyticsGrowthPage />} />
              <Route path="/admin/function-map" element={<FunctionMap />} />
              <Route path="/admin/growth-intel" element={<GrowthIntelligencePage />} />
              <Route path="/admin/lead-intel" element={<LeadIntelligencePage />} />
              <Route path="/admin/marketing-intel" element={<MarketingIntelligencePage />} />
              <Route path="/admin/learning" element={<LearningEnginePage />} />
              <Route path="/admin/it-collaborators" element={<ITCollaboratorsHubPage />} />
              <Route path="/admin/it-collaborators/copilot" element={<ITCopilotPage />} />
              <Route path="/admin/legal-audit" element={<LegalAuditPage />} />
              <Route path="/admin/city-partners" element={<CityPartnersPage />} />
              <Route path="/admin/city-partner-products" element={<CityPartnerProductsPage />} />
              <Route path="/admin/city-partners/:id" element={<CityPartnerDetailPage />} />
              <Route path="/admin/marketplace-partners" element={<MarketplacePartnersPage />} />
              <Route path="/admin/strategic-partners" element={<StrategicPartnersDashboard />} />
              <Route path="/admin/marketing" element={<MarketingDepartmentPage />} />
              <Route path="/admin/demo-accounts" element={<DemoAccountsPage />} />
              <Route path="/admin/admin-accounts" element={<AdminAccountsPage />} />
              <Route path="/admin/demo-activity" element={<DemoActivityPage />} />
              <Route path="/partner/dashboard" element={<PartnerDashboard />} />
              <Route path="/partner/marketplace" element={<MarketplacePartnerPortal />} />
              <Route path="/dashboard/client-junior" element={<ClientJuniorDashboard />} />
              <Route path="/incepe" element={<ClientJuniorDashboard />} />
              <Route path="/legal/sign" element={<LegalSignPage />} />
              <Route path="/contracts/:id" element={<ContractPage />} />
              <Route path="/imobile-verificate/:id" element={<EstateDetail />} />
              <Route path="/ghiduri" element={<GhiduriIndex />} />
              <Route path="/scorul-casei" element={<HealthScorePage />} />
              <Route path="/p/:slug" element={<PublicPassportPage />} />
              <Route path="/checklist-cumparare" element={<BuyingChecklistPage />} />
              <Route path="/preturi" element={<PreturiIndex />} />
              <Route path="/preturi/:slug" element={<PreturiPage />} />
              <Route path="/ghiduri/:slug" element={<GhidPage />} />
              <Route path="/probleme-casa" element={<ProblemeIndex />} />
              <Route path="/probleme-casa/:slug" element={<ProblemaPage />} />
              <Route path="/help/:token" element={<HelpPage />} />
              <Route path="/specialists/:id" element={<SpecialistProfile />} />
              <Route path="/client" element={<ClientDashboardV2 />} />
              <Route path="/administrator" element={<AdministratorWorkspace />} />
              <Route path="/specialist" element={<SpecialistDashboard />} />
              <Route path="/admin" element={<AdminDashboard />} />
              <Route path="/admin/auth-health" element={<AdminAuthHealthPage />} />
              <Route path="/admin/research-coverage" element={<ResearchCoveragePage />} />
              <Route path="/admin/support-inbox" element={<AdminSupportInboxPage />} />
              <Route path="/operator" element={<OperatorDashboard />} />
              <Route path="/projects/:id" element={<ProjectWorkspace />} />
              <Route path="/payment-success" element={<PaymentSuccess />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
              </Suspense>
            <TutorialOverlay />
            <RoleTour />
            <AIConciergeBubble />
            <CookieBanner />
            <BetaFeedbackWidget />
            <AssistantDock />
            <LegalGate />
            <EntitlementToast />
            <Toaster position="top-right" richColors closeButton />
            </ErrorBoundary>
          </BrowserRouter>
        </AuthProvider>
      </I18nProvider>
      </DesignTokensProvider>
      </ThemeProvider>
    </div>
  );
}

export default App;
;
