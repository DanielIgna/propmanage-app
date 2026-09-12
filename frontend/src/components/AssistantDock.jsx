// Assistant Dock — un SINGUR FAB care unește AI Concierge + WhatsApp.
// Rezolvă coliziunile din colțul dreapta-jos (cookie/WhatsApp/AI/bottom-nav).
import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import axios from "axios";
import { MessageCircle, Bot, X } from "lucide-react";
import { useAuth } from "../auth";

const API = process.env.REACT_APP_BACKEND_URL;

const WaIcon = () => (
  <svg viewBox="0 0 32 32" className="w-4.5 h-4.5 fill-white" style={{ width: 18, height: 18 }} aria-hidden="true">
    <path d="M16 3C9.4 3 4 8.3 4 14.9c0 2.6.8 5 2.3 7L4.7 27.6a1 1 0 0 0 1.2 1.3l5.9-1.5a12 12 0 0 0 4.2.7c6.6 0 12-5.3 12-11.9S22.6 3 16 3zm0 21.8c-1.4 0-2.7-.3-3.9-.8l-.7-.3-3.5.9.9-3.3-.4-.7a9.7 9.7 0 0 1-1.6-5.7c0-5.4 4.4-9.8 9.9-9.8s9.9 4.4 9.9 9.8-4.4 9.9-9.9 9.9h-.7zm5.4-7.3c-.3-.2-1.8-.9-2-1s-.5-.2-.7.2c-.2.3-.8 1-.9 1.2s-.3.2-.6.1a7.9 7.9 0 0 1-2.3-1.4 8.7 8.7 0 0 1-1.6-2c-.2-.3 0-.5.1-.6l.5-.5c.1-.2.2-.3.3-.5s0-.4 0-.5c-.1-.2-.7-1.7-1-2.3-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.2.2 2.1 3.2 5.1 4.5.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.8-.7 2-1.4.3-.7.3-1.3.2-1.4-.1-.2-.3-.2-.6-.4z" />
  </svg>
);

export const AssistantDock = () => {
  const { pathname } = useLocation();
  const { user } = useAuth();
  const [cfg, setCfg] = useState(null);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [open, setOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/track/config`).then(r => r.json()).then(setCfg).catch(() => {});
  }, []);

  const loggedIn = !!user && user !== false;
  const aiCandidate = loggedIn && user.role !== "admin";

  useEffect(() => {
    if (!aiCandidate) { setAiEnabled(false); return; }
    axios.get(`${API}/api/concierge/settings/public`)
      .then(r => setAiEnabled(!!r.data?.enabled && !r.data?.is_blocked))
      .catch(() => setAiEnabled(false));
  }, [aiCandidate, user?.id]);

  useEffect(() => {
    const h = (e) => setPanelOpen(!!e.detail?.open);
    window.addEventListener("pm-ai-state", h);
    return () => window.removeEventListener("pm-ai-state", h);
  }, []);

  if (pathname.startsWith("/admin")) return null;
  const hasWa = !!(cfg && cfg.whatsapp_enabled !== false && cfg.whatsapp_phone);
  if ((!hasWa && !aiEnabled) || panelOpen) return null;

  const waHref = hasWa
    ? `https://wa.me/${cfg.whatsapp_phone.replace(/[^0-9]/g, "")}?text=${encodeURIComponent(cfg.whatsapp_message || "")}`
    : null;
  const openAI = () => { setOpen(false); window.dispatchEvent(new CustomEvent("pm-open-ai")); };
  const single = !(hasWa && aiEnabled);
  const hasBottomNav = loggedIn || pathname.startsWith("/incepe") || pathname.startsWith("/dashboard/client-junior");
  const pos = hasBottomNav ? "bottom-24 lg:bottom-8" : "bottom-6";

  return (
    <div className={`fixed ${pos} right-4 lg:right-6 z-[55] flex flex-col items-end gap-2`} data-testid="assistant-dock">
      {open && (
        <div className="w-60 rounded-2xl border border-white/10 bg-[#0f0f0f]/95 backdrop-blur-xl shadow-2xl overflow-hidden" data-testid="assistant-dock-menu">
          {aiEnabled && (
            <button onClick={openAI} data-testid="assistant-dock-ai"
              className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-white/5 transition-colors">
              <span className="w-9 h-9 rounded-full bg-[#ccff00] flex items-center justify-center shrink-0">
                <Bot className="w-4.5 h-4.5 text-black" style={{ width: 18, height: 18 }} />
              </span>
              <span>
                <span className="block text-sm font-semibold" style={{ color: "#fafafa" }}>Asistent AI</span>
                <span className="block text-[10px] text-stone-400">răspuns instant, 24/7</span>
              </span>
            </button>
          )}
          {hasWa && (
            <a href={waHref} target="_blank" rel="noreferrer" data-testid="assistant-dock-whatsapp"
              onClick={() => { import("../lib/analytics").then(({ trackIntent }) => trackIntent("whatsapp_opened")).catch(() => {}); }}
              className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-white/5 transition-colors border-t border-white/5">
              <span className="w-9 h-9 rounded-full flex items-center justify-center shrink-0" style={{ background: "#25D366" }}>
                <WaIcon />
              </span>
              <span>
                <span className="block text-sm font-semibold" style={{ color: "#fafafa" }}>WhatsApp</span>
                <span className="block text-[10px] text-stone-400">scrie-ne direct</span>
              </span>
            </a>
          )}
        </div>
      )}
      <button
        onClick={() => { if (single) { if (aiEnabled) openAI(); else window.open(waHref, "_blank"); } else setOpen(o => !o); }}
        data-testid="assistant-dock-fab" aria-label="Asistență" title="Asistență"
        className="w-14 h-14 rounded-full bg-[#ccff00] shadow-[0_12px_40px_-10px_rgba(204,255,0,0.55)] flex items-center justify-center hover:scale-105 active:scale-95 transition-transform">
        {open ? <X className="w-6 h-6 text-black" /> : <MessageCircle className="w-6 h-6 text-black" strokeWidth={2.2} />}
      </button>
    </div>
  );
};

export default AssistantDock;
