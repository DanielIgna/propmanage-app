// Enterprise Explorer (/admin/explorer) — „Google Maps" al Enterprise OS (Founder-only).
// EXECUTION ORDER 002 · Module 3: graf interactiv cu filtre pe tip + căutare instant.
import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Network, Search, ShieldAlert, X } from "lucide-react";
import { RegistryGraph, TYPE_META, TYPE_ORDER } from "../../components/founder/RegistryGraph";
import { useFounderAccess } from "../../components/founder/useFounderAccess";

export default function EnterpriseExplorer() {
  const isFounder = useFounderAccess();
  const navigate = useNavigate();
  const [filters, setFilters] = useState(new Set());
  const [search, setSearch] = useState("");

  const toggle = (t) => {
    const next = new Set(filters);
    next.has(t) ? next.delete(t) : next.add(t);
    setFilters(next);
  };

  if (isFounder === false) return (
    <div className="min-h-screen bg-[#0a0a0b] flex flex-col items-center justify-center text-stone-400 gap-3" data-testid="explorer-denied">
      <ShieldAlert className="w-8 h-8 text-amber-400" />
      <div className="text-sm">Enterprise Explorer este disponibil exclusiv Fondatorului.</div>
      <Link to="/admin" className="text-[#d4ff3a] text-xs underline">← Înapoi la Admin</Link>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white mb-3 inline-block">← Înapoi la Admin</Link>
        <h1 className="font-serif text-4xl tracking-tight flex items-center gap-3 mb-1" data-testid="explorer-title">
          <Network className="w-8 h-8 text-[#d4ff3a]" /> Enterprise Explorer
          <span className="text-[10px] px-2 py-1 rounded-full bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 text-[#d4ff3a] font-sans tracking-normal">FOUNDER ONLY</span>
        </h1>
        <p className="text-sm text-stone-400 mb-6">Harta completă a Enterprise OS. Fiecare relație are evidență din cod real — zero legături inventate (Truth Engine D161).</p>

        <div className="flex flex-wrap items-center gap-2 mb-4">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-stone-500" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Căutare instant (nod + vecinii lui)..."
              className="bg-white/5 border border-white/10 rounded-xl pl-9 pr-8 py-2 text-xs outline-none focus:border-[#d4ff3a]/50 w-72" data-testid="explorer-search" />
            {search && <button onClick={() => setSearch("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-stone-500 hover:text-white" data-testid="explorer-search-clear"><X className="w-3.5 h-3.5" /></button>}
          </div>
          {TYPE_ORDER.map(t => (
            <button key={t} onClick={() => toggle(t)}
              className={`text-[10px] px-2.5 py-1.5 rounded-full border transition-colors ${filters.has(t) ? "border-[#d4ff3a]/60 bg-[#d4ff3a]/10 text-white" : "border-white/10 text-stone-400 hover:text-white"}`}
              style={filters.has(t) ? {} : { color: TYPE_META[t].color }}
              data-testid={`explorer-filter-${t}`}>
              {TYPE_META[t].label}
            </button>
          ))}
          {filters.size > 0 && <button onClick={() => setFilters(new Set())} className="text-[10px] text-stone-500 underline" data-testid="explorer-filters-reset">resetează filtrele</button>}
        </div>

        <RegistryGraph typeFilter={filters.size ? filters : null} search={search}
          onOpenDoc={(ref) => navigate(`/admin/knowledge-center?doc=${encodeURIComponent(ref)}`)} />
      </div>
    </div>
  );
}
