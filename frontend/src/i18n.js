// PropManage i18n - bilingv RO/EN + CMS overrides for landing texts
import React, { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const translations = {
  ro: {
    // Nav
    "nav.problem": "Problemă", "nav.solution": "Soluție", "nav.journey": "Experiență",
    "nav.twin": "Digital Twin", "nav.business": "Business", "nav.demo": "Începe Demo",
    "nav.login": "Conectează-te", "nav.logout": "Deconectare", "nav.dashboard": "Dashboard",
    // Common
    "common.loading": "Se încarcă...", "common.save": "Salvează", "common.cancel": "Anulează",
    "common.confirm": "Confirmă", "common.back": "Înapoi", "common.continue": "Continuă",
    "common.email": "Email", "common.password": "Parolă", "common.name": "Nume",
    // Login
    "login.title": "Bine ai venit", "login.subtitle": "Introdu datele pentru a accesa contul",
    "login.submit": "Conectează-te", "login.noAccount": "Nu ai cont?",
    "login.register": "Creează cont nou", "login.demo": "Conturi Demo",
    // Register
    "register.title": "Creează cont", "register.subtitle": "Începe-ți călătoria digitală",
    "register.role": "Tip cont", "register.client": "Proprietar", "register.specialist": "Specialist",
    "register.submit": "Creează cont", "register.hasAccount": "Ai deja cont?",
    // Dashboard Client
    "client.welcome": "Bună", "client.health": "Scor Sănătate",
    "client.requests": "Solicitările Mele", "client.specialists": "Specialiști",
    "client.newRequest": "Solicitare Nouă", "client.tokens": "Tokeni",
    "client.wallet": "Portofel", "client.properties": "Proprietăți",
    "client.viewTwin": "Vezi Digital Twin",
    // Dashboard Specialist
    "spec.opportunities": "Oportunități Noi", "spec.myJobs": "Lucrările Mele",
    "spec.accept": "Acceptă Lead", "spec.balance": "Sold Lead-uri",
    "spec.rating": "Rating", "spec.reviews": "Recenzii", "spec.start": "Pornește lucrarea",
    "spec.complete": "Marchează completă",
    // Admin
    "admin.title": "Panou de Control", "admin.users": "Utilizatori",
    "admin.activeJobs": "Joburi Active", "admin.pending": "Verificare în așteptare",
    "admin.verify": "Verifică", "admin.disputes": "Dispute",
    // Operator
    "op.title": "Validare Mentenanță", "op.approve": "Validare", "op.reject": "Respinge",
    "op.queue": "Coadă de Așteptare",
    // Request states
    "status.open": "Deschis", "status.assigned": "Asignat", "status.in_progress": "În lucru",
    "status.completed": "Finalizat", "status.confirmed": "Confirmat",
    // Categories
    "cat.electric": "Electric", "cat.plumbing": "Sanitar", "cat.hvac": "HVAC",
    "cat.other": "Altele",
    // Landing - Hero
    "hero.badge": "CARTEA DIGITALĂ A CASEI TALE",
    "hero.title1": "Cartea Digitală", "hero.title2": "a Casei", "hero.title3": "Tale.",
    "hero.subtitle": "Documentele casei, istoricul lucrărilor, mentenanța și specialiștii verificați — într-un singur loc. Cartea Digitală a Casei Tale, pregătită în câteva minute.",
    "hero.cta1": "Creează contul gratuit", "hero.cta2": "Vezi cum funcționează",
    "hero.cta1.variant_a": "Creează contul gratuit", "hero.cta1.variant_b": "Creează contul gratuit",
    "hero.cta2.variant_a": "Vezi cum funcționează", "hero.cta2.variant_b": "Vezi cum funcționează",
    "hero.stat1": "banii se eliberează doar după ce confirmi lucrarea", "hero.stat2": "identitate și firmă verificate înainte de primul job",
    "hero.stat3": "la fiecare lucrare finalizată prin platformă", "hero.stat4": "fiecare intervenție rămâne salvată permanent",
    // Sections
    "sec.problem": "Problemă", "sec.solution": "Soluție",
    "sec.experience": "Experiență Utilizator", "sec.specialist": "Experiență Specialist",
    "sec.wallet": "Wallet & Ecosistem", "sec.twin": "Digital Twin · Core Differentiator",
    "sec.admin": "Admin & Trust", "sec.business": "Business Model",
    "sec.value": "Value Proposition", "sec.golden": "Golden Path",
    // Problem
    "problem.title1": "Proprietatea ta e o", "problem.title2": "cutie neagră.",
    "problem.intro": "Majoritatea proprietarilor nu au un loc unde să păstreze documentele, istoricul lucrărilor și intervențiile din propria casă. Fără Cartea Digitală a Casei Tale, informațiile se pierd, iar deciziile se iau pe ghicite.",
    "problem.p1.t": "Nu știi ce e în pereți", "problem.p1.d": "Trasee de instalații, vârste de echipamente, intervenții — totul rămâne ascuns până când ceva se strică.",
    "problem.p2.t": "Zero tracking mentenanță", "problem.p2.d": "Când a fost ultima revizie? Cine a făcut-o? Ce s-a schimbat? Nimeni nu mai știe.",
    "problem.p3.t": "Lipsă de încredere", "problem.p3.d": "Specialiști aleși la întâmplare, fără verificare, fără garanții. Risc constant.",
    "problem.p4.t": "Costuri opace", "problem.p4.d": "Prețuri umflate, lucrări nedocumentate, fără devize transparente sau istoric financiar.",
    // Solution
    "sol.title1": "Un sistem de operare pentru", "sol.title2": "casa ta.",
    "sol.intro": "PropManage îți dă Cartea Digitală a Casei Tale: un loc unic pentru documente, istoricul lucrărilor, mentenanță și specialiștii pe care te bazezi. Informațiile stau ordonat, se actualizează cu fiecare intervenție și rămân cu tine.",
    "sol.tagline": "Nu este un cost. Este o investiție.",
    "sol.p1.t": "Digital Twin", "sol.p1.d": "Replică digitală 3D a proprietății cu toate sistemele și echipamentele mapate.",
    "sol.p2.t": "Marketplace Verificat", "sol.p2.d": "Specialiști triple-verified cu rating real și garanție de servicii.",
    "sol.p3.t": "Escrow Securizat", "sol.p3.d": "Plățile sunt protejate până când lucrarea este confirmată ca finalizată.",
    "sol.p4.t": "Istoric Digital", "sol.p4.d": "Fiecare intervenție, fiecare reparație, fiecare cost — salvat permanent.",
    // CTA
    "cta.badge": "GATA DE LANSARE",
    "cta.title1": "Gata să digitalizezi", "cta.title2": "tot ecosistemul?",
    "cta.intro": "Contul e gratuit. Adaugi casa într-un minut, iar documentele, lucrările și mentenanța rămân în Cartea Digitală a Casei Tale — pentru totdeauna.",
    "cta.btn1": "Creează cont gratuit", "cta.btn2": "Vorbește cu un specialist",
    "cta.btn1.variant_a": "Creează cont gratuit", "cta.btn1.variant_b": "Creează cont gratuit",
    "cta.footer": "Fără card de credit · Contul rămâne gratuit",
  },
  en: {
    // Nav
    "nav.problem": "Problem", "nav.solution": "Solution", "nav.journey": "Experience",
    "nav.twin": "Digital Twin", "nav.business": "Business", "nav.demo": "Start Demo",
    "nav.login": "Sign In", "nav.logout": "Logout", "nav.dashboard": "Dashboard",
    // Common
    "common.loading": "Loading...", "common.save": "Save", "common.cancel": "Cancel",
    "common.confirm": "Confirm", "common.back": "Back", "common.continue": "Continue",
    "common.email": "Email", "common.password": "Password", "common.name": "Name",
    // Login
    "login.title": "Welcome back", "login.subtitle": "Enter your credentials to access your account",
    "login.submit": "Sign In", "login.noAccount": "No account?",
    "login.register": "Create new account", "login.demo": "Demo Accounts",
    // Register
    "register.title": "Create account", "register.subtitle": "Start your digital journey",
    "register.role": "Account type", "register.client": "Homeowner", "register.specialist": "Specialist",
    "register.submit": "Create account", "register.hasAccount": "Already have an account?",
    // Dashboard Client
    "client.welcome": "Hi", "client.health": "Health Score",
    "client.requests": "My Requests", "client.specialists": "Specialists",
    "client.newRequest": "New Request", "client.tokens": "Tokens",
    "client.wallet": "Wallet", "client.properties": "Properties",
    "client.viewTwin": "View Digital Twin",
    // Specialist
    "spec.opportunities": "New Opportunities", "spec.myJobs": "My Jobs",
    "spec.accept": "Accept Lead", "spec.balance": "Lead Balance",
    "spec.rating": "Rating", "spec.reviews": "Reviews", "spec.start": "Start work",
    "spec.complete": "Mark complete",
    // Admin
    "admin.title": "Control Panel", "admin.users": "Users",
    "admin.activeJobs": "Active Jobs", "admin.pending": "Pending verification",
    "admin.verify": "Verify", "admin.disputes": "Disputes",
    // Operator
    "op.title": "Maintenance Validation", "op.approve": "Approve", "op.reject": "Reject",
    "op.queue": "Queue",
    // Status
    "status.open": "Open", "status.assigned": "Assigned", "status.in_progress": "In Progress",
    "status.completed": "Completed", "status.confirmed": "Confirmed",
    // Categories
    "cat.electric": "Electric", "cat.plumbing": "Plumbing", "cat.hvac": "HVAC",
    "cat.other": "Other",
    // Hero
    "hero.badge": "PROPERTY OPERATING SYSTEM • V4.2",
    "hero.title1": "Your property,", "hero.title2": "perfected", "hero.title3": "digitally.",
    "hero.subtitle": "PropManage builds a high-fidelity Digital Twin of your home, monitoring structural condition and financial performance in real time. Structured peace of mind for the modern owner.",
    "hero.cta1": "Explore Demo", "hero.cta2": "See Full Flow",
    "hero.cta1.variant_a": "Explore Demo", "hero.cta1.variant_b": "Start free now",
    "hero.cta2.variant_a": "See Full Flow", "hero.cta2.variant_b": "See how it works in 2 min",
    "hero.stat1": "Active users", "hero.stat2": "Active jobs",
    "hero.stat3": "Verified specialists", "hero.stat4": "Portfolio health",
    // Sections
    "sec.problem": "Problem", "sec.solution": "Solution",
    "sec.experience": "User Experience", "sec.specialist": "Specialist Experience",
    "sec.wallet": "Wallet & Ecosystem", "sec.twin": "Digital Twin · Core Differentiator",
    "sec.admin": "Admin & Trust", "sec.business": "Business Model",
    "sec.value": "Value Proposition", "sec.golden": "Golden Path",
    // Problem
    "problem.title1": "Your property is a", "problem.title2": "black box.",
    "problem.intro": "85% of homeowners have no documentation about installations, equipment or interventions in their own home. That means risk, costs and value loss.",
    "problem.p1.t": "You don't know what's in your walls", "problem.p1.d": "Plumbing paths, equipment age, interventions — all hidden until something breaks.",
    "problem.p2.t": "Zero maintenance tracking", "problem.p2.d": "When was the last service? Who did it? What changed? Nobody knows anymore.",
    "problem.p3.t": "Lack of trust", "problem.p3.d": "Specialists picked at random, no verification, no warranty. Constant risk.",
    "problem.p4.t": "Opaque costs", "problem.p4.d": "Inflated prices, undocumented work, no transparent quotes or financial history.",
    // Solution
    "sol.title1": "An operating system for", "sol.title2": "your home.",
    "sol.intro": "PropManage turns your physical property into a digital asset. Diagnostic, analytics, control — all in one platform, with total transparency and secured payments.",
    "sol.tagline": "Not a cost. An investment.",
    "sol.p1.t": "Digital Twin", "sol.p1.d": "3D digital replica of the property with all systems and equipment mapped.",
    "sol.p2.t": "Verified Marketplace", "sol.p2.d": "Triple-verified specialists with real ratings and service guarantee.",
    "sol.p3.t": "Secure Escrow", "sol.p3.d": "Payments are protected until the work is confirmed as completed.",
    "sol.p4.t": "Digital History", "sol.p4.d": "Every intervention, every repair, every cost — saved permanently.",
    // CTA
    "cta.badge": "READY TO BUILD",
    "cta.title1": "Ready to digitize", "cta.title2": "your entire ecosystem?",
    "cta.intro": "The account is free. Add your home in a minute — every document and every job stays in your home's logbook, forever.",
    "cta.btn1": "Create free account", "cta.btn2": "Talk to specialist",
    "cta.btn1.variant_a": "Create free account", "cta.btn1.variant_b": "Start free · 14 days",
    "cta.footer": "No credit card required · Cancel anytime · 14-day trial",
  }
};

const I18nContext = createContext(null);

export const I18nProvider = ({ children }) => {
  const [lang, setLang] = useState(() => localStorage.getItem("propmanage_lang") || "ro");
  const [cms, setCms] = useState({}); // CMS overrides (RO only)

  useEffect(() => { localStorage.setItem("propmanage_lang", lang); }, [lang]);

  useEffect(() => {
    // Fetch CMS public overrides once at mount. Silent fail keeps i18n working offline.
    axios.get(`${API}/cms/public`)
      .then(r => setCms(r.data || {}))
      .catch(() => setCms({}));
  }, []);

  // CMS overrides take priority. Storage convention:
  //   `key` → RO override
  //   `key:en` → EN override (optional)
  // Both fall back to bundled translations[lang] when missing.
  const t = (key) => {
    if (lang === "en") {
      const enOverride = cms[`${key}:en`];
      if (enOverride !== undefined && enOverride !== "") return enOverride;
      return translations.en[key] || translations.ro[key] || key;
    }
    // RO
    if (cms[key] !== undefined && cms[key] !== "") return cms[key];
    return translations.ro[key] || key;
  };
  // Helper for landing visibility flags (defaults to true if missing — fail-open for new sections)
  // Honor ?preview=1&landing_show_X=true/false URL params (admin preview mode)
  const showSection = (key, fallback = true) => {
    if (typeof window !== "undefined") {
      const sp = new URLSearchParams(window.location.search);
      if (sp.get("preview") === "1" && sp.has(key)) {
        return sp.get(key) === "true";
      }
    }
    const v = cms[`_settings.${key}`];
    return v === undefined ? fallback : v === true || v === "true";
  };
  const isPreview = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("preview") === "1";
  const toggle = () => setLang(l => l === "ro" ? "en" : "ro");

  return (
    <I18nContext.Provider value={{ lang, setLang, toggle, t, cms, showSection, isPreview }}>
      {children}
    </I18nContext.Provider>
  );
};

export const useI18n = () => {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be inside I18nProvider");
  return ctx;
};
