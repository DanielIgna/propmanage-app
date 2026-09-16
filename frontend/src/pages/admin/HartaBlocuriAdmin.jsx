// Admin → HartaBlocuri Import Center.
// Reutilizează endpoint-urile /api/admin/hartablocuri/* (import idempotent, batches,
// buildings cu filtre sursă/status, conflicte + rezolvare). Nu duplică logica de import.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import {
  Database, Layers, GitCompareArrows, RefreshCw, Loader2, CheckCircle2, XCircle,
  Building2, MapPin, AlertTriangle, PlayCircle, ShieldCheck,
} from "lucide-react";
import { API } from "../DashShared";
import { formatApiError } from "../../auth";

const TABS = [
  { id: "overview", label: "Overview", icon: Database },
  { id: "batches", label: "Loturi Import", icon: Layers },
  { id: "buildings", label: "Blocuri", icon: Building2 },
  { id: "conflicts", label: "Conflicte", icon: GitCompareArrows },
];

const fmtDate = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString("ro-RO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }); }
  catch { return iso; }
};

const Stat = ({ label, value, tone = "default", testid }) => {
  const tones = { default: "text-stone-100", good: "text-emerald-400", warn: "text-amber-400", muted: "text-stone-400" };
  return (
    <div className="rounded-xl border border-stone-800 bg-stone-900/50 p-4" data-testid={testid}>
      <div className={`text-2xl font-bold ${tones[tone]}`}>{value ?? "—"}</div>
      <div className="text-xs mt-1 text-stone-400">{label}</div>
    </div>
  );
};

// ─── OVERVIEW ───
const OverviewTab = () => {
  const [stats, setStats] = useState(null);
  const [importing, setImporting] = useState(false);
  const [lastRun, setLastRun] = useState(null);

  const load = useCallback(() => {
    axios.get(`${API}/admin/hartablocuri/stats`).then(r => setStats(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const runImport = async (dryRun) => {
    setImporting(true); setLastRun(null);
    try {
      const { data } = await axios.post(`${API}/admin/hartablocuri/import`, { dry_run: dryRun });
      setLastRun(data); load();
    } catch (e) { alert(formatApiError(e)); }
    finally { setImporting(false); }
  };

  return (
    <div className="space-y-5" data-testid="hb-overview">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Stat label="Total blocuri" value={stats?.total_buildings} testid="hb-stat-total" />
        <Stat label="Cu HartaBlocuri" value={stats?.with_hartablocuri} tone="good" testid="hb-stat-hb" />
        <Stat label="Doar HartaBlocuri" value={stats?.hartablocuri_only} testid="hb-stat-hbonly" />
        <Stat label="Ambele surse" value={stats?.matched_both_sources} tone="good" testid="hb-stat-both" />
        <Stat label="Doar PropManage" value={stats?.propmanage_only} testid="hb-stat-pmonly" />
        <Stat label="Cu conflicte" value={stats?.with_conflicts} tone="warn" testid="hb-stat-conflicts" />
      </div>

      <div className="rounded-xl border border-stone-800 bg-stone-900/50 p-4">
        <div className="flex items-center gap-2 mb-2">
          <PlayCircle className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-bold text-stone-100">Rulează import (idempotent)</h3>
        </div>
        <p className="text-xs text-stone-400 mb-3">
          Importul e idempotent: rerularea aceluiași fișier nu creează duplicate. Datele HartaBlocuri rămân
          „neverificate" și nu suprascriu datele manuale/verificate.
        </p>
        <div className="flex gap-2 flex-wrap">
          <button onClick={() => runImport(true)} disabled={importing} data-testid="hb-import-dry"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold border border-stone-700 text-stone-200 hover:bg-stone-800 disabled:opacity-50">
            {importing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />} Simulare (dry-run)
          </button>
          <button onClick={() => runImport(false)} disabled={importing} data-testid="hb-import-run"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50">
            {importing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PlayCircle className="w-3.5 h-3.5" />} Rulează importul real
          </button>
        </div>
        {lastRun && (
          <div className="mt-3 rounded-lg bg-stone-950/60 border border-stone-800 p-3 text-xs text-stone-300" data-testid="hb-import-result">
            <span className="text-emerald-400 font-bold">{lastRun.dry_run ? "Simulare" : "Import"} finalizat</span> ·
            total {lastRun.total} · noi {lastRun.new_buildings} · matched {lastRun.matched_existing} ·
            update {lastRun.duplicates_updated} · conflicte {lastRun.conflicts} · erori {lastRun.errors}
          </div>
        )}
      </div>
    </div>
  );
};

// ─── BATCHES ───
const BatchesTab = () => {
  const [batches, setBatches] = useState([]);
  useEffect(() => { axios.get(`${API}/admin/hartablocuri/batches`).then(r => setBatches(r.data.batches || [])).catch(() => {}); }, []);
  return (
    <div className="space-y-2" data-testid="hb-batches">
      {batches.length === 0 && <div className="text-xs text-stone-500 italic">Niciun lot de import încă.</div>}
      {batches.map((b, i) => (
        <div key={b.batch_id || i} className="rounded-xl border border-stone-800 bg-stone-900/50 p-4" data-testid={`hb-batch-${i}`}>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-stone-400">{b.batch_id}</span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${b.status === "completed" ? "bg-emerald-500/15 text-emerald-400" : "bg-amber-500/15 text-amber-400"}`}>{b.status}</span>
            {b.dry_run && <span className="text-[10px] px-2 py-0.5 rounded-full bg-stone-700 text-stone-300">dry-run</span>}
            <span className="ml-auto text-[11px] text-stone-500">{fmtDate(b.started_at)}</span>
          </div>
          <div className="mt-2 grid grid-cols-3 sm:grid-cols-7 gap-2 text-center">
            <MiniStat label="Total" value={b.total_records} />
            <MiniStat label="Importate" value={b.imported} />
            <MiniStat label="Matched" value={b.matched_existing} />
            <MiniStat label="Noi" value={b.new_buildings} />
            <MiniStat label="Update" value={b.duplicates_updated} />
            <MiniStat label="Conflicte" value={b.conflicts} tone="warn" />
            <MiniStat label="Erori" value={b.errors} tone={b.errors ? "bad" : "default"} />
          </div>
        </div>
      ))}
    </div>
  );
};
const MiniStat = ({ label, value, tone = "default" }) => {
  const tones = { default: "text-stone-200", warn: "text-amber-400", bad: "text-red-400" };
  return (<div><div className={`text-sm font-bold ${tones[tone]}`}>{value ?? 0}</div><div className="text-[9px] text-stone-500 uppercase">{label}</div></div>);
};

// ─── BUILDINGS ───
const BuildingsTab = () => {
  const [q, setQ] = useState("");
  const [source, setSource] = useState("all");
  const [status, setStatus] = useState("all");
  const [data, setData] = useState({ buildings: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const reqId = React.useRef(0);

  const load = useCallback(() => {
    setLoading(true);
    const myReq = ++reqId.current;
    axios.get(`${API}/admin/hartablocuri/buildings`, { params: { q, source, status, page_size: 30 } })
      .then(r => { if (myReq === reqId.current) setData(r.data); })
      .catch(() => {})
      .finally(() => { if (myReq === reqId.current) setLoading(false); });
  }, [q, source, status]);
  useEffect(() => { const t = setTimeout(load, 300); return () => clearTimeout(t); }, [load]);

  return (
    <div className="space-y-3" data-testid="hb-buildings">
      <div className="flex gap-2 flex-wrap">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Caută nume/adresă/oraș..."
          className="flex-1 min-w-[180px] px-3 py-2 text-sm rounded-lg border border-stone-700 bg-stone-900 text-stone-100" data-testid="hb-b-search" />
        <select value={source} onChange={e => setSource(e.target.value)} data-testid="hb-b-source"
          className="px-3 py-2 text-sm rounded-lg border border-stone-700 bg-stone-900 text-stone-100">
          <option value="all">Toate sursele</option>
          <option value="propmanage">PropManage</option>
          <option value="hartablocuri">HartaBlocuri</option>
          <option value="both">Ambele</option>
        </select>
        <select value={status} onChange={e => setStatus(e.target.value)} data-testid="hb-b-status"
          className="px-3 py-2 text-sm rounded-lg border border-stone-700 bg-stone-900 text-stone-100">
          <option value="all">Orice status</option>
          <option value="unverified">Neverificat</option>
          <option value="declared">Declarat</option>
          <option value="documented">Documentat</option>
          <option value="verified">Verificat</option>
          <option value="conflict">Cu conflicte</option>
        </select>
      </div>
      <div className="text-xs text-stone-500">{loading ? "Se încarcă..." : `${data.total} blocuri`}</div>
      <div className="space-y-1.5">
        {(data.buildings || []).map(b => (
          <div key={b.id} className="rounded-lg border border-stone-800 bg-stone-900/50 p-3 flex items-center gap-3" data-testid={`hb-b-row-${b.id}`}>
            <Building2 className="w-4 h-4 text-stone-500 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-stone-100 truncate">{b.name}</div>
              <div className="text-[11px] text-stone-500 truncate">{b.address}{b.neighborhood ? ` · ${b.neighborhood}` : ""}</div>
            </div>
            <span className={`text-[9px] px-2 py-0.5 rounded-full uppercase ${b.source === "both" ? "bg-[#d4ff3a]/15 text-[#d4ff3a]" : b.source === "hartablocuri" ? "bg-amber-500/15 text-amber-400" : "bg-emerald-500/15 text-emerald-400"}`}>{b.source}</span>
            <span className="text-[10px] text-stone-400">{b.verification_status}</span>
            {b.conflicts_count > 0 && <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 inline-flex items-center gap-1"><AlertTriangle className="w-3 h-3" />{b.conflicts_count}</span>}
            <span className="text-[10px] text-stone-500">{b.residents_count} loc.</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ─── CONFLICTS ───
const ConflictsTab = () => {
  const [data, setData] = useState({ buildings: [], total: 0 });
  const [busy, setBusy] = useState(null);

  const load = useCallback(() => {
    axios.get(`${API}/admin/hartablocuri/conflicts`, { params: { unresolved_only: true } })
      .then(r => setData(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const resolve = async (bid, field, action) => {
    setBusy(`${bid}-${field}`);
    try {
      await axios.post(`${API}/admin/hartablocuri/buildings/${bid}/conflicts/resolve`, { field, action });
      load();
    } catch (e) { alert(formatApiError(e)); }
    finally { setBusy(null); }
  };

  return (
    <div className="space-y-3" data-testid="hb-conflicts">
      <div className="text-xs text-stone-500">{data.total} blocuri cu conflicte nerezolvate</div>
      {data.total === 0 && <div className="text-xs text-emerald-400 italic inline-flex items-center gap-1"><CheckCircle2 className="w-4 h-4" /> Niciun conflict nerezolvat.</div>}
      {(data.buildings || []).map(b => (
        <div key={b.id} className="rounded-xl border border-stone-800 bg-stone-900/50 p-4" data-testid={`hb-conflict-${b.id}`}>
          <div className="flex items-center gap-2 mb-3">
            <Building2 className="w-4 h-4 text-stone-500" />
            <div className="text-sm font-bold text-stone-100">{b.name}</div>
            <div className="text-[11px] text-stone-500">{b.address}</div>
          </div>
          <div className="space-y-2">
            {b.conflicts.map(c => (
              <div key={c.field} className="rounded-lg bg-stone-950/60 border border-stone-800 p-3" data-testid={`hb-conflict-field-${b.id}-${c.field}`}>
                <div className="text-[11px] font-bold text-stone-300 mb-2">{c.field}</div>
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <div className="rounded bg-emerald-500/10 border border-emerald-500/30 p-2">
                    <div className="text-[9px] uppercase text-emerald-400">PropManage</div>
                    <div className="text-sm font-bold text-stone-100">{String(c.propmanage_value)}</div>
                  </div>
                  <div className="rounded bg-amber-500/10 border border-amber-500/30 p-2">
                    <div className="text-[9px] uppercase text-amber-400">HartaBlocuri</div>
                    <div className="text-sm font-bold text-stone-100">{String(c.hartablocuri_value)}</div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => resolve(b.id, c.field, "confirm")} disabled={busy === `${b.id}-${c.field}`}
                    data-testid={`hb-resolve-confirm-${b.id}-${c.field}`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-amber-600 text-white hover:bg-amber-500 disabled:opacity-50">
                    <ShieldCheck className="w-3 h-3" /> Confirmă HartaBlocuri
                  </button>
                  <button onClick={() => resolve(b.id, c.field, "reject")} disabled={busy === `${b.id}-${c.field}`}
                    data-testid={`hb-resolve-reject-${b.id}-${c.field}`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-bold border border-stone-700 text-stone-200 hover:bg-stone-800 disabled:opacity-50">
                    <XCircle className="w-3 h-3" /> Păstrează PropManage
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
      <p className="text-[10px] text-stone-600 pt-2">Rezolvarea nu șterge valoarea originală HartaBlocuri — ambele valori și istoricul rămân păstrate în proveniență.</p>
    </div>
  );
};

export const HartaBlocuriAdmin = () => {
  const [tab, setTab] = useState("overview");
  return (
    <div className="min-h-screen bg-stone-950 text-stone-100" data-testid="hb-admin-page">
      <div className="max-w-6xl mx-auto p-4 sm:p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
            <MapPin className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-bold">HartaBlocuri Import Center</h1>
            <p className="text-xs text-stone-400">Sursă externă de referință · județul Cluj · date neverificate de PropManage</p>
          </div>
          <a href="/administrator" className="text-xs text-stone-400 hover:text-stone-200">← Administrare</a>
        </div>
        <div className="flex gap-2 mb-5 flex-wrap">
          {TABS.map(t => {
            const Icon = t.icon;
            return (
              <button key={t.id} onClick={() => setTab(t.id)} data-testid={`hb-tab-${t.id}`}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-colors ${tab === t.id ? "bg-amber-600 text-white" : "border border-stone-800 text-stone-300 hover:bg-stone-900"}`}>
                <Icon className="w-4 h-4" /> {t.label}
              </button>
            );
          })}
        </div>
        {tab === "overview" && <OverviewTab />}
        {tab === "batches" && <BatchesTab />}
        {tab === "buildings" && <BuildingsTab />}
        {tab === "conflicts" && <ConflictsTab />}
      </div>
    </div>
  );
};

export default HartaBlocuriAdmin;
