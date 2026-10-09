// Guided tour overlay (5 steps) — ON DEMAND only (PPOS P3a-M1), opened via "?" HelpButton.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { X, ChevronRight, ChevronLeft, Sparkles } from "lucide-react";
import { useAuth } from "../auth";
import { API } from "./DashShared";

const STEPS = {
  client: [
    {
      icon: "🏡",
      title: "Bun venit pe PropManage!",
      body: "Acesta este panoul tău de client. De aici poți gestiona proprietatea, accesa Digital Twin-ul, cere oferte și plăti specialiști în siguranță.",
    },
    {
      icon: "🔮",
      title: "Digital Twin — inima platformei",
      body: "Twin-ul e replica 3D a casei tale. Vezi sistemele (electric, sanitar, HVAC), istoricul intervențiilor și starea generală. Click pe cardul Twin pentru detalii complete.",
    },
    {
      icon: "🛒",
      title: "Marketplace + Cere ofertă",
      body: "Apasă „Cere o ofertă\" sau intră pe Marketplace ca să găsești specialiști verificați. Filtrele te ajută să găsești cei mai aproape de tine.",
    },
    {
      icon: "💰",
      title: "Plăți securizate via Escrow",
      body: "Banii tăi stau în escrow până confirmi lucrarea. Pentru proiecte mari de design, plătești în 4 tranșe (25% fiecare), cu garanție 30 zile pe final.",
    },
    {
      icon: "🔔",
      title: "Notificări & Activitate",
      body: "Clopoțelul din header îți arată tot ce se întâmplă: oferte primite, status lucrări, plăți eliberate. Activează push notifications din Setări pentru alerte instant.",
    },
  ],
  specialist: [
    {
      icon: "🛠️",
      title: "Bun venit, specialist!",
      body: "De aici accesezi oportunitățile noi, gestionezi lucrările în desfășurare și îți urmărești Trust Score-ul.",
    },
    {
      icon: "📍",
      title: "Setează zona ta de acoperire",
      body: "Mergi în Setări → Aria de acoperire ca să primești doar lead-urile relevante (orașe + cartiere). Cu cât setezi mai precis, cu atât oferiți mai bine.",
    },
    {
      icon: "⭐",
      title: "Trust Score — reputația ta",
      body: "Scor de la 0 la 100 calculat din punctualitate, recenzii, fotografii cu lucrarea și lipsa reclamațiilor. Vezi-l live în profil.",
    },
    {
      icon: "📋",
      title: "Acceptă lead-uri (40-50 RON/lead)",
      body: "Click pe „Oportunități noi\". Plătești taxa de lead doar dacă accepți. Clienții îți văd profilul, rating-ul și certificările.",
    },
    {
      icon: "💼",
      title: "Project Workspace (pentru designeri)",
      body: "Dacă oferi design interior, poți crea proiecte cu Kanban + multi-specialist coordination + plăți pe milestones. Idel pentru proiecte mari.",
    },
  ],
  operator: [
    { icon: "🔍", title: "Operator validare", body: "Validezi Digital Twin-uri și verifici lucrările finalizate. Coada ta de așteptare se actualizează live." },
    { icon: "📐", title: "2D Floorplan editor", body: "Folosește editorul de plan să confirmi camerele și echipamentele înainte de aprobarea Twin-ului." },
  ],
  admin: [
    { icon: "👑", title: "Bun venit, Admin!", body: "Panoul Metronic îți dă control total asupra platformei." },
    { icon: "📝", title: "CMS Live", body: "Editezi texte din landing direct din admin → CONȚINUT → Texte (CMS). Modificările apar instant." },
    { icon: "🧪", title: "A/B Testing", body: "Testează variante de CTA în CONFIGURARE → A/B Tests. Câștigătorul se marchează automat la ≥30 impressions." },
  ],
};

export const TutorialOverlay = () => {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  // PPOS P3a-M1: the tour NEVER auto-opens. It opens only on explicit request
  // (the "?" HelpButton dispatches "pm-open-tour").
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onOpen = () => { setStep(0); setOpen(true); };
    window.addEventListener("pm-open-tour", onOpen);
    return () => window.removeEventListener("pm-open-tour", onOpen);
  }, []);

  const role = user?.active_view || user?.role;
  const steps = STEPS[role] || STEPS.client;

  if (!user || user === false) return null;
  if (!open) return null;

  const finish = async () => {
    setOpen(false);
    try {
      if (user.tutorial_seen !== true) {
        await axios.post(`${API}/auth/tutorial-seen`);
        if (refreshUser) await refreshUser();
      }
    } catch {}
    // Chain into the in-context driver.js tour (also user-initiated now)
    window.dispatchEvent(new Event("pm-start-roletour"));
  };

  const cur = steps[step];
  const isLast = step === steps.length - 1;

  return (
    <div className="fixed inset-0 z-[70] bg-black/80 backdrop-blur-md flex items-center justify-center p-4" data-testid="tutorial-overlay">
      <div className="relative bg-gradient-to-br from-stone-900 to-stone-950 border border-[#d4ff3a]/20 rounded-3xl max-w-lg w-full p-8 shadow-2xl">
        <button onClick={finish} className="absolute top-4 right-4 p-2 hover:bg-white/5 rounded-full" data-testid="tutorial-close">
          <X className="w-4 h-4 text-stone-400" />
        </button>

        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="w-4 h-4 text-[#d4ff3a]" />
          <span className="text-[10px] uppercase tracking-wider text-[#d4ff3a]">Tur ghidat · Pasul {step + 1} / {steps.length}</span>
        </div>

        <div className="text-6xl mb-4" aria-hidden="true">{cur.icon}</div>
        <h2 className="font-serif text-3xl mb-3" data-testid="tutorial-title">{cur.title}</h2>
        <p className="text-stone-300 leading-relaxed mb-8">{cur.body}</p>

        {/* Progress dots */}
        <div className="flex gap-1.5 mb-6">
          {steps.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-colors ${i <= step ? "bg-[#d4ff3a]" : "bg-white/10"}`}
              data-testid={`tutorial-dot-${i}`}
            />
          ))}
        </div>

        <div className="flex justify-between gap-2">
          <button
            onClick={() => setStep(Math.max(0, step - 1))}
            disabled={step === 0}
            className="px-4 py-2.5 rounded-full bg-white/5 hover:bg-white/10 text-sm disabled:opacity-30 flex items-center gap-1"
            data-testid="tutorial-prev"
          >
            <ChevronLeft className="w-3.5 h-3.5" /> Înapoi
          </button>
          {!isLast ? (
            <button
              onClick={() => setStep(step + 1)}
              className="btn-accent px-5 py-2.5 rounded-full text-sm font-medium flex items-center gap-1"
              data-testid="tutorial-next"
            >
              Mai departe <ChevronRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={finish}
              className="btn-accent px-5 py-2.5 rounded-full text-sm font-medium"
              data-testid="tutorial-finish"
            >
              Am înțeles, începem!
            </button>
          )}
        </div>

        <button onClick={finish} className="mt-4 text-xs text-stone-500 hover:text-stone-300 text-center w-full" data-testid="tutorial-skip">
          Sari peste · Mai târziu
        </button>
      </div>
    </div>
  );
};
