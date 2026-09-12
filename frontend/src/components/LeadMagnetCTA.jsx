// Lead Magnet CTA — bloc reutilizabil pe toate ghidurile (Growth OS G1)
import React from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, ClipboardCheck, ArrowRight } from "lucide-react";

export const LeadMagnetCTA = () => (
  <section className="mt-12 pt-10 border-t border-white/5" data-testid="lead-magnet-cta">
    <h2 className="font-serif text-2xl text-white mb-2">Instrumente gratuite</h2>
    <p className="text-sm text-stone-400 mb-5">Folosite de proprietari și cumpărători înainte de orice decizie.</p>
    <div className="grid sm:grid-cols-2 gap-4">
      <Link to="/scorul-casei" className="glass-strong rounded-2xl p-5 hover:bg-white/[0.06] transition group" data-testid="cta-health-score">
        <ShieldCheck className="w-6 h-6 text-[#d4ff3a] mb-3" />
        <div className="font-serif text-lg leading-tight mb-1 group-hover:text-[#d4ff3a] transition">Scorul Casei Tale</div>
        <p className="text-xs text-stone-400 mb-3">Află în 2 minute starea tehnică a locuinței tale (0-100) + riscurile principale.</p>
        <span className="text-xs font-semibold text-[#d4ff3a] inline-flex items-center gap-1">Calculează gratuit <ArrowRight className="w-3 h-3" /></span>
      </Link>
      <Link to="/checklist-cumparare" className="glass-strong rounded-2xl p-5 hover:bg-white/[0.06] transition group" data-testid="cta-buying-checklist">
        <ClipboardCheck className="w-6 h-6 text-[#d4ff3a] mb-3" />
        <div className="font-serif text-lg leading-tight mb-1 group-hover:text-[#d4ff3a] transition">Checklist cumpărare apartament</div>
        <p className="text-xs text-stone-400 mb-3">Cele 25 de verificări obligatorii înainte să semnezi. Interactiv + PDF pe email.</p>
        <span className="text-xs font-semibold text-[#d4ff3a] inline-flex items-center gap-1">Deschide checklist-ul <ArrowRight className="w-3 h-3" /></span>
      </Link>
    </div>
  </section>
);

export default LeadMagnetCTA;
