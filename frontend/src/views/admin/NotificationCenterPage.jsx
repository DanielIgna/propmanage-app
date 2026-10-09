// NotificationCenterPage — «Ai N lucruri importante» prioritizat de AI, cu ack + link direct.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { BellRing, CheckCircle2, ExternalLink, RefreshCw, Brain, Activity } from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { DSButton, EmptyState, DSSkeleton } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const SEV = {
  high:   { badge: "bg-rose-500 text-white", label: "URGENT" },
  medium: { badge: "bg-amber-400 text-slate-900", label: "ATENȚIE" },
  low:    { badge: "bg-slate-400 text-white", label: "INFO" },
};
const SOURCE = {
  operational: { icon: BellRing, label: "Operațional" },
  health: { icon: Activity, label: "Business Health" },
  ai_recommendation: { icon: Brain, label: "Recomandare AI" },
};

export default function NotificationCenterPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const r = await ax.get("/admin/notification-center");
      setData(r.data);
    } catch (e) { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const ack = async (key) => {
    try { await ax.post("/admin/notification-center/ack", { key }); load(); } catch (e) { /* silent */ }
  };

  return (
    <AdminLayoutMetronic
      title="Notification Center AI"
      subtitle="Toate lucrurile importante într-un singur loc — prioritizate, cu acțiune directă"
    >
      {loading ? <DSSkeleton kpis={0} blocks={2} /> : (
        <div className="space-y-6" data-testid="notification-center-root">
          <div className="p-5 rounded-2xl border border-lime-300 dark:border-lime-500/40 bg-lime-50 dark:bg-lime-500/10 flex items-center justify-between" data-testid="nc-headline">
            <div className="flex items-center gap-3">
              <BellRing className="w-6 h-6 text-lime-600 dark:text-lime-300" />
              <div>
                <div className="text-xl font-black text-slate-900 dark:text-white">{data?.headline}</div>
                <div className="text-xs text-slate-500">Agregat din Command Center + Business Health + recomandări AI nerezolvate. Bifate = ascunse până mâine.</div>
              </div>
            </div>
            <DSButton variant="ghost" icon={RefreshCw} onClick={load} data-testid="nc-refresh">Refresh</DSButton>
          </div>

          <AdminCard title={`Item-e importante (${data?.items?.length || 0})`} testid="nc-items">
            {!(data?.items || []).length && <EmptyState icon={CheckCircle2} title="Nimic important" hint="Platforma e sub control." />}
            <div className="space-y-2">
              {(data?.items || []).map((it) => {
                const sv = SEV[it.severity] || SEV.low;
                const src = SOURCE[it.source] || SOURCE.operational;
                return (
                  <div key={it.key} className={`flex items-center gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 ${it.acked ? "opacity-40" : ""}`} data-testid={`nc-item-${it.key}`}>
                    <button
                      onClick={() => !it.acked && ack(it.key)}
                      disabled={it.acked}
                      className={`w-6 h-6 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${it.acked ? "bg-emerald-500 border-emerald-500 text-white" : "border-slate-300 dark:border-slate-600 hover:border-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-500/10"}`}
                      title={it.acked ? "Rezolvat azi" : "Marchează văzut"}
                      data-testid={`nc-ack-${it.key}`}
                    >
                      {it.acked && "✓"}
                    </button>
                    <span className={`text-[9px] font-black uppercase px-1.5 py-0.5 rounded shrink-0 ${sv.badge}`}>{sv.label}</span>
                    <div className="flex-1 min-w-0">
                      <div className={`text-sm font-semibold text-slate-800 dark:text-slate-100 ${it.acked ? "line-through" : ""}`}>{it.label}</div>
                      <div className="text-[10px] text-slate-400 flex items-center gap-1"><src.icon className="w-3 h-3" /> {src.label}</div>
                    </div>
                    {it.link && (
                      <a href={it.link} className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1.5 rounded-full text-[10px] font-black bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:opacity-80" data-testid={`nc-open-${it.key}`}>
                        Rezolvă <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                );
              })}
            </div>
          </AdminCard>
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
