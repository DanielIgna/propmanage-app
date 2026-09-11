// Main Admin Console — Metronic-style entry point. Replaces old AdminDashboard.
import React, { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../../auth";
import { AdminLayoutMetronic } from "./AdminLayoutMetronic";
import { AdminOverview } from "./AdminOverview";
import { AdminUsers } from "./AdminUsers";
import { AdminVerification, AdminDisputes } from "./AdminVerificationDisputes";
import { AdminCMS, AdminEmailTemplates, AdminZones } from "./AdminContentTools";
import {
  AdminTrustWeights, AdminPlatformSettings, AdminFinance, AdminProjects, AdminActivityFull
} from "./AdminPlatformTools";
import { AdminABTests } from "./AdminABTests";
import { AdminAuditLog } from "./AdminAuditLog";
import { AdminAIConsole } from "./AdminAIConsole";
import { AdminConciergePanel } from "./AdminConciergePanel";
import { AdminDemoTimeMachine } from "./AdminDemoTimeMachine";
import { AdminDemoLeads } from "./AdminDemoLeads";
import { AdminGDPR } from "./AdminGDPR";
import { AdminImpersonationLogs } from "./AdminImpersonationLogs";
import { AdminBetaTesters } from "./AdminBetaTesters";
import { AdminDocs } from "./AdminDocs";
import { AdminQAPlaybook } from "./AdminQAPlaybook";
import { AdminSubAdmins } from "./AdminSubAdmins";
import { AdminApprovals } from "./AdminApprovals";
import { AdminKYCQueue } from "./AdminKYCQueue";
import { AdminSEO } from "./AdminSEO";

const TITLES = {
  overview: { title: "Dashboard", subtitle: "Privire de ansamblu asupra platformei" },
  ai: { title: "AI Investigator", subtitle: "Consilier AI cu memorie persistentă · Claude Sonnet 4.5 · acces read-only" },
  concierge: { title: "Concierge & Security", subtitle: "AI pentru utilizatori · GEO/VPN/bot block · prompt-injection guard" },
  demo: { title: "Demo Tools", subtitle: "Time Machine pentru ciclul plății — simulare flow complet pentru prospecți" },
  leads: { title: "Demo Leads", subtitle: "Cererile primite de pe site · status tracking · WhatsApp directe" },
  activity: { title: "Activitate Live", subtitle: "Toate evenimentele din sistem (refresh la 10s)" },
  users: { title: "Toți userii", subtitle: "Caută, filtrează, editează, banează" },
  verification: { title: "Verificare specialiști", subtitle: "Coadă de aprobare cu documente" },
  projects: { title: "Proiecte", subtitle: "Workspace-uri de design și mentenanță" },
  disputes: { title: "Dispute & Sesizări", subtitle: "Mediere și rezolvare cazuri" },
  finance: { title: "Finanțe & Escrow", subtitle: "Wallets, tranzacții, payouts" },
  cms: { title: "Texte (CMS)", subtitle: "Editează landing page, etichete UI, categorii" },
  emails: { title: "Template-uri Email", subtitle: "Modifică subiectul și HTML-ul emailurilor automate" },
  zones: { title: "Zone Acoperire", subtitle: "Adaugă orașe / cartiere sau dezactivează cele existente" },
  abtests: { title: "Experimente A/B", subtitle: "Testează variante și măsoară CTR în timp real" },
  trust: { title: "Trust Score Weights", subtitle: "Ajustează ponderea fiecărui factor (suma = 100%)" },
  audit: { title: "Audit Log", subtitle: "Istoric complet al acțiunilor admin · GDPR compliance" },
  settings: { title: "Setări Platformă", subtitle: "Feature flags, comisioane, branding" },
  gdpr: { title: "GDPR Compliance Pack", subtitle: "Pachet documentar pentru DPO · ROPA · DPIA · Sub-procesatori · Cookies · Breach Plan" },
  impersonation: { title: "Impersonare utilizatori", subtitle: "Jurnal sesiuni admin care au accesat contul altor utilizatori · GDPR audit" },
  beta_testers: { title: "Beta Testers", subtitle: "Useri noi în beta · Provenance Google/Email · Activitate engagement" },
  docs: { title: "Documentație & Training", subtitle: "Ghiduri training per rol · trimite pe email cu PDF · link-uri tokenizate" },
  qa_playbook: { title: "QA Playbook", subtitle: "105 scenarii de test interactive · AI Test Suggester (Claude Sonnet 4.5) · markdown export" },
  sub_admins: { title: "Sub-Admini & RBAC", subtitle: "Gestionare conturi admin cu scope · senior/junior · audit log" },
  approvals: { title: "Aprobări Admin", subtitle: "Queue de cereri pendinte · senior aprobă acțiuni junior · istoric decizii" },
  kyc: { title: "KYC · Verificări Identitate", subtitle: "Review documente buletin + selfie · aprobă & marchează VERIFIED" },
  seo: { title: "SEO Control Center", subtitle: "Observability read-only peste fundația SEO · Indexability Gate · Sitemap · URL Inspector · Clusters" },
};

export const AdminDashboard = () => {
  const { user } = useAuth();
  const [active, setActive] = useState(() => {
    const t = new URLSearchParams(window.location.search).get("tab");
    return t && TITLES[t] ? t : "overview";
  });

  React.useEffect(() => {
    if (new URLSearchParams(window.location.search).get("tab")) {
      window.history.replaceState(null, "", "/admin");
    }
  }, []);

  // Listen for cross-component navigation events (e.g. heatmap → audit log)
  React.useEffect(() => {
    const handler = (ev) => {
      if (ev.detail?.tab) setActive(ev.detail.tab);
    };
    window.addEventListener("propmanage:nav-admin", handler);
    return () => window.removeEventListener("propmanage:nav-admin", handler);
  }, []);

  // Auth state: null = checking, false = not authenticated, object = authenticated
  if (user === false) return <Navigate to="/login?next=/admin" replace />;
  if (!user) return (
    <div className="min-h-screen flex items-center justify-center bg-stone-950">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-2 border-[#d4ff3a] border-t-transparent rounded-full animate-spin" />
        <div className="text-stone-300 text-sm">Se încarcă consola admin...</div>
      </div>
    </div>
  );
  const effectiveRole = user.active_view || user.role;
  if (effectiveRole !== "admin") return <Navigate to={`/${effectiveRole}`} replace />;

  const meta = TITLES[active] || TITLES.overview;
  return (
    <AdminLayoutMetronic active={active} onChange={setActive} title={meta.title} subtitle={meta.subtitle}>
      {active === "overview" && <AdminOverview />}
      {active === "ai" && <AdminAIConsole />}
      {active === "concierge" && <AdminConciergePanel />}
      {active === "demo" && <AdminDemoTimeMachine />}
      {active === "leads" && <AdminDemoLeads />}
      {active === "activity" && <AdminActivityFull />}
      {active === "users" && <AdminUsers />}
      {active === "verification" && <AdminVerification />}
      {active === "projects" && <AdminProjects />}
      {active === "disputes" && <AdminDisputes />}
      {active === "finance" && <AdminFinance />}
      {active === "cms" && <AdminCMS />}
      {active === "emails" && <AdminEmailTemplates />}
      {active === "zones" && <AdminZones />}
      {active === "trust" && <AdminTrustWeights />}
      {active === "abtests" && <AdminABTests />}
      {active === "audit" && <AdminAuditLog />}
      {active === "settings" && <AdminPlatformSettings />}
      {active === "gdpr" && <AdminGDPR />}
      {active === "impersonation" && <AdminImpersonationLogs />}
      {active === "beta_testers" && <AdminBetaTesters />}
      {active === "docs" && <AdminDocs />}
      {active === "qa_playbook" && <AdminQAPlaybook />}
      {active === "sub_admins" && <AdminSubAdmins />}
      {active === "approvals" && <AdminApprovals />}
      {active === "kyc" && <AdminKYCQueue />}
      {active === "seo" && <AdminSEO />}
    </AdminLayoutMetronic>
  );
};

export default AdminDashboard;
