// Role-specific Driver.js inline tour — spotlights real DOM elements with
// popovers anchored to selectors. Triggers AFTER the modal TutorialOverlay
// is dismissed (so user sees the full intro first), and only ONCE per user.
import { useEffect, useRef } from "react";
import axios from "axios";
import { driver } from "driver.js";
import "driver.js/dist/driver.css";
import { useAuth } from "../auth";
import { API } from "./DashShared";

// Selectors use [data-tour="..."] attributes injected into key dashboard
// elements. If a selector is missing in the DOM (e.g. role doesn't have it),
// driver.js automatically skips that step.
const ROLE_STEPS = {
  client: [
    {
      element: '[data-tour="client-property-card"]',
      popover: {
        title: "Proprietatea ta",
        description: "Aici e cardul proprietății tale. Click pentru detalii, Digital Twin și istoric lucrări.",
      },
    },
    {
      element: '[data-tour="client-new-request"]',
      popover: {
        title: "Cere o ofertă în 30 secunde",
        description: "Postezi o cerere de lucrare → 3-5 specialiști verificați îți trimit oferte în câteva ore.",
      },
    },
    {
      element: '[data-tour="client-marketplace"]',
      popover: {
        title: "Marketplace · Caută specialiști",
        description: "Filtrezi după zonă, categorie, rating, badge VERIFIED. Toți au Health Score calculat de noi.",
      },
    },
    {
      element: '[data-tour="client-escrow-info"]',
      popover: {
        title: "Plăți escrow protejate",
        description: "Banii stau blocați la PropManage până confirmi finalizarea. Lucrare slabă → dispută → rambursare.",
      },
    },
    {
      element: '[data-tour="notifications-bell"]',
      popover: {
        title: "Notificările tale",
        description: "Aici vezi oferte primite, status lucrări, plăți eliberate. Activează push notifications din Setări.",
      },
    },
  ],
  specialist: [
    {
      element: '[data-tour="specialist-leads"]',
      popover: {
        title: "Lead-uri noi",
        description: "Cereri de lucrări care îți corespund (zonă + categorii). Acceptă cele care îți convin — taxă 45 RON/lead.",
      },
    },
    {
      element: '[data-tour="specialist-trust-score"]',
      popover: {
        title: "Trust Score · reputația ta",
        description: "Scor 0-100 calculat din punctualitate, recenzii, fotografii lucrări, lipsa reclamațiilor.",
      },
    },
    {
      element: '[data-tour="specialist-wallet"]',
      popover: {
        title: "Portofelul tău",
        description: "Aici vezi câștigurile din lucrări. 95% din valoare ajunge la tine după confirmarea clientului (5% comision platformă).",
      },
    },
    {
      element: '[data-tour="specialist-kyc"]',
      popover: {
        title: "Documente KYC",
        description: "Încarcă buletin + asigurare + certificări. După aprobarea operatorului, primești badge VERIFIED și apari sus în marketplace.",
      },
    },
    {
      element: '[data-tour="notifications-bell"]',
      popover: {
        title: "Notificările tale",
        description: "Toate update-urile importante: lead-uri noi, confirmări, recenzii, dispute. Nu pierde nimic.",
      },
    },
  ],
  operator: [
    {
      element: '[data-tour="operator-kyc-queue"]',
      popover: {
        title: "Coada KYC",
        description: "Documente specialiști care așteaptă validare. SLA: 24 ore. Aprobă/respinge cu motiv.",
      },
    },
    {
      element: '[data-tour="operator-twin-queue"]',
      popover: {
        title: "Twin Validation",
        description: "Modele 3D ale proprietăților clienților. Verifici că sunt corecte înainte să intre în producție.",
      },
    },
    {
      element: '[data-tour="operator-disputes"]',
      popover: {
        title: "Dispute mici (< 1000 RON)",
        description: "Decizi singur: refund client / pay specialist / split. Cele > 1000 RON merg la admin.",
      },
    },
    {
      element: '[data-tour="notifications-bell"]',
      popover: {
        title: "Notificările tale",
        description: "Te alertăm imediat ce o nouă cerere KYC, Twin sau dispută intră în coada ta.",
      },
    },
  ],
  admin: [
    {
      element: '[data-tour="admin-ai-health"]',
      popover: {
        title: "AI Health Score",
        description: "Scor general de sănătate al platformei (0-100) calculat de AI pe baza KPIs live.",
      },
    },
    {
      element: '[data-tour="admin-qa-playbook"]',
      popover: {
        title: "QA Playbook & Release Gate",
        description: "105 scenarii manuale + 38 teste automate. Rulează gate-ul ÎNAINTE de orice deploy.",
      },
    },
    {
      element: '[data-tour="admin-analytics"]',
      popover: {
        title: "Analytics live",
        description: "GMV, revenue, top specialists, dispute rate. Toate metricile cheie într-un singur loc.",
      },
    },
    {
      element: '[data-tour="admin-content-tools"]',
      popover: {
        title: "Content Tools",
        description: "Content Audit + Terminology Audit + AI rewrites. Documentația ta rămâne coerentă single-click.",
      },
    },
    {
      element: '[data-tour="notifications-bell"]',
      popover: {
        title: "Notificările tale",
        description: "Alerte critice: P0 fail, dispute escaladate, backups eșuate. Nu rata nimic important.",
      },
    },
  ],
};

const PER_ROLE_INTRO = {
  client: { title: "Tur ghidat · Client", description: "Hai să-ți arăt cele mai importante 5 zone din panou. Durează ~45 sec." },
  specialist: { title: "Tur ghidat · Specialist", description: "Te ghidez prin lead-uri, wallet, KYC și Trust Score. Durează ~45 sec." },
  operator: { title: "Tur ghidat · Operator", description: "Îți arăt cozile de validare și sistem de dispute. Durează ~30 sec." },
  admin: { title: "Tur ghidat · Admin", description: "Îți arăt AI Health, QA Playbook, Analytics și Content Tools. Durează ~45 sec." },
};

// Attach data-testid attributes to driver.js popover elements via MutationObserver.
// Driver.js renders popovers dynamically, so we observe additions to <body>.
const DRIVER_TESTID_MAP = {
  "driver-popover": "tour-popover",
  "driver-popover-title": "tour-title",
  "driver-popover-description": "tour-description",
  "driver-popover-next-btn": "tour-next",
  "driver-popover-prev-btn": "tour-prev",
  "driver-popover-close-btn": "tour-skip",
  "driver-popover-done-btn": "tour-done",
  "driver-popover-progress-text": "tour-progress",
};

let driverObserver = null;

const stampTestIds = (root) => {
  if (!root || !root.querySelectorAll) return;
  Object.entries(DRIVER_TESTID_MAP).forEach(([cls, tid]) => {
    const nodes = root.classList && root.classList.contains(cls) ? [root] : root.querySelectorAll(`.${cls}`);
    nodes.forEach((n) => {
      if (n && !n.getAttribute("data-testid")) {
        n.setAttribute("data-testid", tid);
      }
    });
  });
};

const attachDriverTestIds = () => {
  // Stamp anything already rendered
  stampTestIds(document.body);
  // Detach previous observer if any
  if (driverObserver) driverObserver.disconnect();
  driverObserver = new MutationObserver((mutations) => {
    mutations.forEach((m) => {
      m.addedNodes.forEach((node) => {
        if (node.nodeType === 1) stampTestIds(node);
      });
    });
  });
  driverObserver.observe(document.body, { childList: true, subtree: true });
};

export const RoleTour = ({ forceStart = false }) => {
  const { user, refreshUser } = useAuth();
  const startedRef = useRef(false);

  useEffect(() => {
    if (!user || user === false) return;

    const role = user.active_view || user.role;
    const steps = ROLE_STEPS[role] || [];
    if (steps.length === 0) return;

    const intro = PER_ROLE_INTRO[role] || PER_ROLE_INTRO.client;

    let cancelled = false;
    let timer = null;
    let attempts = 0;
    const MAX_ATTEMPTS = 20; // ~10s of polling (20 × 500ms)

    const tryLaunch = () => {
      if (cancelled) return;
      attempts += 1;
      const visible = steps.filter((s) => {
        try { return !!document.querySelector(s.element); } catch { return false; }
      });

      if (visible.length === 0) {
        if (attempts < MAX_ATTEMPTS) {
          timer = setTimeout(tryLaunch, 500);
        }
        return;
      }

      startedRef.current = true;
      let tour;
      try {
        tour = driver({
          showProgress: true,
          animate: true,
          smoothScroll: true,
          allowClose: true,
          stagePadding: 6,
          stageRadius: 12,
          nextBtnText: "Mai departe →",
          prevBtnText: "← Înapoi",
          doneBtnText: "Am înțeles, gata!",
          progressText: "{{current}} / {{total}}",
          popoverClass: "propmanage-driver-popover",
          steps: [
            { popover: { ...intro, side: "over", align: "center" } },
            ...visible.map((s) => ({ element: s.element, popover: { ...s.popover, side: "bottom", align: "start" } })),
          ],
          onDestroyStarted: async () => {
            try {
              await axios.post(`${API}/auth/dashboard-tour-done`);
              if (refreshUser) await refreshUser();
            } catch {
              /* best-effort */
            }
            if (driverObserver) { driverObserver.disconnect(); driverObserver = null; }
            if (tour) tour.destroy();
          },
        });
        tour.drive();
        // Inject data-testid attributes on driver.js elements for QA automation
        attachDriverTestIds();
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error("[RoleTour] driver failed:", e);
        startedRef.current = false;
      }
    };

    // PPOS P3a-M1: never auto-start — launch only on explicit user request
    const onStart = () => {
      if (startedRef.current) return;
      attempts = 0;
      timer = setTimeout(tryLaunch, 300);
    };
    window.addEventListener("pm-start-roletour", onStart);
    if (forceStart) timer = setTimeout(tryLaunch, 1200);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      window.removeEventListener("pm-start-roletour", onStart);
    };
  }, [user, forceStart, refreshUser]);

  return null;
};

// Lightweight button to manually replay the tour (opens the on-demand guide)
export const ReplayTourButton = () => {
  const { user } = useAuth();
  if (!user || user === false) return null;
  const handleReplay = () => window.dispatchEvent(new Event("pm-open-tour"));
  return (
    <button
      type="button"
      onClick={handleReplay}
      className="text-xs text-stone-500 hover:text-[#d4ff3a] underline-offset-2 hover:underline"
      data-testid="replay-tour-btn"
    >
      Reia turul ghidat
    </button>
  );
};
