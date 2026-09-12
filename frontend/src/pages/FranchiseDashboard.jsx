// Dashboard Franciză (Tenant Val 3) — franchise_admin vede DOAR lead-urile tenantului lui.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { useAuth } from "../auth";
import { Navigate } from "react-router-dom";
import { Building2, Flame, Sun, Sprout, LogOut, RefreshCw } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const SEG_STYLE = {
  hot: "bg-red-100 text-red-700",
  warm: "bg-amber-100 text-amber-700",
  nurture: "bg-sky-100 text-sky-700",
};

export default function FranchiseDashboard() {
  const { user, logout } = useAuth();
  const [data, setData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      axios.get(`${API}/api/admin/leads?limit=100`, { withCredentials: true }),
      axios.get(`${API}/api/admin/leads/summary?days=30`, { withCredentials: true }),
    ]).then(([r1, r2]) => {
      setData(r1.data);
      setSummary(r2.data);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => {
    if (user?.role !== "franchise_admin") return;
    load();
    axios.get(`${API}/api/public/tenant-context`, { withCredentials: true, headers: { "X-Tenant-ID": user.tenant_id || "" } })
      .then((r) => setTenant(r.data.tenant)).catch(() => {});
  }, [user]);

  if (user === undefined || user === null) return null;
  if (user === false) return <Navigate to="/login" replace />;
  if (user.role !== "franchise_admin") return <Navigate to={`/${user.role}`} replace />;

  const leads = data?.leads || [];
  const segCount = (s) => leads.filter((l) => l.segment === s).length;

  return (
    <div className="min-h-screen bg-stone-50 text-stone-800" data-testid="franchise-dashboard">
      <header className="bg-stone-900 text-white">
        <div className="max-w-6xl mx-auto px-5 sm:px-8 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Building2 className="w-5 h-5 text-emerald-400" />
            <div>
              <div className="font-black leading-none" data-testid="franchise-tenant-name">{tenant?.name || user.tenant_id}</div>
              <div className="text-[10px] text-stone-400 tracking-wide">Franciză PropManage · {user.email}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={load} className="p-2 rounded-xl hover:bg-white/10" title="Reîncarcă" data-testid="franchise-refresh">
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button onClick={logout} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-white/10 hover:bg-white/20" data-testid="franchise-logout">
              <LogOut className="w-3.5 h-3.5" /> Ieșire
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-5 sm:px-8 py-8 space-y-8">
        <div className="grid sm:grid-cols-4 gap-4">
          <div className="p-5 rounded-3xl bg-white border border-stone-100" data-testid="franchise-stat-total">
            <div className="text-xs font-bold text-stone-400 uppercase tracking-wide">Lead-uri (afișate)</div>
            <div className="text-3xl font-black text-stone-900 mt-1">{leads.length}</div>
            <div className="text-[11px] text-stone-400 mt-1">ultimele 30 zile: {summary?.total ?? "—"}</div>
          </div>
          {[["hot", Flame, "Hot"], ["warm", Sun, "Warm"], ["nurture", Sprout, "Nurture"]].map(([seg, Icon, label]) => (
            <div key={seg} className="p-5 rounded-3xl bg-white border border-stone-100" data-testid={`franchise-stat-${seg}`}>
              <div className="text-xs font-bold text-stone-400 uppercase tracking-wide flex items-center gap-1.5"><Icon className="w-3.5 h-3.5" /> {label}</div>
              <div className="text-3xl font-black text-stone-900 mt-1">{segCount(seg)}</div>
            </div>
          ))}
        </div>

        <div className="rounded-3xl bg-white border border-stone-100 overflow-hidden">
          <div className="px-5 py-4 border-b border-stone-100 flex items-center justify-between">
            <h2 className="font-black text-stone-900">Lead-urile francizei tale</h2>
            <span className="text-xs text-stone-400">tenant: {data?.tenant || user.tenant_id}</span>
          </div>
          {leads.length === 0 ? (
            <div className="p-10 text-center text-sm text-stone-400" data-testid="franchise-leads-empty">
              Niciun lead încă pentru această franciză. Lead-urile create cu tenantul tău apar automat aici.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-stone-400 uppercase tracking-wide border-b border-stone-100">
                    <th className="px-5 py-3">Nume</th><th className="px-5 py-3">Contact</th>
                    <th className="px-5 py-3">Sursă</th><th className="px-5 py-3">Segment</th>
                    <th className="px-5 py-3">Scor</th><th className="px-5 py-3">Data</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.map((l, i) => (
                    <tr key={i} className="border-b border-stone-50 hover:bg-stone-50" data-testid={`franchise-lead-${i}`}>
                      <td className="px-5 py-3 font-bold text-stone-800">{l.name || "—"}</td>
                      <td className="px-5 py-3 text-stone-500">{l.email}{l.phone ? ` · ${l.phone}` : ""}</td>
                      <td className="px-5 py-3 text-stone-500">{l.source}</td>
                      <td className="px-5 py-3"><span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${SEG_STYLE[l.segment] || "bg-stone-100 text-stone-500"}`}>{l.segment}</span></td>
                      <td className="px-5 py-3 font-bold text-stone-700">{l.score ?? "—"}</td>
                      <td className="px-5 py-3 text-stone-400 text-xs">{(l.created_at || "").slice(0, 10)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
