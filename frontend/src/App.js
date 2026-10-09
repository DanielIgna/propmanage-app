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
import { LoginPage, RegisterPage } from "./views/Auth";
import { EmailVerifyPage } from "./views/EmailVerifyPage";
const ClientRequestOffersPage = lazy(() => import("./views/ClientRequestOffersPage").then(m => ({ default: m.ClientRequestOffersPage })));
const PremiumProfileEditorPage = lazy(() => import("./views/PremiumProfileEditorPage").then(m => ({ default: m.PremiumProfileEditorPage })));
import { CookieBanner } from "./components/CookieBanner";
import { BetaFeedbackWidget } from "./components/BetaFeedbackWidget";
import { AssistantDock } from "./components/AssistantDock";
import { ThemeToggle } from "./views/DashShared";
const SpecialistDashboard = lazy(() => import("./views/Dashboards").then(m => ({ default: m.SpecialistDashboard })));
const AdminDashboard = lazy(() => import("./views/Dashboards").then(m => ({ default: m.AdminDashboard })));
const OperatorDashboard = lazy(() => import("./views/Dashboards").then(m => ({ default: m.OperatorDashboard })));
import { AuthCallback } from "./views/AuthCallback";
import { SpecialistProfile } from "./views/SpecialistProfile";
import { PublicMarketplace } from "./views/Marketplace";
import { MarketplaceLanding } from "./views/MarketplaceLanding";
import { GhiduriIndex } from "./views/GhiduriIndex";
import { GhidPage } from "./views/GhidPage";
import { ProblemeIndex } from "./views/ProblemeIndex";
import { ProblemaPage } from "./views/ProblemaPage";
import { DesignInteriorPage } from "./views/DesignInteriorPage";
import { HelpPage } from "./views/HelpPage";
import { ProjectWorkspace } from "./views/ProjectWorkspace";
import { PaymentSuccess } from "./views/PaymentSuccess";
import { TutorialOverlay } from "./views/TutorialOverlay";
import { RoleTour } from "./views/RoleTour";
import { AIConciergeBubble } from "./components/AIConciergeBubble";
import { BookDemoModal } from "./views/BookDemoModal";
import { LandingDemo3D } from "./components/LandingDemo3D";
import { BuildingDiscovery } from "./components/BuildingDiscovery";
const PublicDemoPage = lazy(() => import("./views/PublicDemoPage").then(m => ({ default: m.PublicDemoPage })));
const AdminAuthHealthPage = lazy(() => import("./views/admin/AdminAuthHealthPage").then(m => ({ default: m.AdminAuthHealthPage })));
const ResearchCoveragePage = lazy(() => import("./views/admin/ResearchCoveragePage"));
const AcquisitionPage = lazy(() => import("./views/AcquisitionPage"));
const AdminSupportInboxPage = lazy(() => import("./views/admin/AdminSupportInboxPage").then(m => ({ default: m.AdminSupportInboxPage })));
import { PrivacyPage, TermsPage, CookiePolicyPage } from "./views/LegalPages";
const TrustCenterPage = lazy(() => import("./views/TrustCenterPage").then(m => ({ default: m.TrustCenterPage })));
const PrivacyNoticesPage = lazy(() => import("./views/PrivacyNoticesPage").then(m => ({ default: m.PrivacyNoticesPage })));
const StatusPage = lazy(() => import("./views/StatusPage").then(m => ({ default: m.StatusPage })));
const DesignSystemShowcase = lazy(() => import("./views/DesignSystemShowcase"));
const CommunityPage = lazy(() => import("./views/CommunityPage"));
import { GDPRAuditBadge } from "./components/GDPRAuditBadge";
import { TrustStrip } from "./components/TrustStrip";
const DigitalTwinPage = lazy(() => import("./views/DigitalTwinPage"));
const BlocuriExplorer = lazy(() => import("./views/BlocuriPublic").then(m => ({ default: m.BlocuriExplorer })));
const BlocuriBuildingDetail = lazy(() => import("./views/BlocuriPublic").then(m => ({ default: m.BlocuriBuildingDetail })));
const BlocuriCluster = lazy(() => import("./views/BlocuriPublic").then(m => ({ default: m.BlocuriCluster })));
const PropertyGISPage = lazy(() => import("./views/PropertyGIS").then(m => ({ default: m.PropertyGISPage })));
const ReportApprovalPage = lazy(() => import("./views/ReportApprovalPage"));
const KYCPage = lazy(() => import("./views/KYCPage"));
const EstateBrowse = lazy(() => import("./views/verified-estate/EstateBrowse").then(m => ({ default: m.EstateBrowse })));
const EstateDetail = lazy(() => import("./views/verified-estate/EstateDetail").then(m => ({ default: m.EstateDetail })));
const SellMyProperty = lazy(() => import("./views/verified-estate/SellMyProperty").then(m => ({ default: m.SellMyProperty })));
const VerifiedEstateAdmin = lazy(() => import("./views/verified-estate/VerifiedEstateAdmin").then(m => ({ default: m.VerifiedEstateAdmin })));
const WhyUsPage = lazy(() => import("./views/WhyUsPage"));
const AdminSettingsControl = lazy(() => import("./views/admin/AdminSettingsControl"));
const HartaBlocuriAdmin = lazy(() => import("./views/admin/HartaBlocuriAdmin"));
const HartaBlocuriObservability = lazy(() => import("./views/admin/HartaBlocuriObservability"));
const AdminDocumentation = lazy(() => import("./views/admin/AdminDocumentation"));
const QACopilotPage = lazy(() => import("./views/admin/QACopilotPage"));
const AIControlCenterPage = lazy(() => import("./views/admin/AIControlCenterPage"));
const DocsAIPage = lazy(() => import("./views/DocsAIPage"));
const AIDevTeamPage = lazy(() => import("./views/admin/AIDevTeamPage"));
const AISecurityCenterPage = lazy(() => import("./views/admin/AISecurityCenterPage"));
const AutonomyEnginePage = lazy(() => import("./views/admin/AutonomyEnginePage"));
const AutonomyOrchestratorPage = lazy(() => import("./views/admin/AutonomyOrchestratorPage"));
const ConstructionIntelligencePage = lazy(() => import("./views/admin/ConstructionIntelligencePage"));
const ControlTowerPage = lazy(() => import("./views/admin/ControlTowerPage"));
const TwinPage = lazy(() => import("./views/admin/TwinPage"));
const AdminHouseHealthPage = lazy(() => import("./views/admin/AdminHouseHealthPage"));
const ManualTesterPage = lazy(() => import("./views/admin/ManualTesterPage"));
const HouseHealthPage = lazy(() => import("./views/HouseHealthPage"));
const HouseHealthUpgradeLazy = lazy(() => import("./views/HouseHealthUpgradePage"));
const PricingPageLazy = lazy(() => import("./views/PricingPage"));
const HouseHealthUpgradeSuccessLazy = lazy(() => import("./views/HouseHealthUpgradePage").then(m => ({ default: m.HouseHealthUpgradeSuccess })));
const AdminTodoBoard = lazy(() => import("./views/admin/AdminTodoBoard"));
const ExperienceSpacesPage = lazy(() => import("./views/admin/ExperienceSpacesPage"));
const FutureIdeasVault = lazy(() => import("./views/admin/FutureIdeasVault"));
const FounderGatePage = lazy(() => import("./views/admin/FounderGatePage"));
const AIGovernancePage = lazy(() => import("./views/admin/AIGovernancePage"));
const DesignAuditPage = lazy(() => import("./views/admin/DesignAuditPage"));
const DesignStudioPage = lazy(() => import("./views/admin/DesignStudioPage"));
const DesignIntelligencePage = lazy(() => import("./views/admin/DesignIntelligencePage"));
const PlatformRoadmapPage = lazy(() => import("./views/admin/PlatformRoadmapPage"));
const CommandCenterPage = lazy(() => import("./views/admin/CommandCenterPage"));
const BusinessHealthPage = lazy(() => import("./views/admin/BusinessHealthPage"));
const MarketplaceIntelPage = lazy(() => import("./views/admin/MarketplaceIntelPage"));
const FinancialCockpitPage = lazy(() => import("./views/admin/FinancialCockpitPage"));
const AutomationCenterPage = lazy(() => import("./views/admin/AutomationCenterPage"));
const CEODashboardPage = lazy(() => import("./views/admin/CEODashboardPage"));
const FirstRevenueWarRoom = lazy(() => import("./views/admin/FirstRevenueWarRoom"));
const BetaCockpitPage = lazy(() => import("./views/admin/BetaCockpitPage"));
const BetaIssuesPage = lazy(() => import("./views/admin/BetaIssuesPage"));
const CapabilityEditorPage = lazy(() => import("./views/CapabilityEditorPage"));
const OperationsCenter = lazy(() => import("./views/admin/OperationsCenter"));
const KnowledgeCenter = lazy(() => import("./views/admin/KnowledgeCenter"));
const EnterpriseExplorer = lazy(() => import("./views/admin/EnterpriseExplorer"));
const ArchitectureNavigator = lazy(() => import("./views/admin/ArchitectureNavigator"));
const EnterpriseHealthPage = lazy(() => import("./views/admin/EnterpriseHealthPage"));
const RepairCenterPage = lazy(() => import("./views/admin/RepairCenterPage"));
const AIBrainPage = lazy(() => import("./views/admin/AIBrainPage"));
const PropBenefitsAdminPage = lazy(() => import("./views/admin/PropBenefitsAdminPage"));
const StorageAdminPage = lazy(() => import("./views/admin/StorageAdminPage"));
const ServiceProvidersPage = lazy(() => import("./views/ServiceProvidersPage"));
const CeoBriefingPage = lazy(() => import("./views/admin/CeoBriefingPage"));
const EvolutionCouncilPage = lazy(() => import("./views/admin/EvolutionCouncilPage"));
const HealthScorePage = lazy(() => import("./views/growth/HealthScorePage"));
const PublicPassportPage = lazy(() => import("./views/PublicPassportPage"));
const BuyingChecklistPage = lazy(() => import("./views/growth/BuyingChecklistPage"));
const NotificationCenterPage = lazy(() => import("./views/admin/NotificationCenterPage"));
const UserTimelinePage = lazy(() => import("./views/admin/UserTimelinePage"));
const AISearchPage = lazy(() => import("./views/admin/AISearchPage"));
const InteriorDesignLanding = lazy(() => import("./views/InteriorDesignLanding"));
const InteriorDesignAdminPage = lazy(() => import("./views/admin/InteriorDesignAdminPage"));
const MenuManagerPage = lazy(() => import("./views/admin/MenuManagerPage"));
const PageRegistryPage = lazy(() => import("./views/admin/PageRegistryPage"));
const ConfigIOPage = lazy(() => import("./views/admin/ConfigIOPage"));
const XOSBuilderPage = lazy(() => import("./views/admin/XOSBuilderPage"));
const ServiceHubLanding = lazy(() => import("./views/ServiceHubLanding"));
const FranchiseDashboard = lazy(() => import("./views/FranchiseDashboard"));
const FranchiseApplyPage = lazy(() => import("./views/FranchiseApplyPage"));
const SpecialistApplyPage = lazy(() => import("./views/SpecialistApplyPage"));
const UIRulesPage = lazy(() => import("./views/admin/UIRulesPage"));
const ContentManagerPage = lazy(() => import("./views/admin/ContentManagerPage"));
const BugMemoryAggregatorPage = lazy(() => import("./views/admin/BugMemoryAggregatorPage"));
const ArchitectureBoardPage = lazy(() => import("./views/admin/ArchitectureBoardPage"));
const AIProductManagerPage = lazy(() => import("./views/admin/AIProductManagerPage"));
const OperatingManualPage = lazy(() => import("./views/admin/OperatingManualPage"));
const ExperienceTiersPage = lazy(() => import("./views/admin/ExperienceTiersPage"));
const FeatureConfiguratorPage = lazy(() => import("./views/admin/FeatureConfiguratorPage"));
const SpecialistProgressionPage = lazy(() => import("./views/admin/SpecialistProgressionPage"));
const BIMoePage = lazy(() => import("./views/admin/BIMoePage"));
const AnalyticsGrowthPage = lazy(() => import("./views/admin/AnalyticsGrowthPage"));
const FunctionMap = lazy(() => import("./views/admin/FunctionMap"));
const GrowthIntelligencePage = lazy(() => import("./views/admin/GrowthIntelligencePage"));
const LeadIntelligencePage = lazy(() => import("./views/admin/LeadIntelligencePage"));
const MarketingIntelligencePage = lazy(() => import("./views/admin/MarketingIntelligencePage"));
const LearningEnginePage = lazy(() => import("./views/admin/LearningEnginePage"));
const ITCollaboratorsHubPage = lazy(() => import("./views/admin/ITCollaboratorsHubPage"));
const ITCopilotPage = lazy(() => import("./views/admin/ITCopilotPage"));
const LegalAuditPage = lazy(() => import("./views/admin/LegalAuditPage"));
const LegalSignPage = lazy(() => import("./views/LegalSignPage"));
import LegalGate from "./components/LegalGate";
const CityPartnersPage = lazy(() => import("./views/admin/CityPartnersPage"));
const CityPartnerProductsPage = lazy(() => import("./views/admin/CityPartnerProductsPage"));
const CityPartnerDetailPage = lazy(() => import("./views/admin/CityPartnerDetailPage"));
const MarketplacePartnersPage = lazy(() => import("./views/admin/MarketplacePartnersPage"));
const StrategicPartnersDashboard = lazy(() => import("./views/admin/StrategicPartnersDashboard"));
const MarketingDepartmentPage = lazy(() => import("./views/admin/MarketingDepartmentPage"));
const DemoAccountsPage = lazy(() => import("./views/admin/DemoAccountsPage"));
const AdminAccountsPage = lazy(() => import("./views/admin/AdminAccountsPage"));
const DemoActivityPage = lazy(() => import("./views/admin/DemoActivityPage"));
const PartnerDashboard = lazy(() => import("./views/partner/PartnerDashboard"));
const MarketplacePartnerPortal = lazy(() => import("./views/partner/MarketplacePartnerPortal"));
const ClientJuniorDashboard = lazy(() => import("./views/dashboard/ClientJuniorDashboard"));
const ClientDashboardV2 = lazy(() => import("./views/clientv2/ClientDashboardV2"));
const AdministratorWorkspace = lazy(() => import("./views/AdministratorWorkspace"));
const ContractPage = lazy(() => import("./views/ContractPage"));
const PreturiIndex = lazy(() => import("./views/PreturiIndex"));
const PreturiPage = lazy(() => import("./views/PreturiPage"));
import { trackPageView } from "@/lib/analytics";
import { useDynamicSEO } from "@/lib/useDynamicSEO";
import { HOUSE_HEALTH_AXIS, AXIS_DISCLAIMER } from "@/lib/houseHealthAxis";

const AnalyticsRouteTracker = () => {
  const location = useLocation();
  React.useEffect(() => {
    trackPageView(location.pathname + location.search);
    // AI Brain · Navigation Context (doar utilizatori autentificați, fire-and-forget)
    if (localStorage.getItem("pm_session_hint")) {
      fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/ai-brain/navigation`, {
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

import { LandingPage } from "./landing/LandingPage";

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
              <Route path="/pentru-proprietari" element={<AcquisitionPage />} />
              <Route path="/cartea-casei" element={<AcquisitionPage />} />
              <Route path="/pentru-specialisti" element={<AcquisitionPage />} />
              <Route path="/pentru-specialisti/:trade" element={<AcquisitionPage />} />
              <Route path="/pentru-designeri" element={<AcquisitionPage />} />
              <Route path="/franchise_admin" element={<FranchiseDashboard />} />
              <Route path="/servicii/design-interior" element={<Navigate to="/design-interior" replace />} />
              <Route path="/demo" element={<PublicDemoPage />} />
              <Route path="/privacy" element={<PrivacyPage />} />
              <Route path="/privacy/notices" element={<PrivacyNoticesPage />} />
              <Route path="/digital-twin" element={<DigitalTwinPage />} />
              <Route path="/blocuri" element={<BlocuriExplorer />} />
              <Route path="/blocuri/cladire/:id" element={<BlocuriBuildingDetail />} />
              <Route path="/blocuri/*" element={<BlocuriCluster />} />
              <Route path="/property/:id/gis" element={<PropertyGISPage />} />
              <Route path="/property/:id/map" element={<PropertyGISPage />} />
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
              <Route path="/admin/hartablocuri" element={<HartaBlocuriAdmin />} />
              <Route path="/admin/harta-blocuri" element={<HartaBlocuriObservability />} />
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
