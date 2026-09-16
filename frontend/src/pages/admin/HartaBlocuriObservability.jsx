// Admin → HartaBlocuri (Observability) — READ-ONLY v1.
// Suprafață de observare a infrastructurii Buildings/HartaBlocuri deja existente.
// Reutilizează endpoint-urile read-only: /api/admin/hartablocuri/{stats,buildings,buildings/{id}}.
// NU permite editare/ștergere/import/modificarea sursei. Fără mutații de date.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import {
  Building2, MapPin, Search, X, Layers, Home, Calendar, Users, ShieldCheck, Info, Loader2,
} from "lucide-react";
import { API } from "../DashShared";

const SOURCE_BADGE = {
  hartablocuri: { label: "HartaBlocuri", cls: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  both: { label: "PropManage + HartaBlocuri", cls: "bg-lime-400/15 text-lime-300 border-lime-400/30" },
  propmanage: { label: "PropManage", cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
};

const StatCard = ({ label, value, tone = "default", testid }) => {
  const tones = { default: "text-stone-100", hb: "text-amber-400", pm: "text-emerald-400", warn: "text-amber-400" };
  return (
    <div className="rounded-xl border border-stone-800 bg-stone-900/50 p-4" data-testid={testid}>
      <div className={`text-2xl font-bold ${tones[tone]}`}>{value ?? "—"}</div>
      <div className="text-xs mt-1 text-stone-400">{label}</div>
    </div>
  );
};

// ─── Building detail (read-only) ───
const BuildingDetailModal = ({ id, onClose }) => {
  const [b, setB] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    axios.get(`${API}/admin/hartablocuri/buildings/${id}`)
      .then(r => setB(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, [id]);

  const ctx = b?.context || {};
  const hb = b?.hartablocuri;
  const src = b?.source || "propmanage";
  const badge = SOURCE_BADGE[src] || SOURCE_BADGE.hartablocuri;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose} data-testid="hb-obs-detail-modal">
      <div className="bg-stone-950 border border-stone-800 rounded-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-2 p-4 border-b border-stone-800 sticky top-0 bg-stone-950">
          <Building2 className="w-5 h-5 text-amber-400" />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-bold text-stone-100 truncate">{b?.name || "—"}</div>
            <div className="text-[11px] text-stone-500 truncate">{b?.address}</div>
          </div>
          <button onClick={onClose} data-testid="hb-obs-detail-close" className="text-stone-500 hover:text-stone-200"><X className="w-5 h-5" /></button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-stone-500"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
        ) : b ? (
          <div className="p-4 space-y-4">
            <section>
              <h4 className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-2">Identitate</h4>
              <dl className="grid grid-cols-2 gap-2 text-[12px]">
                <Field label="Adresă" value={b.address} />
                <Field label="Localitate" value={b.city} />
                <Field label="Cartier / zonă" value={ctx.neighborhood} />
                <Field label="Identificator (bloc)" value={b.name} />
              </dl>
            </section>
            <section>
              <h4 className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-2">Date disponibile</h4>
              <dl className="grid grid-cols-2 gap-2 text-[12px]">
                <Field label="An construcție" value={ctx.construction_year} />
                <Field label="Etaje / niveluri" value={ctx.floors} />
                <Field label="Număr unități" value={ctx.number_of_units} />
                <Field label="Coordonate" value={ctx.lat && ctx.lng ? `${ctx.lat}, ${ctx.lng}` : null} />
              </dl>
            </section>
            <section>
              <h4 className="text-[10px] font-black uppercase tracking-wider text-stone-500 mb-2">Proveniență</h4>
              <div className="rounded-lg border border-stone-800 bg-stone-900/50 p-3 space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className={`text-[9px] px-2 py-0.5 rounded-full border uppercase ${badge.cls}`}>{badge.label}</span>
                  <span className="text-[11px] text-stone-400">Status: <b className="text-stone-200">{b.verification_status}</b></span>
                </div>
                {hb && (
                  <div className="text-[11px] text-amber-400/80 flex items-center gap-1" data-testid="hb-obs-detail-external">
                    <Info className="w-3 h-3" /> Date externe HartaBlocuri — neverificate de PropManage
                  </div>
                )}
                {hb?.reference_url && (
                  <a href={hb.reference_url} target="_blank" rel="noreferrer nofollow" className="text-[11px] text-amber-400 hover:underline">
                    {hb.reference_url.replace(/^https?:\/\//, "")}
                  </a>
                )}
              </div>
            </section>
            {b.residents_count > 0 && (
              <div className="text-[11px] text-stone-400 flex items-center gap-1.5" data-testid="hb-obs-detail-residents">
                <Users className="w-3.5 h-3.5" /> Asociată cu proprietăți PropManage: <b className="text-stone-200">{b.residents_count}</b>
              </div>
            )}
            <p className="text-[10px] text-stone-600 pt-2 border-t border-stone-800">Vizualizare read-only. Modificarea datelor nu este disponibilă în această etapă.</p>
          </div>
        ) : <div className="p-8 text-center text-stone-500 text-sm">Blocul nu a fost găsit.</div>}
      </div>
    </div>
  );
};
const Field = ({ label, value }) => (
  <div><dt className="text-stone-500 text-[10px]">{label}</dt><dd className="font-bold text-stone-200 break-words">{value ?? "—"}</dd></div>
);

export const HartaBlocuriObservability = () => {
  const [stats, setStats] = useState(null);
  const [q, setQ] = useState("");
  const [source, setSource] = useState("all");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ buildings: [], total: 0, page_size: 25 });
  const [loading, setLoading] = useState(false);
  const [detailId, setDetailId] = useState(null);
  const reqId = React.useRef(0);

  useEffect(() => { axios.get(`${API}/admin/hartablocuri/stats`).then(r => setStats(r.data)).catch(() => {}); }, []);

  const load = useCallback(() => {
    setLoading(true);
    const my = ++reqId.current;
    axios.get(`${API}/admin/hartablocuri/buildings`, { params: { q, source, status, page, page_size: 25 } })
      .then(r => { if (my === reqId.current) setData(r.data); })
      .catch(() => {}).finally(() => { if (my === reqId.current) setLoading(false); });
  }, [q, source, status, page]);
  useEffect(() => { const t = setTimeout(load, 300); return () => clearTimeout(t); }, [load]);
  useEffect(() => { setPage(1); }, [q, source, status]);

  const totalPages = Math.max(1, Math.ceil((data.total || 0) / (data.page_size || 25)));

  return (
    <div className="min-h-screen bg-stone-950 text-stone-100" data-testid="hb-observability-page">
      <div className="max-w-6xl mx-auto p-4 sm:p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
            <Building2 className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-bold">HartaBlocuri · Observability</h1>
            <p className="text-xs text-stone-400">Vizualizare read-only a infrastructurii Buildings · date externe neverificate de PropManage</p>
          </div>
          <span className="text-[10px] px-2 py-1 rounded-full bg-stone-800 text-stone-400 font-bold">READ-ONLY v1</span>
        </div>

        {/* Overview */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
          <StatCard label="Total clădiri" value={stats?.total_buildings} testid="hb-obs-total" />
          <StatCard label="HartaBlocuri" value={stats?.with_hartablocuri} tone="hb" testid="hb-obs-hb" />
          <StatCard label="PropManage" value={stats?.propmanage_only} tone="pm" testid="hb-obs-pm" />
          <StatCard label="Localități" value={stats?.localities} testid="hb-obs-localities" />
          <StatCard label="Cartiere / zone" value={stats?.neighborhoods} testid="hb-obs-neighborhoods" />
          <StatCard label="Date incomplete" value={stats?.incomplete} tone="warn" testid="hb-obs-incomplete" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <StatCard label="Cu an construcție" value={stats?.with_construction_year} testid="hb-obs-with-year" />
          <StatCard label="Cu număr etaje" value={stats?.with_floors} testid="hb-obs-with-floors" />
          <StatCard label="Cu număr unități" value={stats?.with_units} testid="hb-obs-with-units" />
          <StatCard label="Ambele surse" value={stats?.matched_both_sources} testid="hb-obs-both" />
        </div>

        {/* Search + filters */}
        <div className="flex gap-2 flex-wrap mb-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
            <input value={q} onChange={e => setQ(e.target.value)} data-testid="hb-obs-search"
              placeholder="Caută stradă, număr, bloc, localitate, cartier..."
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-stone-700 bg-stone-900 text-stone-100" />
          </div>
          <select value={source} onChange={e => setSource(e.target.value)} data-testid="hb-obs-source"
            className="px-3 py-2 text-sm rounded-lg border border-stone-700 bg-stone-900 text-stone-100">
            <option value="all">Toate sursele</option>
            <option value="hartablocuri">HartaBlocuri</option>
            <option value="propmanage">PropManage</option>
            <option value="both">Ambele</option>
          </select>
          <select value={status} onChange={e => setStatus(e.target.value)} data-testid="hb-obs-status"
            className="px-3 py-2 text-sm rounded-lg border border-stone-700 bg-stone-900 text-stone-100">
            <option value="all">Orice status</option>
            <option value="unverified">Neverificat</option>
            <option value="declared">Declarat</option>
            <option value="documented">Documentat</option>
            <option value="verified">Verificat</option>
          </select>
        </div>

        {/* Table */}
        <div className="rounded-xl border border-stone-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="hb-obs-table">
              <thead className="bg-stone-900 text-stone-400 text-[11px] uppercase">
                <tr>
                  <th className="text-left p-3">Localitate</th>
                  <th className="text-left p-3">Adresă / Stradă</th>
                  <th className="text-left p-3">Bloc</th>
                  <th className="text-center p-3">An</th>
                  <th className="text-center p-3">Etaje</th>
                  <th className="text-center p-3">Unități</th>
                  <th className="text-left p-3">Sursă</th>
                  <th className="text-left p-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {loading && (<tr><td colSpan={8} className="p-6 text-center text-stone-500"><Loader2 className="w-5 h-5 animate-spin mx-auto" /></td></tr>)}
                {!loading && data.buildings.length === 0 && (<tr><td colSpan={8} className="p-6 text-center text-stone-500 text-xs">Niciun rezultat.</td></tr>)}
                {!loading && data.buildings.map(b => (
                  <tr key={b.id} onClick={() => setDetailId(b.id)} data-testid={`hb-obs-row-${b.id}`}
                    className="border-t border-stone-800 hover:bg-stone-900/60 cursor-pointer">
                    <td className="p-3 text-stone-300">{b.city || "—"}</td>
                    <td className="p-3 text-stone-300">{b.address || "—"}</td>
                    <td className="p-3 font-medium text-stone-100">{b.name || "—"}</td>
                    <td className="p-3 text-center text-stone-400">{b.construction_year ?? "—"}</td>
                    <td className="p-3 text-center text-stone-400">{b.floors ?? "—"}</td>
                    <td className="p-3 text-center text-stone-400">{b.units ?? "—"}</td>
                    <td className="p-3">
                      <span className={`text-[9px] px-2 py-0.5 rounded-full border uppercase ${(SOURCE_BADGE[b.source] || SOURCE_BADGE.hartablocuri).cls}`}>
                        {(SOURCE_BADGE[b.source] || SOURCE_BADGE.hartablocuri).label}
                      </span>
                    </td>
                    <td className="p-3 text-[11px] text-stone-400">{b.verification_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between mt-3 text-xs text-stone-400">
          <span data-testid="hb-obs-count">{data.total} clădiri</span>
          <div className="flex items-center gap-2">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} data-testid="hb-obs-prev"
              className="px-3 py-1.5 rounded-lg border border-stone-700 disabled:opacity-40 hover:bg-stone-900">Înapoi</button>
            <span data-testid="hb-obs-page">Pagina {page} / {totalPages}</span>
            <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} data-testid="hb-obs-next"
              className="px-3 py-1.5 rounded-lg border border-stone-700 disabled:opacity-40 hover:bg-stone-900">Înainte</button>
          </div>
        </div>
      </div>

      {detailId && <BuildingDetailModal id={detailId} onClose={() => setDetailId(null)} />}
    </div>
  );
};

export default HartaBlocuriObservability;
