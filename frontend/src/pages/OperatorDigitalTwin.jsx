// Operator Digital Twin onboarding & file uploads for clients.
//
// PROPERTY TWIN · STRATUL 3D (decizie Fondator, 27 Aug 2026): această suprafață operează pe
// `digital_twin_projects` + `digital_twin_models` (model arhitectural/BIM/SketchUp + layere + Trimble)
// = stratul 3D profesional. NU e duplicat cu OperatorTwin.jsx — acela e stratul 2D (`twins`).
// Ambele = suprafețe operator ale ACELUIAȘI Property Twin (2D + 3D), tab-uri în OperatorDashboard.
// Consolidare = clarificare non-breaking, FĂRĂ ștergere.
// User flow:
// 1. Operator sees list of clients with digital_twin_pro flag (grouped by status: needs_setup / in_progress / delivered)
// 2. For clients without flag → "Acordă acces" button (uses operator grant endpoint)
// 3. For clients without project → "Creează proiect" button + name input
// 4. For projects existing → "Încarcă model 3D" (.glb / .gltf / .skp) + "Încarcă plan 2D" (.pdf)
// 5. Files become instantly visible to the client at /digital-twin
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  Box, Upload, FileText, CheckCircle2, Clock, AlertCircle, Loader2, X,
  Plus, Search, Mail, MapPin, User as UserIcon, Layers, Eye, ShieldCheck, Edit3,
  RefreshCw, Wand2, Link2, Unlink,
} from "lucide-react";
import { API } from "./DashShared";

const STATUS_META = {
  needs_setup: { label: "Necesită setup", color: "bg-amber-500/15 text-amber-300 border-amber-500/30", icon: AlertCircle },
  in_progress: { label: "În lucru", color: "bg-blue-500/15 text-blue-300 border-blue-500/30", icon: Clock },
  delivered: { label: "Livrat", color: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30", icon: CheckCircle2 },
};

const fmtBytes = (n) => {
  if (!n) return "—";
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / (1024 * 1024)).toFixed(1) + " MB";
};

// ============= GRANT ACCESS MODAL =============
const GrantAccessModal = ({ onClose, onGranted }) => {
  const [email, setEmail] = useState("");
  const [results, setResults] = useState([]);
  const [busy, setBusy] = useState(false);
  const [searching, setSearching] = useState(false);
  const [err, setErr] = useState(null);

  const search = async (q) => {
    setEmail(q);
    setErr(null);
    if (q.trim().length < 2) { setResults([]); return; }
    setSearching(true);
    try {
      // Operator-scoped client search (role=client only). Case-insensitive, name + email.
      const r = await axios.get(`${API}/operator/digital-twin/search-clients`, { params: { q: q.trim() } });
      setResults(r.data?.items || []);
    } catch (e) {
      setResults([]);
      setErr(e?.response?.data?.detail || "Eroare la căutare. Încearcă din nou.");
    } finally {
      setSearching(false);
    }
  };

  const grant = async (clientId) => {
    setBusy(true); setErr(null);
    try {
      await axios.post(`${API}/operator/digital-twin/grant-access`, { user_id: clientId, active: true });
      onGranted?.();
      onClose();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  // Client already has DT Pro → don't create a second relation, just refresh + close.
  const alreadyGranted = () => { onGranted?.(); onClose(); };

  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-stone-900 border border-white/10 rounded-2xl p-5 w-full max-w-md space-y-3" data-testid="grant-access-modal">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-400/90 font-semibold">Digital Twin Pro</div>
            <h3 className="font-serif text-lg text-white">Acordă acces unui client</h3>
            <p className="text-xs text-stone-400 mt-0.5">Caută clientul după nume sau email și activează-i flag-ul DT.</p>
          </div>
          <button onClick={onClose}><X className="w-5 h-5 text-stone-500" /></button>
        </div>

        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-stone-500" />
          <input
            value={email}
            onChange={(e) => search(e.target.value)}
            placeholder="Caută client după nume sau email..."
            className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-3 py-2.5 text-sm text-white placeholder:text-stone-500"
            data-testid="grant-access-search"
            autoFocus
          />
        </div>

        <div className="space-y-1 max-h-72 overflow-y-auto">
          {searching && <div className="text-xs text-stone-500 text-center py-3" data-testid="grant-search-loading">Se caută…</div>}
          {!searching && !err && email.trim().length >= 2 && results.length === 0 && <div className="text-xs text-stone-500 text-center py-3" data-testid="grant-no-results">Niciun client găsit.</div>}
          {results.map(u => (
            <button
              key={u.id}
              onClick={() => (u.digital_twin_pro ? alreadyGranted() : grant(u.id))}
              disabled={busy}
              className="w-full text-left bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg p-2.5 disabled:opacity-50"
              data-testid={`grant-target-${u.id}`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-sm text-white font-medium truncate">{u.name}</div>
                  <div className="text-[11px] text-stone-400 truncate">{u.email}</div>
                </div>
                {u.digital_twin_pro && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/25 shrink-0" data-testid={`already-granted-${u.id}`}>
                    Acces deja acordat
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>

        {err && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">{err}</div>}
      </div>
    </div>
  );
};

// ============= CREATE PROJECT MODAL =============
const CreateProjectModal = ({ client, onClose, onCreated }) => {
  const [name, setName] = useState(`Digital Twin — ${client.client_name || "Client"}`);
  const [desc, setDesc] = useState("");
  const [trimbleUrl, setTrimbleUrl] = useState("");
  const [properties, setProperties] = useState([]);
  const [propertyId, setPropertyId] = useState("");
  const [loadingProps, setLoadingProps] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  // P0.1 — Property Anchor: încarcă proprietățile clientului pentru selector.
  useEffect(() => {
    let active = true;
    (async () => {
      setLoadingProps(true);
      try {
        const { data } = await axios.get(`${API}/operator/digital-twin/clients/${client.client_id}/properties`);
        if (!active) return;
        const items = data.items || [];
        setProperties(items);
        if (items.length === 1) setPropertyId(items[0].id);
      } catch (_) {
        if (active) setProperties([]);
      } finally {
        if (active) setLoadingProps(false);
      }
    })();
    return () => { active = false; };
  }, [client.client_id]);

  const create = async () => {
    setBusy(true); setErr(null);
    try {
      const { data } = await axios.post(`${API}/operator/digital-twin/clients/${client.client_id}/projects`, {
        client_id: client.client_id, name, description: desc,
        property_id: propertyId || null,
        trimble_embed_url: trimbleUrl.trim() || null,
      });
      onCreated?.(data);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-stone-900 border border-white/10 rounded-2xl p-5 w-full max-w-md space-y-3" data-testid="create-project-modal">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-400/90 font-semibold">Pas 1 / 3 · Proiect</div>
            <h3 className="font-serif text-lg text-white">Creează proiect Digital Twin</h3>
            <p className="text-xs text-stone-400 mt-0.5">Pentru <strong>{client.client_name}</strong>. Proiectul va apărea în contul clientului instant.</p>
          </div>
          <button onClick={onClose}><X className="w-5 h-5 text-stone-500" /></button>
        </div>

        <div>
          <label className="text-[10px] uppercase text-emerald-300 font-semibold flex items-center gap-1.5">
            <MapPin className="w-3 h-3" /> Proprietate (Property Anchor) *
          </label>
          {loadingProps ? (
            <div className="mt-1 text-xs text-stone-500 flex items-center gap-1.5" data-testid="create-project-property-loading">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Se încarcă proprietățile clientului…
            </div>
          ) : properties.length === 0 ? (
            <div className="mt-1 text-xs text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2" data-testid="create-project-no-properties">
              Clientul nu are nicio proprietate. Clientul trebuie să adauge o proprietate înainte de a ancora un Digital Twin.
            </div>
          ) : (
            <select
              value={propertyId}
              onChange={(e) => setPropertyId(e.target.value)}
              className="w-full mt-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
              data-testid="create-project-property"
            >
              <option value="" className="bg-stone-900">Selectează proprietatea…</option>
              {properties.map(p => (
                <option key={p.id} value={p.id} className="bg-stone-900">
                  {p.name}{p.address ? ` · ${p.address}` : ""}
                </option>
              ))}
            </select>
          )}
          <p className="text-[10px] text-stone-500 mt-1">Twin-ul și modelele 3D vor fi ancorate de această proprietate.</p>
        </div>

        <div>
          <label className="text-[10px] uppercase text-stone-500 font-semibold">Nume proiect</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={200}
            className="w-full mt-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            data-testid="create-project-name"
          />
        </div>
        <div>
          <label className="text-[10px] uppercase text-stone-500 font-semibold">Descriere (opțional)</label>
          <textarea
            rows={3}
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            maxLength={2000}
            className="w-full mt-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            data-testid="create-project-desc"
          />
        </div>

        <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3 space-y-1.5">
          <label className="text-[10px] uppercase text-emerald-300 font-bold flex items-center gap-1.5">
            <Box className="w-3 h-3" /> Trimble Connect — viewer SketchUp nativ (opțional)
          </label>
          <input
            value={trimbleUrl}
            onChange={(e) => setTrimbleUrl(e.target.value)}
            placeholder="https://web.connect.trimble.com/projects/.../viewer/..."
            maxLength={2000}
            className="w-full bg-white/5 border border-emerald-500/20 rounded-lg px-3 py-1.5 text-xs text-white placeholder:text-stone-600"
            data-testid="create-project-trimble"
          />
          <p className="text-[10px] text-stone-500 leading-relaxed">
            🔗 Lipește aici link-ul de share din Trimble Connect → clientul vede modelul SketchUp cu X-Ray nativ, layers, secțiuni. Poți seta și mai târziu.
          </p>
        </div>

        {err && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">{err}</div>}

        <div className="flex gap-2 pt-1">
          <button onClick={onClose} className="flex-1 px-3 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-stone-300">Anulează</button>
          <button
            onClick={create}
            disabled={busy || name.trim().length < 2 || !propertyId}
            className="flex-1 px-3 py-2 text-sm rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-medium flex items-center justify-center gap-1.5"
            data-testid="create-project-submit"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            Creează proiect
          </button>
        </div>
      </div>
    </div>
  );
};

// ============= UPLOAD FILES MODAL =============
const UploadFilesModal = ({ project, client, onClose, onUploaded }) => {
  const [tab, setTab] = useState("3d"); // 3d | 2d | trimble
  const [model, setModel] = useState(null);
  const [plan, setPlan] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [history, setHistory] = useState({ models: [], plans: [] });
  const [trimbleUrl, setTrimbleUrl] = useState(project.trimble_embed_url || "");
  const [savingTrimble, setSavingTrimble] = useState(false);
  const [err, setErr] = useState(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiMsg, setAiMsg] = useState(null);

  const aiGenerate = async () => {
    setAiBusy(true); setAiMsg(null); setErr(null);
    try {
      await axios.post(`${API}/digital-twin/projects/${project.id}/ai-generate`);
      setAiMsg("✓ Model AI orientativ generat (inferred, neverificat).");
      await loadHistory();
      onUploaded?.();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setAiBusy(false);
    }
  };

  const saveTrimble = async () => {
    setSavingTrimble(true); setErr(null);
    try {
      await axios.patch(`${API}/operator/digital-twin/projects/${project.id}/trimble`, {
        trimble_embed_url: trimbleUrl.trim() || null,
      });
      onUploaded?.();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setSavingTrimble(false);
    }
  };

  const loadHistory = async () => {
    try {
      const [m, p] = await Promise.all([
        axios.get(`${API}/digital-twin/projects/${project.id}/models`),
        axios.get(`${API}/digital-twin/projects/${project.id}/plans`),
      ]);
      setHistory({
        models: m.data.items || [],
        plans: p.data.items || [],
      });
    } catch (_) { /* ignore */ }
  };
  useEffect(() => { loadHistory(); }, [project.id]);

  // Auto-poll while any .skp archive is mid-conversion so the UI updates
  // from "Se convertește 35%" → "Gata!" without manual refresh.
  useEffect(() => {
    const converting = (history.models || []).filter(
      m => m.kind === "archive" && m.conversion_status && !["completed", "failed", "unsupported", "n/a"].includes(m.conversion_status)
    );
    if (converting.length === 0) return undefined;
    const t = setInterval(() => { loadHistory(); }, 5000);
    return () => clearInterval(t);
  }, [history.models]);

  const retryConversion = async (modelId) => {
    try {
      await axios.post(`${API}/digital-twin/conversions/${modelId}/retry`);
      await loadHistory();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    }
  };

  const uploadModel = async () => {
    if (!model) return;
    setUploading(true); setErr(null); setProgress(0);
    const fd = new FormData();
    fd.append("file", model);
    try {
      await axios.post(`${API}/digital-twin/projects/${project.id}/upload`, fd, {
        onUploadProgress: (e) => setProgress(Math.round((e.loaded / e.total) * 100)),
      });
      setModel(null);
      await loadHistory();
      onUploaded?.();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setUploading(false);
    }
  };

  const uploadPlan = async () => {
    if (!plan) return;
    setUploading(true); setErr(null); setProgress(0);
    const fd = new FormData();
    fd.append("file", plan);
    try {
      await axios.post(`${API}/digital-twin/projects/${project.id}/plans`, fd, {
        onUploadProgress: (e) => setProgress(Math.round((e.loaded / e.total) * 100)),
      });
      setPlan(null);
      await loadHistory();
      onUploaded?.();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-stone-900 border border-white/10 rounded-2xl p-5 w-full max-w-xl max-h-[90vh] overflow-y-auto space-y-3" data-testid="upload-files-modal">
        <div className="flex items-start justify-between sticky top-0 bg-stone-900 pb-2 z-10">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-400/90 font-semibold">Încarcă fișiere · Proiect</div>
            <h3 className="font-serif text-lg text-white">{project.name}</h3>
            <p className="text-xs text-stone-400 mt-0.5">Pentru <strong>{client.client_name}</strong> · {client.client_email}</p>
          </div>
          <button onClick={onClose}><X className="w-5 h-5 text-stone-500" /></button>
        </div>

        {/* Tab switcher */}
        <div className="flex gap-1 bg-white/[0.03] rounded-lg p-1">
          <button
            onClick={() => setTab("3d")}
            className={`flex-1 py-1.5 rounded text-xs font-medium ${tab === "3d" ? "bg-emerald-500/20 text-emerald-300" : "text-stone-400"}`}
            data-testid="upload-tab-3d"
          >
            <Box className="w-3.5 h-3.5 inline mr-1" />Model 3D
          </button>
          <button
            onClick={() => setTab("2d")}
            className={`flex-1 py-1.5 rounded text-xs font-medium ${tab === "2d" ? "bg-emerald-500/20 text-emerald-300" : "text-stone-400"}`}
            data-testid="upload-tab-2d"
          >
            <FileText className="w-3.5 h-3.5 inline mr-1" />Plan 2D (PDF)
          </button>
          <button
            onClick={() => setTab("trimble")}
            className={`flex-1 py-1.5 rounded text-xs font-medium ${tab === "trimble" ? "bg-emerald-500/20 text-emerald-300" : "text-stone-400"}`}
            data-testid="upload-tab-trimble"
          >
            <Wand2 className="w-3.5 h-3.5 inline mr-1" />Trimble Connect
          </button>
        </div>

        {/* 3D upload zone */}
        {tab === "3d" && (
          <div className="space-y-2">
            <label className="block border-2 border-dashed border-white/10 hover:border-emerald-500/50 rounded-xl p-6 text-center cursor-pointer transition-colors">
              <input
                type="file"
                accept=".glb,.gltf,.skp,.dae,.obj,.fbx,.stl,.ply"
                onChange={(e) => setModel(e.target.files[0])}
                className="hidden"
                data-testid="upload-3d-input"
              />
              <Upload className="w-8 h-8 mx-auto text-stone-500 mb-2" />
              {model ? (
                <div>
                  <div className="text-sm text-white font-medium">{model.name}</div>
                  <div className="text-xs text-stone-400">{fmtBytes(model.size)}</div>
                </div>
              ) : (
                <div>
                  <div className="text-sm text-stone-300">Trage fișierul aici sau click</div>
                  <div className="text-[11px] text-stone-500 mt-1 leading-relaxed">
                    <strong className="text-emerald-400">.glb / .gltf</strong> — vizualizabil instant<br/>
                    <strong className="text-amber-400">.dae / .obj / .fbx / .stl / .ply</strong> — auto-conversie via Blender ⚡<br/>
                    <strong className="text-stone-400">.skp</strong> — SketchUp: stocat intact & descărcabil (exportă .glb/.gltf/.dae din SketchUp sau vezi în Trimble Connect)
                  </div>
                </div>
              )}
            </label>

            {model && (
              <>
                {uploading && (
                  <div className="bg-white/5 rounded-full h-1.5 overflow-hidden">
                    <div className="h-full bg-emerald-500 transition-all" style={{ width: `${progress}%` }} />
                  </div>
                )}
                <button
                  onClick={uploadModel}
                  disabled={uploading}
                  className="w-full py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white text-sm font-medium flex items-center justify-center gap-2"
                  data-testid="upload-3d-submit"
                >
                  {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  {uploading ? `Se încarcă ${progress}%...` : "Încarcă"}
                </button>
              </>
            )}

            {/* AI-3D orientative generation (inferred) — anchored projects only */}
            <div className="pt-2 border-t border-white/5">
              <button
                onClick={aiGenerate}
                disabled={aiBusy}
                className="w-full py-2 rounded-lg border border-violet-500/30 bg-violet-500/10 hover:bg-violet-500/20 disabled:opacity-50 text-violet-200 text-sm font-medium flex items-center justify-center gap-2"
                data-testid="op-ai-generate"
                title="Generează un model 3D orientativ (AI, inferred). Necesită proiect ancorat la o proprietate. Nu suprascrie modele documentate."
              >
                {aiBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
                {aiBusy ? "Se generează…" : "Generează AI 3D (orientativ)"}
              </button>
              {aiMsg && <div className="mt-2 text-[11px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2" data-testid="op-ai-msg">{aiMsg}</div>}
              <p className="text-[10px] text-stone-500 mt-1.5 leading-relaxed">
                Massing orientativ din camerele proprietății. Etichetat „inferred / neverificat". Nu înlocuiește modelul profesional.
              </p>
            </div>

            {history.models.length > 0 && (
              <div className="pt-3 space-y-1.5">
                <div className="text-[10px] uppercase tracking-wider text-stone-500 font-bold">Versiuni încărcate</div>
                {history.models.map(m => {
                  const isArchive = m.kind === "archive";
                  const isSource = m.kind === "source"; // DAE/OBJ/FBX/STL/PLY — auto-converts to .glb
                  const cstatus = m.conversion_status;
                  const cpct = m.conversion_percent || 0;
                  const isConverting = (isArchive || isSource) && cstatus && !["completed", "failed", "unsupported", "n/a"].includes(cstatus);
                  const engine = m.conversion_engine === "blender" ? "Blender ⚡" : "CloudConvert ☁️";
                  const conversionLabel = {
                    pending: `${engine} · În așteptare…`,
                    uploading: `${engine} · Trimit…`,
                    converting: `${engine} · Se convertește…`,
                    downloading: `${engine} · Finalizez…`,
                    completed: "Convertit ✓",
                    failed: "Conversie eșuată",
                  }[cstatus] || null;
                  return (
                    <div key={m.id} className="bg-white/[0.03] border border-white/5 rounded-lg p-2 text-xs space-y-1.5" data-testid={`model-row-${m.id}`}>
                      <div className="flex items-center gap-2">
                        {isArchive ? <FileText className="w-3.5 h-3.5 text-amber-400" /> : (isSource ? <Wand2 className="w-3.5 h-3.5 text-blue-400" /> : <Box className="w-3.5 h-3.5 text-emerald-400" />)}
                        <div className="flex-1 min-w-0">
                          <div className="text-white truncate">{m.filename}</div>
                          <div className="text-stone-500 text-[10px]">
                            {fmtBytes(m.size_bytes)} · {new Date(m.uploaded_at).toLocaleDateString("ro-RO")} · {m.uploaded_by_name}
                            {m.converted_from_filename && <span className="text-emerald-400/80"> · ⚡ auto din {m.converted_from_filename}</span>}
                          </div>
                        </div>
                        {isArchive && !cstatus && <span className="text-[9px] uppercase text-amber-400">Descărcabil</span>}
                        {cstatus === "unsupported" && <span className="text-[9px] uppercase text-amber-400">SketchUp · descărcabil</span>}
                        {isSource && !cstatus && <span className="text-[9px] uppercase text-blue-400">Sursă</span>}
                        {cstatus === "completed" && <span className="text-[9px] uppercase text-emerald-400 flex items-center gap-1"><Wand2 className="w-3 h-3"/>GLB Gata</span>}
                      </div>
                      {cstatus === "unsupported" && (
                        <div className="bg-amber-500/10 border border-amber-500/20 rounded p-2 space-y-1.5" data-testid={`conv-unsupported-${m.id}`}>
                          <div className="text-[10px] text-amber-200 leading-relaxed">
                            📦 {m.conversion_note || "Fișier SketchUp stocat intact. Nu poate fi convertit automat pe server."}
                          </div>
                          <div className="flex items-center gap-2">
                            <a
                              href={`${process.env.REACT_APP_BACKEND_URL}${m.url}`}
                              target="_blank" rel="noreferrer"
                              className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-100 flex items-center gap-1"
                              data-testid={`skp-download-${m.id}`}
                            >
                              <FileText className="w-2.5 h-2.5" /> Descarcă .skp
                            </a>
                            <span className="text-[9px] text-stone-500">sau folosește tab-ul „Trimble Connect” pentru viewer nativ</span>
                          </div>
                        </div>
                      )}
                      {isConverting && (
                        <div className="space-y-1" data-testid={`conv-row-${m.id}`}>
                          <div className="flex items-center justify-between text-[10px]">
                            <span className="text-emerald-300 flex items-center gap-1"><Loader2 className="w-2.5 h-2.5 animate-spin" />{conversionLabel}</span>
                            <span className="text-stone-400 font-mono">{cpct}%</span>
                          </div>
                          <div className="bg-white/5 rounded-full h-1 overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-amber-500 via-emerald-500 to-emerald-400 transition-all" style={{ width: `${cpct}%` }} />
                          </div>
                        </div>
                      )}
                      {cstatus === "failed" && (
                        <div className="flex items-center justify-between gap-2 bg-red-500/10 border border-red-500/20 rounded p-1.5">
                          <div className="text-[10px] text-red-300 truncate" title={m.conversion_error}>⚠️ {m.conversion_error || "Eroare conversie"}</div>
                          <button onClick={() => retryConversion(m.id)} className="text-[10px] px-2 py-0.5 rounded bg-red-500/20 hover:bg-red-500/30 text-red-200 flex items-center gap-1" data-testid={`conv-retry-${m.id}`}>
                            <RefreshCw className="w-2.5 h-2.5" />Reîncearcă
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* 2D upload zone */}
        {tab === "2d" && (
          <div className="space-y-2">
            <label className="block border-2 border-dashed border-white/10 hover:border-emerald-500/50 rounded-xl p-6 text-center cursor-pointer transition-colors">
              <input
                type="file"
                accept=".pdf,application/pdf"
                onChange={(e) => setPlan(e.target.files[0])}
                className="hidden"
                data-testid="upload-2d-input"
              />
              <Upload className="w-8 h-8 mx-auto text-stone-500 mb-2" />
              {plan ? (
                <div>
                  <div className="text-sm text-white font-medium">{plan.name}</div>
                  <div className="text-xs text-stone-400">{fmtBytes(plan.size)}</div>
                </div>
              ) : (
                <div>
                  <div className="text-sm text-stone-300">Trage planul PDF aici sau click</div>
                  <div className="text-[11px] text-stone-500 mt-1">Plan structural 2D (.pdf)</div>
                </div>
              )}
            </label>

            {plan && (
              <>
                {uploading && (
                  <div className="bg-white/5 rounded-full h-1.5 overflow-hidden">
                    <div className="h-full bg-emerald-500 transition-all" style={{ width: `${progress}%` }} />
                  </div>
                )}
                <button
                  onClick={uploadPlan}
                  disabled={uploading}
                  className="w-full py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white text-sm font-medium flex items-center justify-center gap-2"
                  data-testid="upload-2d-submit"
                >
                  {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  {uploading ? `Se încarcă ${progress}%...` : "Încarcă"}
                </button>
              </>
            )}

            {history.plans.length > 0 && (
              <div className="pt-3 space-y-1.5">
                <div className="text-[10px] uppercase tracking-wider text-stone-500 font-bold">Planuri 2D încărcate</div>
                {history.plans.map(p => (
                  <div key={p.id} className="flex items-center gap-2 bg-white/[0.03] border border-white/5 rounded-lg p-2 text-xs" data-testid={`plan-row-${p.id}`}>
                    <FileText className="w-3.5 h-3.5 text-blue-400" />
                    <div className="flex-1 min-w-0">
                      <div className="text-white truncate">{p.filename || p.title}</div>
                      <div className="text-stone-500 text-[10px]">{fmtBytes(p.size_bytes)} · {new Date(p.uploaded_at).toLocaleDateString("ro-RO")}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Trimble Connect tab */}
        {tab === "trimble" && (
          <div className="space-y-3" data-testid="trimble-tab-content">
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 space-y-2">
              <div className="flex items-start gap-2">
                <Wand2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <div className="text-sm text-white font-medium">Viewer SketchUp nativ via Trimble Connect</div>
                  <p className="text-[11px] text-stone-400 leading-relaxed mt-1">
                    Clientul vede modelul în viewer-ul oficial SketchUp, direct în PropManage — cu X-Ray, layers,
                    secțiuni, măsurători nativi. Zero conversie, zero pierderi.
                  </p>
                </div>
              </div>
            </div>

            <div>
              <label className="text-[10px] uppercase text-stone-500 font-semibold flex items-center justify-between">
                <span>URL Trimble Connect</span>
                {project.trimble_embed_url && <span className="text-emerald-400 normal-case">● Setat</span>}
              </label>
              <input
                value={trimbleUrl}
                onChange={(e) => setTrimbleUrl(e.target.value)}
                placeholder="https://web.connect.trimble.com/projects/.../viewer/..."
                maxLength={2000}
                className="w-full mt-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder:text-stone-600 font-mono"
                data-testid="trimble-url-input"
              />
            </div>

            <button
              onClick={saveTrimble}
              disabled={savingTrimble}
              className="w-full py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white text-sm font-medium flex items-center justify-center gap-2"
              data-testid="trimble-save"
            >
              {savingTrimble ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              {savingTrimble ? "Se salvează…" : (project.trimble_embed_url ? "Actualizează link" : "Salvează link")}
            </button>

            <details className="bg-stone-950/50 border border-white/5 rounded-lg p-3 text-[11px] text-stone-400">
              <summary className="cursor-pointer text-stone-300 font-medium">📘 Cum obții link-ul Trimble Connect (3 pași)</summary>
              <ol className="mt-2 space-y-1.5 pl-4 list-decimal leading-relaxed">
                <li>Mergi pe <a href="https://web.connect.trimble.com/" target="_blank" rel="noreferrer" className="text-emerald-400 underline">web.connect.trimble.com</a> și loghează-te (gratuit, 10GB).</li>
                <li>Creează un proiect → urcă fișierul <code className="text-amber-300">.skp</code> → așteaptă procesarea automată.</li>
                <li>Click dreapta pe model → <strong>Share</strong> → setează <em>&quot;Anyone with link&quot;</em> → copiază URL-ul și lipește-l aici.</li>
              </ol>
            </details>
          </div>
        )}

        {err && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">{err}</div>}
      </div>
    </div>
  );
};

// ============= CLIENT CARD =============
const ClientCard = ({ client, onCreateProject, onUpload, onOpenDigitalTwin }) => {
  const meta = STATUS_META[client.status];
  return (
    <div className="bg-white/[0.03] hover:bg-white/[0.05] border border-white/10 rounded-2xl p-4 transition-colors" data-testid={`dt-client-${client.client_id}`}>
      <div className="flex items-start gap-3 mb-3">
        <div className="w-10 h-10 rounded-full bg-stone-700 flex items-center justify-center shrink-0">
          <UserIcon className="w-5 h-5 text-stone-300" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="font-semibold text-white truncate">{client.client_name}</div>
            <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border ${meta.color}`}>
              <meta.icon className="w-3 h-3 inline -mt-0.5 mr-0.5" />{meta.label}
            </span>
          </div>
          <div className="text-xs text-stone-400 truncate flex items-center gap-1.5">
            <Mail className="w-3 h-3" />{client.client_email}
          </div>
          {client.zone && (
            <div className="text-xs text-stone-500 truncate flex items-center gap-1.5">
              <MapPin className="w-3 h-3" />{client.zone.replace(/-/g, " ")}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-3 text-center">
        <div className="bg-black/30 rounded-lg p-2">
          <div className="text-[9px] uppercase tracking-wider text-stone-500">Proiecte</div>
          <div className="font-serif text-lg text-white">{client.project_count}</div>
        </div>
        <div className="bg-black/30 rounded-lg p-2">
          <div className="text-[9px] uppercase tracking-wider text-stone-500">Modele 3D</div>
          <div className="font-serif text-lg text-white">{client.model_count}</div>
        </div>
        <div className="bg-black/30 rounded-lg p-2">
          <div className="text-[9px] uppercase tracking-wider text-stone-500">Planuri 2D</div>
          <div className="font-serif text-lg text-white">{client.plan_count}</div>
        </div>
      </div>

      {client.projects.length > 0 && (
        <div className="space-y-1.5 mb-3">
          {client.projects.map(p => (
            <div key={p.id} className="bg-white/[0.02] rounded-lg p-2 flex items-center gap-2" data-testid={`dt-project-${p.id}`}>
              <Layers className="w-3.5 h-3.5 text-emerald-400" />
              <div className="flex-1 min-w-0">
                <div className="text-xs text-white truncate">{p.name}</div>
                <div className="text-[10px] text-stone-500">{p.model_count} model · {p.plan_count} plan · {p.pin_count} pin</div>
              </div>
              <button
                onClick={() => onUpload(client, p)}
                className="px-2 py-1 rounded bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 text-[11px] font-medium flex items-center gap-1"
                data-testid={`upload-files-${p.id}`}
              >
                <Upload className="w-3 h-3" />Încarcă
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        {client.status === "needs_setup" ? (
          <button
            onClick={() => onCreateProject(client)}
            className="flex-1 px-3 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-medium flex items-center justify-center gap-1.5"
            data-testid={`create-project-${client.client_id}`}
          >
            <Plus className="w-3.5 h-3.5" />Creează proiect & încarcă
          </button>
        ) : (
          <button
            onClick={() => onCreateProject(client)}
            className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-stone-300 text-xs font-medium flex items-center gap-1.5"
            data-testid={`add-project-${client.client_id}`}
          >
            <Plus className="w-3.5 h-3.5" />Proiect nou
          </button>
        )}
        <button
          onClick={() => onOpenDigitalTwin(client)}
          className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-stone-300 text-xs font-medium flex items-center gap-1.5"
          title="Deschide modulul Digital Twin (ca operator)"
          data-testid={`view-dt-${client.client_id}`}
        >
          <Eye className="w-3.5 h-3.5" />Vezi DT
        </button>
      </div>
    </div>
  );
};

// ============= UNRESOLVED PROJECTS (Historical Anchor) — single + BULK =============
// Ancorare manuală a proiectelor 3D istorice (neancorate) la o proprietate.
// ZERO auto-assign. Bulk: multi-select DOAR în cadrul aceluiași owner + preview obligatoriu + confirmare explicită.
const UnresolvedRow = ({ item, selected, onToggle, selectDisabled, onAnchored }) => {
  const [propertyId, setPropertyId] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [done, setDone] = useState(false);
  const cands = item.candidate_properties || [];

  const anchor = async () => {
    if (!propertyId) return;
    setBusy(true); setErr(null);
    try {
      await axios.patch(`${API}/digital-twin/projects/${item.id}/property`, { property_id: propertyId });
      setDone(true);
      onAnchored?.(item.id);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3 text-xs text-emerald-300 flex items-center gap-2" data-testid={`unresolved-done-${item.id}`}>
        <CheckCircle2 className="w-4 h-4" /> „{item.name}" a fost ancorat la proprietate.
      </div>
    );
  }

  return (
    <div className={`rounded-xl p-3 space-y-2 border ${selected ? "bg-emerald-500/10 border-emerald-500/30" : "bg-white/[0.03] border-white/10"}`} data-testid={`unresolved-row-${item.id}`}>
      <div className="flex items-start gap-2">
        <input
          type="checkbox"
          checked={selected}
          disabled={selectDisabled || cands.length === 0}
          onChange={() => onToggle(item)}
          className="mt-0.5 accent-emerald-500 disabled:opacity-30"
          data-testid={`unresolved-check-${item.id}`}
          title={cands.length === 0 ? "Proprietarul nu are proprietăți" : (selectDisabled ? "Selectează doar proiecte ale aceluiași proprietar" : "Selectează pentru ancorare în masă")}
        />
        <Unlink className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-sm text-white truncate">{item.name || "Proiect fără nume"}</div>
          <div className="text-[10px] text-stone-500">
            {item.owner_name} · {item.created_at ? new Date(item.created_at).toLocaleDateString("ro-RO") : "—"} · {item.model_count} model · {item.plan_count} plan
          </div>
        </div>
      </div>

      {cands.length === 0 ? (
        <div className="text-[11px] text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2" data-testid={`unresolved-no-cands-${item.id}`}>
          Proprietarul nu are nicio proprietate. Adaugă o proprietate în contul lui înainte de ancorare.
        </div>
      ) : (
        <div className="flex gap-2">
          <select
            value={propertyId}
            onChange={(e) => setPropertyId(e.target.value)}
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2.5 py-2 text-xs text-white"
            data-testid={`unresolved-select-${item.id}`}
          >
            <option value="" className="bg-stone-900">Ancorare individuală…</option>
            {cands.map((c) => (
              <option key={c.id} value={c.id} className="bg-stone-900">
                {c.name}{c.address ? ` · ${c.address}` : ""}
              </option>
            ))}
          </select>
          <button
            onClick={anchor}
            disabled={!propertyId || busy}
            className="px-3 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 text-white text-xs font-medium flex items-center gap-1.5 shrink-0"
            data-testid={`unresolved-anchor-${item.id}`}
          >
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Link2 className="w-3.5 h-3.5" />}
            Ancorează
          </button>
        </div>
      )}
      {err && <div className="text-[11px] text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">{err}</div>}
    </div>
  );
};

const PropertyPreviewCard = ({ propertyId }) => {
  const [pv, setPv] = useState(null);
  useEffect(() => {
    if (!propertyId) { setPv(null); return; }
    axios.get(`${API}/admin/digital-twin/properties/${propertyId}/preview`)
      .then((r) => setPv(r.data)).catch(() => setPv(null));
  }, [propertyId]);
  if (!propertyId) return null;
  if (!pv) return <div className="text-[11px] text-stone-500 py-2"><Loader2 className="w-3 h-3 animate-spin inline mr-1" />Se încarcă previzualizarea…</div>;
  return (
    <div className="rounded-lg bg-white/[0.04] border border-white/10 p-2.5" data-testid="bulk-property-preview">
      <div className="flex items-center gap-2">
        <div className="w-9 h-9 rounded-lg bg-emerald-500/15 flex items-center justify-center shrink-0"><MapPin className="w-4 h-4 text-emerald-300" /></div>
        <div className="min-w-0">
          <div className="text-sm text-white truncate">{pv.name}</div>
          <div className="text-[10px] text-stone-500 truncate">{pv.address || "—"}</div>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 mt-2 text-[10px] text-stone-400">
        {pv.type && <span className="px-1.5 py-0.5 rounded bg-white/5">{pv.type}</span>}
        {pv.surface != null && <span className="px-1.5 py-0.5 rounded bg-white/5">{pv.surface} m²</span>}
        {pv.rooms != null && <span className="px-1.5 py-0.5 rounded bg-white/5">{pv.rooms} camere</span>}
        {pv.health_score != null && <span className="px-1.5 py-0.5 rounded bg-white/5">Sănătate {pv.health_score}</span>}
        <span className="px-1.5 py-0.5 rounded bg-white/5">Proprietar: {pv.owner_name}</span>
      </div>
    </div>
  );
};

const UnresolvedModal = ({ onClose, onChanged }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [selected, setSelected] = useState([]); // array of items
  const [bulkProp, setBulkProp] = useState("");
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);

  const selectedOwner = selected[0]?.owner_id || null;
  const selectedCands = selected[0]?.candidate_properties || [];

  const load = async () => {
    setLoading(true); setErr(null);
    try {
      const { data } = await axios.get(`${API}/admin/digital-twin/unresolved-projects`);
      setItems(data.items || []);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const toggle = (item) => {
    setBulkResult(null);
    setSelected((arr) => {
      const exists = arr.find((x) => x.id === item.id);
      if (exists) {
        const next = arr.filter((x) => x.id !== item.id);
        if (next.length === 0) { setBulkProp(""); }
        return next;
      }
      // enforce same owner
      if (arr.length && arr[0].owner_id !== item.owner_id) return arr;
      return [...arr, item];
    });
  };

  const handleAnchored = (id) => {
    setTimeout(() => setItems((arr) => arr.filter((x) => x.id !== id)), 1200);
    setSelected((arr) => arr.filter((x) => x.id !== id));
    onChanged?.();
  };

  const runBulk = async () => {
    if (!bulkProp || selected.length === 0) return;
    setBulkBusy(true); setErr(null); setBulkResult(null);
    try {
      const { data } = await axios.post(`${API}/admin/digital-twin/bulk-anchor`, {
        project_ids: selected.map((s) => s.id),
        property_id: bulkProp,
      });
      setBulkResult(data);
      const okIds = new Set(data.results.filter((r) => r.ok).map((r) => r.project_id));
      setTimeout(() => setItems((arr) => arr.filter((x) => !okIds.has(x.id))), 1200);
      setSelected([]);
      setBulkProp("");
      onChanged?.();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setBulkBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-stone-900 border border-white/10 rounded-2xl w-full max-w-lg max-h-[90vh] flex flex-col" data-testid="unresolved-modal">
        <div className="flex items-start justify-between p-5 pb-3 border-b border-white/10">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-amber-400/90 font-semibold">Ancorare istorică</div>
            <h3 className="font-serif text-lg text-white">Proiecte 3D neancorate</h3>
            <p className="text-xs text-stone-400 mt-0.5">Leagă manual proiectele vechi de o proprietate. Bifează mai multe (același proprietar) pentru ancorare în masă. ZERO atribuire automată.</p>
          </div>
          <button onClick={onClose} data-testid="unresolved-close"><X className="w-5 h-5 text-stone-500" /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-2">
          {loading ? (
            <div className="text-center py-8 text-sm text-stone-500"><Loader2 className="w-4 h-4 animate-spin inline mr-2" />Se încarcă…</div>
          ) : err ? (
            <div className="text-center py-6 text-red-400 text-sm">{err}</div>
          ) : items.length === 0 ? (
            <div className="text-center py-8" data-testid="unresolved-empty">
              <CheckCircle2 className="w-10 h-10 text-emerald-500/60 mx-auto mb-2" />
              <p className="text-sm text-stone-300">Toate proiectele sunt ancorate. Nimic de rezolvat.</p>
            </div>
          ) : (
            <>
              <div className="text-[11px] text-stone-500">{items.length} proiecte neancorate{selectedOwner ? ` · selectezi de la ${selected[0].owner_name}` : ""}</div>
              {items.map((it) => (
                <UnresolvedRow
                  key={it.id}
                  item={it}
                  selected={!!selected.find((x) => x.id === it.id)}
                  selectDisabled={!!selectedOwner && it.owner_id !== selectedOwner}
                  onToggle={toggle}
                  onAnchored={handleAnchored}
                />
              ))}
            </>
          )}
        </div>

        {/* Persistent bulk result (stays visible after selection clears) */}
        {bulkResult && (
          <div className="mx-5 mb-3 text-[11px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2.5" data-testid="bulk-result">
            ✓ {bulkResult.anchored_count}/{bulkResult.requested} proiecte ancorate la „{bulkResult.property_name}".
          </div>
        )}

        {/* Bulk bar */}
        {selected.length > 0 && (
          <div className="border-t border-white/10 p-4 space-y-2 bg-stone-900" data-testid="bulk-anchor-bar">
            <div className="flex items-center justify-between">
              <span className="text-xs text-white font-medium">{selected.length} proiecte selectate</span>
              <button onClick={() => { setSelected([]); setBulkProp(""); }} className="text-[11px] text-stone-500 hover:text-stone-300" data-testid="bulk-clear">Anulează selecția</button>
            </div>
            <select
              value={bulkProp}
              onChange={(e) => setBulkProp(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-2.5 py-2 text-xs text-white"
              data-testid="bulk-property-select"
            >
              <option value="" className="bg-stone-900">Alege proprietatea țintă…</option>
              {selectedCands.map((c) => (
                <option key={c.id} value={c.id} className="bg-stone-900">{c.name}{c.address ? ` · ${c.address}` : ""}</option>
              ))}
            </select>
            <PropertyPreviewCard propertyId={bulkProp} />
            <button
              onClick={runBulk}
              disabled={!bulkProp || bulkBusy}
              className="w-full inline-flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 text-white text-sm font-medium"
              data-testid="bulk-anchor-confirm"
            >
              {bulkBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link2 className="w-4 h-4" />}
              Ancorează în masă ({selected.length})
            </button>
            <p className="text-[10px] text-stone-500 text-center">Confirmarea leagă toate proiectele bifate de proprietatea aleasă. Nimic nu se șterge.</p>
          </div>
        )}
      </div>
    </div>
  );
};

// ============= PROFESSIONAL REVIEW QUEUE (cross-project) =============
const ReviewQueueModal = ({ onClose, onChanged }) => {
  const [items, setItems] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [err, setErr] = useState(null);

  const load = () => {
    axios.get(`${API}/digital-twin/professional/review-queue`)
      .then((r) => setItems(r.data.items || [])).catch((e) => { setItems([]); setErr(e?.response?.data?.detail || e.message); });
  };
  useEffect(() => { load(); }, []);

  const act = async (modelId, action) => {
    setBusyId(modelId + action); setErr(null);
    try {
      await axios.post(`${API}/digital-twin/models/${modelId}/validate`, { action });
      setItems((arr) => arr.filter((x) => x.model_id !== modelId));
      onChanged?.();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-stone-900 border border-white/10 rounded-2xl w-full max-w-lg max-h-[90vh] flex flex-col" data-testid="review-queue-modal">
        <div className="flex items-start justify-between p-5 pb-3 border-b border-white/10">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-blue-400/90 font-semibold">Validare profesională</div>
            <h3 className="font-serif text-lg text-white">Coadă de validare</h3>
            <p className="text-xs text-stone-400 mt-0.5">Modele orientative (AI) trimise la validare. Confirmă → devine „Verificat profesional".</p>
          </div>
          <button onClick={onClose} data-testid="review-queue-close"><X className="w-5 h-5 text-stone-500" /></button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-2">
          {items === null ? (
            <div className="text-center py-8 text-sm text-stone-500"><Loader2 className="w-4 h-4 animate-spin inline mr-2" />Se încarcă…</div>
          ) : items.length === 0 ? (
            <div className="text-center py-8" data-testid="review-queue-empty">
              <CheckCircle2 className="w-10 h-10 text-emerald-500/60 mx-auto mb-2" />
              <p className="text-sm text-stone-300">Nimic de validat. Coada e goală.</p>
            </div>
          ) : items.map((it) => (
            <div key={it.model_id} className="rounded-xl border border-white/10 bg-white/[0.03] p-3 space-y-2" data-testid={`review-item-${it.model_id}`}>
              <div>
                <div className="text-sm text-white truncate">{it.filename}</div>
                <div className="text-[10px] text-stone-500">{it.project_name} · {it.owner_name} · cerut de {it.requested_by_name}{it.is_design_concept ? " · Concept Design" : ""}</div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => act(it.model_id, "confirm")} disabled={!!busyId}
                  className="flex-1 px-3 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 text-white text-xs font-medium flex items-center justify-center gap-1.5"
                  data-testid={`review-confirm-${it.model_id}`}>
                  {busyId === it.model_id + "confirm" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />} Validează
                </button>
                <button onClick={() => act(it.model_id, "reject")} disabled={!!busyId}
                  className="px-3 py-2 rounded-lg bg-red-500/15 hover:bg-red-500/25 text-red-200 text-xs font-medium flex items-center justify-center gap-1.5"
                  data-testid={`review-reject-${it.model_id}`}>
                  Respinge
                </button>
              </div>
            </div>
          ))}
          {err && <div className="text-xs text-red-400">{err}</div>}
        </div>
      </div>
    </div>
  );
};

// ============= MAIN VIEW =============
export const OperatorDigitalTwin = () => {
  const [items, setItems] = useState([]);
  const [counters, setCounters] = useState({ needs_setup: 0, in_progress: 0, delivered: 0, total: 0 });
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [showGrant, setShowGrant] = useState(false);
  const [creatingFor, setCreatingFor] = useState(null);
  const [uploadingFor, setUploadingFor] = useState(null); // { client, project }
  const [toast, setToast] = useState(null);
  const [showUnresolved, setShowUnresolved] = useState(false);
  const [unresolvedCount, setUnresolvedCount] = useState(0);
  const [showReviewQueue, setShowReviewQueue] = useState(false);
  const [reviewCount, setReviewCount] = useState(0);

  const loadUnresolvedCount = async () => {
    try {
      const { data } = await axios.get(`${API}/admin/digital-twin/unresolved-projects`);
      setUnresolvedCount(data.count ?? (data.items || []).length);
    } catch { /* ignore */ }
  };

  const loadReviewCount = async () => {
    try {
      const { data } = await axios.get(`${API}/digital-twin/professional/review-queue`);
      setReviewCount(data.count ?? (data.items || []).length);
    } catch { /* ignore */ }
  };

  const load = async () => {
    setLoading(true); setErr(null);
    try {
      const { data } = await axios.get(`${API}/operator/digital-twin/clients-queue`, { params: { status: filter } });
      setItems(data.items || []);
      setCounters(data.counters || {});
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load();   }, [filter]);
  useEffect(() => { loadUnresolvedCount(); loadReviewCount(); }, []);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };

  const onCreateProject = (client) => setCreatingFor(client);
  const onProjectCreated = (data) => {
    showToast(`✓ Proiect „${data.name}" creat. Acum încarcă fișierele.`);
    setUploadingFor({ client: creatingFor, project: data });
    setCreatingFor(null);
    load();
  };
  const onUpload = (client, project) => setUploadingFor({ client, project });
  const onUploaded = () => { showToast("✓ Fișier încărcat. Vizibil pentru client."); load(); };
  const onOpenDigitalTwin = () => { window.location.href = "/digital-twin"; };

  const filterPills = [
    { id: "all", label: "Toți", count: counters.total },
    { id: "needs_setup", label: "Setup necesar", count: counters.needs_setup },
    { id: "in_progress", label: "În lucru", count: counters.in_progress },
    { id: "delivered", label: "Livrat", count: counters.delivered },
  ];

  return (
    <div className="space-y-4" data-testid="operator-digital-twin">
      {/* Header actions */}
      <div className="glass-strong rounded-3xl p-5">
        <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-400/80 font-semibold">Digital Twin Pro · Operator</div>
            <h2 className="font-serif text-xl text-white">Clienți cu acces 3D</h2>
            <p className="text-xs text-stone-400 mt-0.5">Acordă acces, creează proiecte, încarcă modele .glb/.gltf/.skp și planuri PDF 2D.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowReviewQueue(true)}
              className="relative px-3 py-2 rounded-lg bg-blue-500/15 hover:bg-blue-500/25 text-blue-200 text-xs font-medium flex items-center gap-1.5"
              data-testid="op-review-queue-btn"
              title="Validează modelele orientative (AI) trimise la validare"
            >
              <ShieldCheck className="w-3.5 h-3.5" />Coadă validare
              {reviewCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-blue-500 text-white text-[10px] font-bold leading-none" data-testid="op-review-badge">
                  {reviewCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setShowUnresolved(true)}
              className="relative px-3 py-2 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-200 text-xs font-medium flex items-center gap-1.5"
              data-testid="op-unresolved-btn"
              title="Ancorează proiectele 3D vechi (neancorate) la o proprietate"
            >
              <Unlink className="w-3.5 h-3.5" />Proiecte neancorate
              {unresolvedCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-amber-500 text-stone-900 text-[10px] font-bold leading-none" data-testid="op-unresolved-badge">
                  {unresolvedCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setShowGrant(true)}
              className="px-3 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-medium flex items-center gap-1.5"
              data-testid="op-grant-access-btn"
            >
              <ShieldCheck className="w-3.5 h-3.5" />Acordă acces DT
            </button>
          </div>
        </div>

        {/* Filter pills */}
        <div className="flex flex-wrap gap-2">
          {filterPills.map(p => (
            <button
              key={p.id}
              onClick={() => setFilter(p.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5 ${
                filter === p.id ? "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40" : "bg-white/5 text-stone-400 hover:text-white"
              }`}
              data-testid={`dt-filter-${p.id}`}
            >
              {p.label}
              <span className="px-1.5 py-0.5 rounded-full bg-stone-950 text-[10px]">{p.count || 0}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center py-12 text-sm text-stone-500"><Loader2 className="w-4 h-4 animate-spin inline mr-2" />Se încarcă...</div>
      ) : err ? (
        <div className="text-center py-8 text-red-400 text-sm">{err}</div>
      ) : items.length === 0 ? (
        <div className="glass-strong rounded-3xl p-12 text-center" data-testid="op-dt-empty">
          <Box className="w-12 h-12 text-stone-600 mx-auto mb-3" />
          <h3 className="font-serif text-xl text-white mb-2">Niciun client cu Digital Twin Pro</h3>
          <p className="text-sm text-stone-400 max-w-md mx-auto">
            Acordă accesul unui client folosind butonul „Acordă acces DT" de mai sus. După acordare, vei putea crea proiectul și încărca fișierele.
          </p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-3">
          {items.map(c => (
            <ClientCard
              key={c.client_id}
              client={c}
              onCreateProject={onCreateProject}
              onUpload={onUpload}
              onOpenDigitalTwin={onOpenDigitalTwin}
            />
          ))}
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-[70] px-4 py-2 rounded-full bg-emerald-500 text-white text-sm shadow-2xl" data-testid="op-dt-toast">
          {toast}
        </div>
      )}

      {showGrant && <GrantAccessModal onClose={() => setShowGrant(false)} onGranted={load} />}
      {showUnresolved && (
        <UnresolvedModal
          onClose={() => setShowUnresolved(false)}
          onChanged={() => { loadUnresolvedCount(); load(); }}
        />
      )}
      {showReviewQueue && (
        <ReviewQueueModal
          onClose={() => setShowReviewQueue(false)}
          onChanged={() => { loadReviewCount(); }}
        />
      )}
      {creatingFor && (
        <CreateProjectModal client={creatingFor} onClose={() => setCreatingFor(null)} onCreated={onProjectCreated} />
      )}
      {uploadingFor && (
        <UploadFilesModal
          client={uploadingFor.client}
          project={uploadingFor.project}
          onClose={() => setUploadingFor(null)}
          onUploaded={onUploaded}
        />
      )}
    </div>
  );
};

export default OperatorDigitalTwin;
