// UserTimelinePage — cronologia completă a unui utilizator (cont → cerere → escrow → review).
import React, { useState } from "react";
import axios from "axios";
import { Clock, Search, User, ShieldCheck, Zap, Inbox, Handshake, Lock, CheckCircle2, CreditCard, Star, Activity } from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { EmptyState, DSSkeleton } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const KIND = {
  account: { icon: User, cls: "bg-cyan-500" },
  verify: { icon: ShieldCheck, cls: "bg-emerald-500" },
  badge: { icon: Zap, cls: "bg-lime-400" },
  activity: { icon: Activity, cls: "bg-slate-400" },
  request: { icon: Inbox, cls: "bg-cyan-500" },
  match: { icon: Handshake, cls: "bg-lime-400" },
  escrow: { icon: Lock, cls: "bg-amber-400" },
  complete: { icon: CheckCircle2, cls: "bg-emerald-500" },
  payment: { icon: CreditCard, cls: "bg-emerald-500" },
  review: { icon: Star, cls: "bg-amber-400" },
};

export default function UserTimelinePage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(false);

  const search = async (val) => {
    setQ(val);
    if (val.length < 2) { setResults([]); return; }
    try {
      const r = await ax.get(`/admin/user-timeline/search?q=${encodeURIComponent(val)}`);
      setResults(r.data.users || []);
    } catch (e) { /* silent */ }
  };

  const openTimeline = async (userId) => {
    setLoading(true);
    setResults([]);
    try {
      const r = await ax.get(`/admin/user-timeline/${userId}`);
      setTimeline(r.data);
    } catch (e) { /* silent */ }
    setLoading(false);
  };

  return (
    <AdminLayoutMetronic
      title="User Timeline"
      subtitle="Cronologia completă a oricărui utilizator — cont → verificare → cereri → escrow → plăți → review-uri"
    >
      <div className="space-y-6" data-testid="user-timeline-root">
        <AdminCard title={<span className="flex items-center gap-2"><Search className="w-4 h-4 text-lime-500" /> Caută utilizator</span>} testid="ut-search-card">
          <div className="relative">
            <input
              value={q}
              onChange={(e) => search(e.target.value)}
              placeholder="Email sau nume (min 2 caractere)…"
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white"
              data-testid="ut-search-input"
            />
            {results.length > 0 && (
              <div className="absolute z-20 top-full mt-1 w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-xl overflow-hidden" data-testid="ut-search-results">
                {results.map((u) => (
                  <button key={u.id} onClick={() => openTimeline(u.id)} className="w-full text-left px-4 py-2.5 hover:bg-lime-50 dark:hover:bg-lime-500/10 flex items-center justify-between" data-testid={`ut-result-${u.id}`}>
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">{u.name} <span className="text-slate-400 font-normal">· {u.email}</span></span>
                    <span className="text-[10px] font-bold uppercase text-slate-400">{u.role}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </AdminCard>

        {loading && <DSSkeleton kpis={0} blocks={2} />}
        {!loading && !timeline && <EmptyState icon={Clock} title="Niciun utilizator selectat" hint="Caută după email sau nume și selectează din listă." />}
        {!loading && timeline && (
          <AdminCard
            title={<span className="flex items-center gap-2"><Clock className="w-4 h-4 text-lime-500" /> {timeline.user.name} · {timeline.user.email} · {timeline.total} evenimente</span>}
            testid="ut-timeline"
          >
            <div className="flex items-center gap-2 mb-4 flex-wrap text-[11px]">
              <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 font-bold uppercase">{timeline.user.role}</span>
              {timeline.user.verified && <span className="px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-bold">✓ Verificat</span>}
              {timeline.user.county && <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700">{timeline.user.county}</span>}
            </div>
            <div className="relative ml-3 border-l-2 border-slate-200 dark:border-slate-700 space-y-4 pb-1">
              {timeline.events.map((e, i) => {
                const k = KIND[e.kind] || KIND.activity;
                return (
                  <div key={i} className="relative pl-6" data-testid={`ut-event-${i}`}>
                    <span className={`absolute -left-[11px] top-0.5 w-5 h-5 rounded-full ${k.cls} flex items-center justify-center`}>
                      <k.icon className="w-3 h-3 text-white" />
                    </span>
                    <div className="text-[10px] text-slate-400 font-bold">{new Date(e.ts).toLocaleString("ro-RO")}</div>
                    <div className="text-sm font-semibold text-slate-900 dark:text-white">{e.label}</div>
                    {e.detail && <div className="text-xs text-slate-500">{e.detail}</div>}
                  </div>
                );
              })}
            </div>
          </AdminCard>
        )}
      </div>
    </AdminLayoutMetronic>
  );
}
