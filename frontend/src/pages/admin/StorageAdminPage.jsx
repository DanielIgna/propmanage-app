// StorageAdminPage — ST-001 · configurare stocare FĂRĂ cod + audit utilizare + migrare.
// Route: /admin/storage · API: /api/admin/storage/*
import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  HardDrive, ChevronLeft, Loader2, RefreshCw, SlidersHorizontal, Users,
  CloudUpload, Save, Database, Gauge, CheckCircle2, AlertTriangle,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const Field = ({ label, children }) => (
  <label className="block">
    <span className="text-[10px] font-bold uppercase tracking-wider text-stone-500">{label}</span>
    {children}
  </label>
);
const inputCls = "w-full mt-1 bg-stone-800 border border-stone-700 rounded-xl px-3 py-2 text-sm text-white";

const TIER_LABELS = { free: "FREE (cont gratuit)", house_health: "House Health (abonament)", digital_twin: "Digital Twin (bucket separat)" };
const LIMIT_LABELS = {
  document_vault: "Document Vault (Cartea casei)",
  house_health_doc: "House Health · documente",
  house_health_eval: "House Health · evaluări",
  digital_twin_model: "Digital Twin · modele 3D",
  digital_twin_plan: "Digital Twin · planuri PDF",
  docs_ai: "Docs AI (RAG)",
};

const ConfigPanel = ({ cfg, onSaved }) => {
  const [f, setF] = useState(cfg);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const setTier = (k, v) => setF((p) => ({ ...p, tiers: { ...p.tiers, [k]: { ...p.tiers[k], quota_mb: v } } }));
  const setLimit = (k, v) => setF((p) => ({ ...p, file_limits_mb: { ...p.file_limits_mb, [k]: v } }));
  const setComp = (k, v) => setF((p) => ({ ...p, compression: { ...p.compression, [k]: v } }));
  const setThr = (i, v) => setF((p) => {
    const t = [...(p.warning_thresholds || [80, 95])];
    t[i] = v;
    return { ...p, warning_thresholds: t };
  });

  const save = async () => {
    setBusy(true); setMsg(null);
    try {
      await ax.put("/api/admin/storage/config", {
        tiers: f.tiers,
        file_limits_mb: f.file_limits_mb,
        warning_thresholds: (f.warning_thresholds || []).map(Number),
        compression: f.compression,
      });
      setMsg({ ok: true, text: "Configurația a fost salvată. Limitele se aplică imediat, fără cod." });
      onSaved();
    } catch (e) {
      setMsg({ ok: false, text: e?.response?.data?.detail || e.message });
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-4" data-testid="st-config-panel">
      <div className="border border-stone-800 rounded-2xl p-4">
        <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-3">Cote per plan (MB)</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {Object.keys(TIER_LABELS).map((k) => (
            <Field key={k} label={TIER_LABELS[k]}>
              <input type="number" min="1" className={inputCls} value={f.tiers?.[k]?.quota_mb ?? ""}
                onChange={(e) => setTier(k, Number(e.target.value))} data-testid={`st-tier-${k}`} />
            </Field>
          ))}
        </div>
        <p className="text-[10px] text-stone-500 mt-2">Digital Twin are bucket separat — NU consumă cota personală a utilizatorului.</p>
      </div>

      <div className="border border-stone-800 rounded-2xl p-4">
        <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-3">Limite per fișier (MB)</div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Object.keys(LIMIT_LABELS).map((k) => (
            <Field key={k} label={LIMIT_LABELS[k]}>
              <input type="number" min="0.1" step="0.1" className={inputCls} value={f.file_limits_mb?.[k] ?? ""}
                onChange={(e) => setLimit(k, Number(e.target.value))} data-testid={`st-limit-${k}`} />
            </Field>
          ))}
        </div>
      </div>

      <div className="border border-stone-800 rounded-2xl p-4">
        <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-3">Avertizări & Compresie</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Field label="Prag avertizare (%)">
            <input type="number" min="1" max="99" className={inputCls} value={f.warning_thresholds?.[0] ?? 80}
              onChange={(e) => setThr(0, Number(e.target.value))} data-testid="st-thr-soft" />
          </Field>
          <Field label="Prag critic (%)">
            <input type="number" min="2" max="100" className={inputCls} value={f.warning_thresholds?.[1] ?? 95}
              onChange={(e) => setThr(1, Number(e.target.value))} data-testid="st-thr-critical" />
          </Field>
          <Field label="Calitate imagine (JPEG/WebP)">
            <input type="number" min="40" max="100" className={inputCls} value={f.compression?.image_quality ?? 82}
              onChange={(e) => setComp("image_quality", Number(e.target.value))} data-testid="st-img-quality" />
          </Field>
          <Field label="Dimensiune max. imagine (px)">
            <input type="number" min="800" className={inputCls} value={f.compression?.image_max_dimension ?? 2560}
              onChange={(e) => setComp("image_max_dimension", Number(e.target.value))} />
          </Field>
          <Field label="Video CRF (18–35, mai mare = mai mic)">
            <input type="number" min="18" max="35" className={inputCls} value={f.compression?.video_crf ?? 28}
              onChange={(e) => setComp("video_crf", Number(e.target.value))} />
          </Field>
          <Field label="Video: comprimă peste (MB)">
            <input type="number" min="1" className={inputCls} value={f.compression?.video_min_mb ?? 8}
              onChange={(e) => setComp("video_min_mb", Number(e.target.value))} />
          </Field>
        </div>
        <div className="flex gap-2 mt-3">
          {[["images_enabled", "Compresie imagini"], ["videos_enabled", "Compresie video"]].map(([k, lbl]) => (
            <button key={k} onClick={() => setComp(k, !f.compression?.[k])} data-testid={`st-comp-${k}`}
              className={`px-3 py-1.5 rounded-lg text-[11px] font-bold border ${f.compression?.[k] ? "bg-[#d4ff3a]/10 text-[#d4ff3a] border-[#d4ff3a]/40" : "bg-stone-900 text-stone-400 border-stone-700"}`}>
              {lbl}: {f.compression?.[k] ? "ON" : "OFF"}
            </button>
          ))}
        </div>
      </div>

      {msg && (
        <div className={`text-xs font-bold p-3 rounded-xl border ${msg.ok ? "text-emerald-300 border-emerald-500/30 bg-emerald-500/10" : "text-rose-300 border-rose-500/30 bg-rose-500/10"}`}
          data-testid="st-config-msg">{msg.text}</div>
      )}
      <button onClick={save} disabled={busy} data-testid="st-save-config"
        className="px-4 py-2 text-xs rounded-xl bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5">
        {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />} Salvează configurația
      </button>
    </div>
  );
};

const MigratePanel = ({ ov, reload }) => {
  const [busy, setBusy] = useState(false);
  const mig = ov?.migration || {};
  const start = async () => {
    setBusy(true);
    try { await ax.post("/api/admin/storage/migrate"); reload(); } finally { setBusy(false); }
  };
  const recompute = async () => {
    setBusy(true);
    try { await ax.post("/api/admin/storage/recompute"); reload(); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-3" data-testid="st-migrate-panel">
      <div className="border border-stone-800 rounded-2xl p-4">
        <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-2">Migrare disc local → Emergent Object Storage</div>
        <p className="text-[11px] text-stone-500 mb-3">
          House Health se mută complet pe Object Storage. Digital Twin primește copie durabilă (mirror) —
          discul rămâne cache pentru viewer 3D și conversia Blender. Fișierele de pe disc se pierd la redeploy; după migrare sunt în siguranță.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={start} disabled={busy || mig.status === "running"} data-testid="st-migrate-btn"
            className="px-4 py-2 text-xs rounded-xl bg-[#d4ff3a] text-stone-900 font-bold flex items-center gap-1.5">
            {mig.status === "running" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CloudUpload className="w-3.5 h-3.5" />}
            {mig.status === "running" ? "Migrarea rulează…" : "Pornește migrarea"}
          </button>
          <button onClick={reload} className="px-3 py-2 text-xs rounded-xl bg-stone-800 border border-stone-700 text-white font-bold flex items-center gap-1.5" data-testid="st-migrate-refresh">
            <RefreshCw className="w-3 h-3" /> Actualizează statusul
          </button>
          <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full border ${mig.status === "done" ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30" : mig.status === "running" ? "bg-amber-500/10 text-amber-300 border-amber-500/30" : mig.status === "failed" ? "bg-rose-500/10 text-rose-300 border-rose-500/30" : "bg-stone-800 text-stone-400 border-stone-700"}`}
            data-testid="st-migrate-status">{mig.status || "not_started"}</span>
        </div>
        {mig.status && mig.status !== "not_started" && (
          <div className="mt-3 grid grid-cols-2 md:grid-cols-5 gap-2 text-center">
            {[["Docs HH", mig.hh_docs], ["Evaluări HH", mig.hh_evals], ["Modele DT", mig.dt_models], ["Planuri DT", mig.dt_plans]].map(([l, v]) => (
              <div key={l} className="bg-stone-900/40 border border-stone-800 rounded-xl p-2">
                <div className="text-lg font-black text-white">{v ?? 0}</div>
                <div className="text-[9px] uppercase text-stone-500">{l}</div>
              </div>
            ))}
            <div className="bg-stone-900/40 border border-stone-800 rounded-xl p-2">
              <div className="text-lg font-black text-white">{((mig.bytes_moved || 0) / 1024 / 1024).toFixed(1)} MB</div>
              <div className="text-[9px] uppercase text-stone-500">mutați</div>
            </div>
          </div>
        )}
        {(mig.errors || []).length > 0 && (
          <div className="mt-2 text-[10px] text-rose-300">{mig.errors.length} erori: {mig.errors.slice(0, 3).join(" · ")}</div>
        )}
      </div>
      <div className="border border-stone-800 rounded-2xl p-4">
        <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-2">Recalculare retroactivă</div>
        <p className="text-[11px] text-stone-500 mb-3">Agregă spațiul deja ocupat de fiecare utilizator din toate colecțiile (Vault, House Health, Digital Twin, Docs AI).</p>
        <button onClick={recompute} disabled={busy} data-testid="st-recompute-btn"
          className="px-4 py-2 text-xs rounded-xl bg-stone-800 border border-stone-700 text-white font-bold flex items-center gap-1.5">
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Gauge className="w-3.5 h-3.5" />} Recalculează utilizarea
        </button>
      </div>
    </div>
  );
};

export default function StorageAdminPage() {
  const navigate = useNavigate();
  const [ov, setOv] = useState(null);
  const [tab, setTab] = useState("usage");

  const load = useCallback(() => {
    ax.get("/api/admin/storage/overview").then((r) => setOv(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const TABS = [
    { id: "usage", label: "Utilizare", icon: Users },
    { id: "config", label: "Configurare", icon: SlidersHorizontal },
    { id: "migrate", label: "Migrare & Audit", icon: CloudUpload },
  ];

  return (
    <div className="min-h-screen bg-stone-950 p-4 lg:p-8 admin-shell" data-testid="storage-admin-page">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 flex-wrap mb-2">
          <button onClick={() => navigate("/admin")} className="text-stone-400 hover:text-white" data-testid="st-back"><ChevronLeft className="w-5 h-5" /></button>
          <HardDrive className="w-6 h-6 text-[#d4ff3a]" />
          <h1 className="text-xl lg:text-2xl font-bold text-white">Storage</h1>
          <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-full border bg-[#d4ff3a]/10 text-[#d4ff3a] border-[#d4ff3a]/30">ST-001 · Cote configurabile</span>
          <div className="flex-1" />
          <button onClick={load} className="px-3 py-1.5 text-[11px] rounded-xl bg-stone-800 border border-stone-700 text-white font-bold flex items-center gap-1.5" data-testid="st-reload">
            <RefreshCw className="w-3 h-3" /> Reîncarcă
          </button>
        </div>
        <p className="text-xs text-stone-500 mb-5">FREE 250 MB · House Health 5 GB · Digital Twin 20 GB (separat). Zero limite hardcodate — totul din DB.</p>

        {!ov && <Loader2 className="w-6 h-6 animate-spin text-stone-500" />}

        {ov && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5" data-testid="st-kpis">
              {[["Stocare personală", ov.totals?.personal_human], ["Digital Twin", ov.totals?.dt_human],
                ["Fișiere", (ov.totals?.files || 0) + (ov.totals?.dt_files || 0)], ["Utilizatori cu fișiere", ov.totals?.users]].map(([l, v]) => (
                <div key={l} className="bg-stone-900/40 border border-stone-800 rounded-xl p-3">
                  <div className="text-[10px] uppercase text-stone-500">{l}</div>
                  <div className="text-xl font-bold text-white">{v ?? 0}</div>
                </div>
              ))}
            </div>

            <div className="flex gap-1.5 flex-wrap mb-5">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button key={id} onClick={() => setTab(id)}
                  className={`px-3 py-1.5 text-[11px] font-bold rounded-xl border flex items-center gap-1.5 ${tab === id ? "bg-[#d4ff3a]/10 text-[#d4ff3a] border-[#d4ff3a]/40" : "bg-stone-900 text-stone-400 border-stone-800"}`}
                  data-testid={`st-tab-${id}`}>
                  <Icon className="w-3 h-3" /> {label}
                </button>
              ))}
            </div>

            {tab === "usage" && (
              <div className="space-y-4" data-testid="st-usage-tab">
                <div className="border border-stone-800 rounded-2xl p-4">
                  <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-2 flex items-center gap-1.5"><Database className="w-3.5 h-3.5" /> Module & provideri</div>
                  {(ov.modules || []).map((m) => (
                    <div key={m.id} className="flex items-center gap-3 py-2 border-b border-stone-900 last:border-0" data-testid={`st-module-${m.id}`}>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-bold text-white">{m.label}</div>
                        <div className="text-[10px] text-stone-500">{m.provider}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-black text-white">{m.human}</div>
                        <div className="text-[10px] text-stone-500">{m.count} fișiere</div>
                      </div>
                    </div>
                  ))}
                  <div className="mt-2 text-[10px] text-stone-500 flex items-center gap-1.5">
                    {ov.video_compression_available ? <CheckCircle2 className="w-3 h-3 text-emerald-400" /> : <AlertTriangle className="w-3 h-3 text-amber-400" />}
                    Compresie video (ffmpeg): {ov.video_compression_available ? "disponibilă" : "indisponibilă pe acest server"} ·
                    Disc local: HH {ov.disk?.house_health_human} · DT {ov.disk?.digital_twin_human}
                  </div>
                </div>

                <div className="border border-stone-800 rounded-2xl p-4" data-testid="st-top-users">
                  <div className="text-xs font-black uppercase tracking-wider text-stone-400 mb-2">Top utilizatori</div>
                  {(ov.top_users || []).length === 0 && <div className="text-xs text-stone-500">Nimeni nu ocupă spațiu încă.</div>}
                  {(ov.top_users || []).map((u) => (
                    <div key={u.user_id} className="py-2 border-b border-stone-900 last:border-0">
                      <div className="flex items-center gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-bold text-white truncate">{u.name || u.email || u.user_id}</div>
                          <div className="text-[10px] text-stone-500">{u.email} · {u.tier_label}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-xs font-black text-white">{u.personal_human} <span className="text-stone-500 font-normal">/ {u.pct}%</span></div>
                          {(u.digital_twin_bytes || 0) > 0 && <div className="text-[10px] text-sky-300">DT: {u.dt_human}</div>}
                        </div>
                      </div>
                      <div className="mt-1.5 h-1.5 bg-stone-800 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${Math.min(100, u.pct)}%`, background: u.pct >= 95 ? "#ef4444" : u.pct >= 80 ? "#f59e0b" : "#d4ff3a" }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {tab === "config" && <ConfigPanel cfg={ov.config} onSaved={load} />}
            {tab === "migrate" && <MigratePanel ov={ov} reload={load} />}
          </>
        )}
      </div>
    </div>
  );
}
