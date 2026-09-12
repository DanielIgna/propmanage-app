// NextStep — continuitate vizuală: fiecare pagină publică continuă natural în următoarea.
// Fără fundături (dead ends) în customer journey.
import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

export const NextStep = ({ dark = false, label = "Pasul următor", title, desc, to, cta }) => (
  <div
    className={`rounded-3xl border p-6 sm:p-8 ${dark ? "bg-[#d4ff3a]/5 border-[#d4ff3a]/25" : "bg-emerald-50 border-emerald-200"}`}
    data-testid="next-step-card"
  >
    <div className={`text-[10px] font-black uppercase tracking-widest mb-2 ${dark ? "text-[#d4ff3a]" : "text-emerald-700"}`}>
      → {label}
    </div>
    <h3 className={`text-xl sm:text-2xl font-black ${dark ? "text-white" : "text-stone-900"}`}>{title}</h3>
    {desc && <p className={`mt-2 text-sm max-w-2xl ${dark ? "text-stone-400" : "text-stone-600"}`}>{desc}</p>}
    <Link
      to={to}
      className={`mt-5 inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-bold transition-opacity hover:opacity-90 ${dark ? "bg-[#d4ff3a] text-black" : "bg-emerald-700 text-white"}`}
      data-testid="next-step-cta"
    >
      {cta} <ArrowRight className="w-4 h-4" />
    </Link>
  </div>
);
