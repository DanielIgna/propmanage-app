// Digital Twin page — Phase C MVP project list + viewer launcher.
import React, { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { Box, Plus, Lock, Eye, Trash2, ArrowLeft, Sparkles, ExternalLink, Upload, FileBox, X, Layers, BellRing, Wand2, Loader2 } from "lucide-react";
import { API } from "./DashShared";
import DigitalTwinViewer from "../components/DigitalTwinViewer";
import { PbContextBanner } from "../components/pb/PbEverywhere";
import DigitalTwinPlans from "../components/DigitalTwinPlans";
import SentReportsDashboard from "../components/SentReportsDashboard";

const ProjectCard = ({ p, onOpen, onDelete, onUpload, onPlans, onAiGenerate, aiBusy }) => {
  const anchored = !!p.property_id;
  return (
  <div className="group relative rounded-2xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.04] p-5 transition-colors" data-testid={`dt-project-${p.id}`}>
    <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-t-2xl opacity-50 group-hover:opacity-100 transition-opacity" />
    <div className="flex items-start gap-3 mb-3">
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 flex items-center justify-center shrink-0">
        <Box className="w-5 h-5 text-emerald-300" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-base text-white truncate">{p.name}</div>
        <div className="text-[11px] text-stone-500">{p.owner_name} · {new Date(p.created_at).toLocaleDateString("ro-RO")}</div>
      </div>
    </div>
    {p.description && <p className="text-xs text-stone-400 line-clamp-2 mb-3">{p.description}</p>}
    <div className="flex gap-3 text-[11px] text-stone-500 mb-4 flex-wrap">
      <span>📌 {p.pin_count || 0} pin-uri</span>
      <span>📁 {p.model_count || 0} modele</span>
      <span>📐 {p.plan_count || 0} planuri 2D</span>
      {p.model_url ? <span className="text-emerald-400">● Model încărcat</span> : <span className="text-amber-400">● Demo procedural</span>}
      {anchored
        ? <span className="text-cyan-400">● Ancorat la proprietate</span>
        : <span className="text-stone-500">○ Neancorat</span>}
    </div>
    <div className="flex gap-2 mb-2">
      <button
        onClick={() => onOpen(p)}
        className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 text-xs rounded-full bg-[#d4ff3a] text-black font-medium hover:bg-[#c5f02e] transition-colors"
        data-testid={`dt-open-${p.id}`}
      >
        <Eye className="w-3.5 h-3.5" /> Deschide viewer
      </button>
      <button
        onClick={() => onPlans(p)}
        className="px-3 py-2 text-xs rounded-full border border-white/10 text-stone-300 hover:bg-white/5"
        title="Planuri 2D (PDF)"
        data-testid={`dt-plans-${p.id}`}
      >
        <Layers className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={() => onUpload(p)}
        className="px-3 py-2 text-xs rounded-full border border-white/10 text-stone-300 hover:bg-white/5"
        title="Încarcă model 3D (.glb/.gltf/.skp/.dae/.obj/.fbx/.stl/.ply)"
        data-testid={`dt-upload-${p.id}`}
      >
        <Upload className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={() => onDelete(p)}
        className="px-3 py-2 text-xs rounded-full border border-white/10 text-stone-400 hover:bg-red-500/10 hover:text-red-300 hover:border-red-500/30"
        data-testid={`dt-delete-${p.id}`}
      >
        <Trash2 className="w-3.5 h-3.5" />
      </button>
    </div>
    <button
      onClick={() => anchored && onAiGenerate(p)}
      disabled={!anchored || aiBusy}
      title={anchored ? "Generează un model 3D orientativ (AI, inferred)" : "Ancorează proiectul la o proprietate pentru a genera modelul AI"}
      className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-xs rounded-full border border-violet-500/30 bg-violet-500/10 text-violet-200 hover:bg-violet-500/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      data-testid={`dt-ai-generate-${p.id}`}
    >
      {aiBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wand2 className="w-3.5 h-3.5" />}
      {aiBusy ? "Se generează…" : "Generează AI 3D (orientativ)"}
    </button>
  </div>
  );
};

// =============== UPLOAD MODAL ===============
const DT_ALLOWED_EXTS = ["glb", "gltf", "skp", "dae", "obj", "fbx", "stl", "ply"];
const DT_CONVERTING = ["pending", "uploading", "converting", "downloading"];

const UploadModal = ({ project, onClose, onUploaded }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [err, setErr] = useState(null);
  const [conv, setConv] = useState(null); // { model_id, status, percent, error }
  const dropRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const onDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer?.files?.[0];
    if (f) acceptFile(f);
  };
  const acceptFile = (f) => {
    const ext = f.name.toLowerCase().split(".").pop();
    if (!DT_ALLOWED_EXTS.includes(ext)) {
      setErr(`Format invalid: .${ext}. Acceptăm .glb / .gltf / .skp / .dae / .obj / .fbx / .stl / .ply.`);
      return;
    }
    if (f.size > 200 * 1024 * 1024) {
      setErr(`Fișier prea mare (${(f.size / (1024 * 1024)).toFixed(1)} MB). Maxim 200 MB.`);
      return;
    }
    setErr(null);
    setFile(f);
  };

  const pollConversion = (modelId) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await axios.get(`${API}/digital-twin/conversions/${modelId}/status`);
        setConv({ model_id: modelId, status: data.status, percent: data.percent || 0, error: data.error });
        if (!DT_CONVERTING.includes(data.status)) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }, 5000);
  };

  const submit = async () => {
    if (!file) return;
    setUploading(true);
    setErr(null);
    setProgress(0);
    setConv(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const xhr = new XMLHttpRequest();
      const done = await new Promise((resolve, reject) => {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText));
          else {
            try { reject(new Error(JSON.parse(xhr.responseText).detail || xhr.statusText)); }
            catch { reject(new Error(xhr.statusText || "Upload error")); }
          }
        };
        xhr.onerror = () => reject(new Error("Network error"));
        xhr.withCredentials = true;
        xhr.open("POST", `${API}/digital-twin/projects/${project.id}/upload`);
        xhr.send(fd);
      });
      onUploaded(done);
      // If the backend queued a conversion (.dae/.obj/...), keep the modal open and poll.
      if (done.conversion_status && DT_CONVERTING.includes(done.conversion_status)) {
        setConv({ model_id: done.id, status: done.conversion_status, percent: done.conversion_percent || 0 });
        pollConversion(done.id);
      } else if (done.conversion_status === "unsupported") {
        // .skp — stored intact & downloadable; show the clear note, keep modal open.
        setConv({ model_id: done.id, status: "unsupported", note: done.conversion_note, url: done.url });
      } else {
        onClose();
      }
    } catch (e) {
      setErr(e.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-stone-900 border border-white/10 rounded-2xl p-6 w-full max-w-lg"
        data-testid="dt-upload-modal"
      >
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="font-serif text-xl text-white">Încarcă model 3D</h3>
            <p className="text-xs text-stone-400 mt-0.5">Proiect: <strong>{project.name}</strong></p>
          </div>
          <button onClick={onClose} className="text-stone-500 hover:text-white" data-testid="dt-upload-close"><X className="w-5 h-5" /></button>
        </div>

        <div
          ref={dropRef}
          onDragOver={(e) => e.preventDefault()}
          onDrop={onDrop}
          className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${
            file ? "border-emerald-500/40 bg-emerald-500/5" : "border-white/15 hover:border-white/30"
          }`}
          data-testid="dt-upload-dropzone"
        >
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileBox className="w-7 h-7 text-emerald-400" />
              <div className="text-left">
                <div className="text-sm text-white truncate max-w-[280px]">{file.name}</div>
                <div className="text-xs text-stone-500">{(file.size / (1024 * 1024)).toFixed(1)} MB</div>
              </div>
              <button onClick={() => setFile(null)} className="text-stone-500 hover:text-red-400" data-testid="dt-upload-clear">
                <X className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <>
              <Upload className="w-8 h-8 text-stone-500 mx-auto mb-2" />
              <div className="text-sm text-stone-300 mb-1">Trage fișierul aici sau</div>
              <label className="inline-block px-4 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-xs text-white cursor-pointer">
                alege un fișier
                <input
                  type="file"
                  accept=".glb,.gltf,.skp,.dae,.obj,.fbx,.stl,.ply"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && acceptFile(e.target.files[0])}
                  data-testid="dt-upload-input"
                />
              </label>
              <p className="text-[10px] text-stone-500 mt-3 leading-relaxed">
                <strong className="text-emerald-400">.glb / .gltf</strong> — vizualizabil instant ·{" "}
                <strong className="text-amber-400">.dae / .obj / .fbx / .stl / .ply</strong> — auto-conversie ·{" "}
                <strong className="text-stone-400">.skp</strong> — SketchUp (stocat & descărcabil) · max 200 MB
              </p>
            </>
          )}
        </div>

        {uploading && (
          <div className="mt-3" data-testid="dt-upload-progress">
            <div className="flex justify-between text-xs text-stone-400 mb-1">
              <span>Se încarcă...</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
        )}

        {err && <div className="mt-3 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">{err}</div>}

        {conv && (
          <div className="mt-3 rounded-xl bg-white/[0.03] border border-white/10 p-3" data-testid="dt-upload-conversion">
            {DT_CONVERTING.includes(conv.status) ? (
              <>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="text-emerald-300 flex items-center gap-1.5">
                    <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    Se convertește în .glb…
                  </span>
                  <span className="text-stone-400 font-mono">{conv.percent}%</span>
                </div>
                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-amber-500 via-emerald-500 to-emerald-400 transition-all" style={{ width: `${conv.percent}%` }} />
                </div>
                <p className="text-[10px] text-stone-500 mt-1.5">Poți închide — conversia continuă în fundal.</p>
              </>
            ) : conv.status === "completed" ? (
              <div className="text-xs text-emerald-300 flex items-center gap-1.5">✓ Convertit — modelul .glb e gata de vizualizare.</div>
            ) : conv.status === "failed" ? (
              <div className="text-xs text-red-300">⚠️ Conversia a eșuat: {conv.error || "eroare necunoscută"}. Fișierul rămâne descărcabil.</div>
            ) : conv.status === "unsupported" ? (
              <div className="space-y-2" data-testid="dt-upload-skp-note">
                <div className="text-xs text-amber-200 leading-relaxed">
                  📦 {conv.note || "Fișier SketchUp stocat intact și descărcabil. Nu poate fi convertit automat pe server. Exportă .glb/.gltf/.dae din SketchUp pentru randare în viewer."}
                </div>
                {conv.url && (
                  <a
                    href={`${process.env.REACT_APP_BACKEND_URL}${conv.url}`}
                    target="_blank" rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-full bg-amber-500/20 hover:bg-amber-500/30 text-amber-100"
                    data-testid="dt-skp-download"
                  >
                    <FileBox className="w-3.5 h-3.5" /> Descarcă .skp
                  </a>
                )}
              </div>
            ) : (
              <div className="text-xs text-stone-400">Stocat. Format nevizualizabil în browser — descărcabil din proiect.</div>
            )}
          </div>
        )}

        <div className="mt-4 rounded-xl bg-white/[0.03] border border-white/5 p-3 text-[11px] text-stone-400 leading-relaxed">
          <strong className="text-stone-300">🛠️ Formate 3D acceptate.</strong> Încarcă direct — le gestionăm noi:
          <ul className="mt-1 space-y-0.5 list-disc list-inside">
            <li><strong className="text-emerald-400">.glb / .gltf</strong> — vizualizabil instant în viewer</li>
            <li><strong className="text-amber-400">.dae / .obj / .fbx / .stl / .ply</strong> — auto-conversie server-side în .glb</li>
            <li><strong>.skp</strong> (SketchUp) — stocat intact & descărcabil; exportă .glb/.gltf/.dae din SketchUp pentru randare, sau vezi nativ în Trimble Connect</li>
          </ul>
        </div>

        <div className="mt-4 flex gap-2">
          <button onClick={onClose} className="flex-1 px-3 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-stone-300" data-testid="dt-upload-cancel">
            {conv ? "Închide" : "Anulează"}
          </button>
          <button
            onClick={submit}
            disabled={!file || uploading}
            className="flex-1 px-3 py-2 text-sm rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-medium"
            data-testid="dt-upload-submit"
          >
            {uploading ? "Se încarcă..." : "Încarcă model"}
          </button>
        </div>
      </div>
    </div>
  );
};

const CreateModal = ({ onClose, onCreated }) => {
  const [form, setForm] = useState({ name: "", description: "", model_url: "" });
  const [properties, setProperties] = useState([]);
  const [propertyId, setPropertyId] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await axios.get(`${API}/properties`);
        const list = Array.isArray(data) ? data : (data?.items || []);
        setProperties(list);
        if (list.length === 1) setPropertyId(list[0].id);
      } catch {
        setProperties([]);
      }
    })();
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const { data } = await axios.post(`${API}/digital-twin/projects`, {
        name: form.name.trim(),
        description: form.description.trim(),
        model_url: form.model_url.trim() || null,
        property_id: propertyId || null,
      });
      onCreated(data);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <form
        onSubmit={submit}
        onClick={(e) => e.stopPropagation()}
        className="bg-stone-900 border border-white/10 rounded-2xl p-6 w-full max-w-md space-y-4"
        data-testid="dt-create-modal"
      >
        <div>
          <h3 className="font-serif text-xl text-white mb-1">Proiect Digital Twin nou</h3>
          <p className="text-xs text-stone-400">Adaugă un model 3D (glTF/GLB direct URL) sau lasă gol pentru a folosi modelul demo.</p>
        </div>
        <div>
          <label className="text-xs text-stone-400 block mb-1">Nume proiect</label>
          <input
            required
            minLength={2}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Ex: Hillside House Sannicolau"
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            data-testid="dt-create-name"
          />
        </div>
        {properties.length > 0 && (
          <div>
            <label className="text-xs text-stone-400 block mb-1">Proprietate</label>
            <select
              required
              value={propertyId}
              onChange={(e) => setPropertyId(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
              data-testid="dt-create-property"
            >
              <option value="">Alege proprietatea…</option>
              {properties.map((p) => (
                <option key={p.id} value={p.id} className="bg-stone-900">
                  {p.name || p.address || p.id}
                </option>
              ))}
            </select>
            <p className="text-[10px] text-stone-500 mt-1">
              Twin-ul 3D se ancorează de această proprietate (camere, active, documente, istoric).
            </p>
          </div>
        )}
        <div>
          <label className="text-xs text-stone-400 block mb-1">Descriere (opțional)</label>
          <textarea
            rows={2}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            data-testid="dt-create-desc"
          />
        </div>
        <div>
          <label className="text-xs text-stone-400 block mb-1">
            URL model glTF/GLB (opțional) <span className="text-stone-600">— Phase B upload vine mai târziu</span>
          </label>
          <input
            type="url"
            value={form.model_url}
            onChange={(e) => setForm({ ...form, model_url: e.target.value })}
            placeholder="https://.../model.glb"
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            data-testid="dt-create-url"
          />
          <p className="text-[10px] text-stone-500 mt-1">
            Lasă gol → folosește modelul demo public Khronos Sponza (interior arhitectural).
          </p>
        </div>
        {err && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">{err}</div>}
        <div className="flex gap-2 pt-1">
          <button type="button" onClick={onClose} className="flex-1 px-3 py-2 text-sm rounded-lg bg-white/5 text-stone-300 hover:bg-white/10">
            Anulează
          </button>
          <button
            type="submit"
            disabled={busy}
            className="flex-1 px-3 py-2 text-sm rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white font-medium"
            data-testid="dt-create-submit"
          >
            {busy ? "Se creează..." : "Creează proiect"}
          </button>
        </div>
      </form>
    </div>
  );
};

const LockedScreen = ({ onRequest, tierLabel }) => (
  <div className="min-h-screen bg-stone-950 text-white flex items-center justify-center px-4">
    <div className="max-w-md text-center" data-testid="dt-locked-screen">
      <div className="w-16 h-16 rounded-2xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center mx-auto mb-4">
        <Lock className="w-7 h-7 text-amber-400" />
      </div>
      <h1 className="font-serif text-3xl mb-2">Digital Twin Advanced</h1>
      {tierLabel && (
        <div className="inline-block text-[10px] font-black uppercase tracking-[0.16em] text-amber-300 px-2 py-0.5 rounded-full bg-amber-500/10 mb-2">
          Planul tău: {tierLabel} · Funcție blocată
        </div>
      )}
      <p className="text-stone-400 mb-6 leading-relaxed">
        Poți vedea ce este Digital Twin, dar pentru editarea avansată (pin-uri 3D, tape measure, colaborare cu specialiști) trebuie să activezi planul potrivit.
      </p>
      <div className="space-y-2 mb-6 text-sm text-stone-400 text-left max-w-sm mx-auto">
        <Feat>Pereți cu textură, albi, la roșu, transparenți (X-Ray)</Feat>
        <Feat>Layer toggle: AR_PERETI, AR_USI, AR_STALPI etc.</Feat>
        <Feat>Pin-uri 3D cu thread comentarii și roluri</Feat>
        <Feat>Colaborare client / specialist / arhitect</Feat>
        <Feat>Tape Measure, Section Plane, Camera tours</Feat>
      </div>
      <button
        onClick={onRequest}
        className="px-6 py-3 rounded-full bg-[#d4ff3a] text-black font-semibold hover:bg-[#c5f02e]"
        data-testid="dt-cta-pricing"
      >
        <Sparkles className="w-4 h-4 inline mr-2" /> Vezi planurile PropManage
      </button>
      <p className="text-xs text-stone-600 mt-4">
        Digital Twin Advanced este inclus în planul Pro și mai sus. Basic acoperă House Health.
      </p>
    </div>
  </div>
);

const Feat = ({ children }) => (
  <div className="flex items-start gap-2 px-3 py-1.5 rounded-lg bg-white/[0.02] border border-white/5">
    <span className="text-stone-300">{children}</span>
  </div>
);

export default function DigitalTwinPage() {
  const [sub, setSub] = useState(null);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openCreate, setOpenCreate] = useState(false);
  const [viewing, setViewing] = useState(null);
  const [uploadingTo, setUploadingTo] = useState(null);
  const [plansFor, setPlansFor] = useState(null);
  const [showSentReports, setShowSentReports] = useState(false);
  const [pendingReportsCount, setPendingReportsCount] = useState(0);
  const [aiBusyId, setAiBusyId] = useState(null);
  const [toast, setToast] = useState(null);
  useEffect(() => { import("../lib/analytics").then(({ trackIntent }) => trackIntent("twin_viewed")).catch(() => {}); }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const subRes = await axios.get(`${API}/digital-twin/subscription`);
      setSub(subRes.data);
      if (subRes.data.active) {
        const pr = await axios.get(`${API}/digital-twin/projects`);
        setProjects(pr.data.items || []);
        // Load pending reports count for the badge
        try {
          const sr = await axios.get(`${API}/digital-twin/reports/sent`, { params: { status: "pending" } });
          setPendingReportsCount(sr.data?.counters?.pending || 0);
        } catch {/* ignore */}
      }
    } catch {/* unauth handled by interceptor */} finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  const handleDelete = async (p) => {
    if (!window.confirm(`Șterge proiectul "${p.name}" și toate pin-urile?`)) return;
    try {
      await axios.delete(`${API}/digital-twin/projects/${p.id}`);
      setProjects((arr) => arr.filter((x) => x.id !== p.id));
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    }
  };

  const requestAccess = () => {
    // Route unificată către planul PropManage (Task 2 /pricing)
    window.location.href = "/pricing";
  };

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(null), 4000); };

  const handleAiGenerate = async (p) => {
    if (!p.property_id) { showToast("Ancorează proiectul la o proprietate întâi."); return; }
    setAiBusyId(p.id);
    try {
      const { data } = await axios.post(`${API}/digital-twin/projects/${p.id}/ai-generate`);
      setProjects((arr) => arr.map((x) =>
        x.id === p.id ? { ...x, model_url: data.url || x.model_url, model_count: (x.model_count || 0) + 1 } : x
      ));
      showToast("✓ Model AI orientativ generat (inferred, neverificat).");
    } catch (e) {
      showToast(e?.response?.data?.detail || e.message || "Generarea AI a eșuat.");
    } finally {
      setAiBusyId(null);
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-stone-950 text-stone-400 flex items-center justify-center text-sm">Se încarcă...</div>;
  }
  if (!sub?.active) return <LockedScreen onRequest={requestAccess} tierLabel={sub?.tier_label} />;

  if (showSentReports) {
    return (
      <SentReportsDashboard
        onClose={() => { setShowSentReports(false); loadAll(); }}
        onOpenProject={(projectId) => {
          const p = projects.find((x) => x.id === projectId);
          if (p) {
            setShowSentReports(false);
            setViewing(p);
          }
        }}
      />
    );
  }

  if (plansFor) {
    return (
      <DigitalTwinPlans
        projectId={plansFor.id}
        projectName={plansFor.name}
        projectModelUrl={plansFor.model_url}
        onClose={() => setPlansFor(null)}
      />
    );
  }

  if (viewing) {
    return (
      <DigitalTwinViewer
        projectId={viewing.id}
        modelUrl={viewing.model_url}
        projectName={viewing.name}
        onClose={() => setViewing(null)}
        onOpenPlans={() => { setPlansFor(viewing); setViewing(null); }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-stone-950 text-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-stone-400 hover:text-white mb-6">
          <ArrowLeft className="w-4 h-4" /> Înapoi
        </Link>
        <header className="flex items-center justify-between mb-8 flex-wrap gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-400/80 font-semibold mb-1">Premium · Digital Twin Pro</div>
            <h1 className="font-serif text-4xl">Proiectele tale 3D</h1>
            <p className="text-sm text-stone-400 mt-1">Vizualizare BIM colaborativă · X-Ray · pin-uri · workflow inter-specialități</p>
          </div>          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSentReports(true)}
              className="relative inline-flex items-center gap-2 px-3 py-2 rounded-full bg-white/5 hover:bg-white/10 text-stone-300 text-sm"
              data-testid="dt-sent-reports-btn"
              title="Răspunsuri așteptate la rapoarte"
            >
              <BellRing className="w-4 h-4" /> Răspunsuri
              {pendingReportsCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-amber-500 text-stone-900 text-[10px] font-bold leading-none" data-testid="dt-sent-reports-badge">
                  {pendingReportsCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setOpenCreate(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#d4ff3a] text-black font-medium hover:bg-[#c5f02e]"
              data-testid="dt-new-project-btn"
            >
              <Plus className="w-4 h-4" /> Proiect nou
            </button>
          </div>
        </header>

        <PbContextBanner surface="digital_twin" />

        {projects.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/10 p-12 text-center" data-testid="dt-empty-state">
            <Box className="w-12 h-12 text-stone-600 mx-auto mb-3" />
            <h2 className="text-lg text-white mb-1">Niciun proiect încă</h2>
            <p className="text-sm text-stone-400 mb-4">Creează primul tău Digital Twin. Poți folosi un URL .glb propriu sau modelul demo.</p>
            <button
              onClick={() => setOpenCreate(true)}
              className="px-4 py-2 rounded-full bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium"
              data-testid="dt-empty-create-btn"
            >
              Creează primul proiect
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="dt-projects-grid">
            {projects.map((p) => (
              <ProjectCard key={p.id} p={p} onOpen={setViewing} onDelete={handleDelete} onUpload={setUploadingTo} onPlans={setPlansFor} onAiGenerate={handleAiGenerate} aiBusy={aiBusyId === p.id} />
            ))}
          </div>
        )}

        <div className="mt-10 rounded-2xl border border-white/5 bg-white/[0.02] p-5 text-xs text-stone-500">
          <div className="flex items-center gap-2 mb-2">
            <ExternalLink className="w-3.5 h-3.5" />
            <strong className="text-stone-300">Phase C MVP — what works now</strong>
          </div>
          <ul className="space-y-1 list-disc list-inside pl-1">
            <li>Viewer 3D web cu Three.js + react-three-fiber</li>
            <li>5 face styles: Shaded · White · X-Ray · Wireframe · Monochrome</li>
            <li>Auto-detectare layers/tags din numele mesh-urilor (AR_PERETI, AR_USI etc.)</li>
            <li>Layer toggle individual per categorie</li>
            <li>OrbitControls (rotate · zoom · pan) cu damping</li>
          </ul>
          <div className="mt-3 text-stone-600">
            Next: upload .skp/.ifc + conversie server-side (Phase B), Tape Measure + Section Plane (Phase D), Pin UI cu thread (Phase E).
          </div>
        </div>
      </div>

      {openCreate && (
        <CreateModal
          onClose={() => setOpenCreate(false)}
          onCreated={(p) => {
            setProjects((arr) => [p, ...arr]);
            setOpenCreate(false);
            setViewing(p);
          }}
        />
      )}

      {uploadingTo && (
        <UploadModal
          project={uploadingTo}
          onClose={() => setUploadingTo(null)}
          onUploaded={(model) => {
            // Patch the project with the new model_url + increment count.
            // The modal stays open if a conversion is queued (it closes itself).
            setProjects((arr) => arr.map((x) =>
              x.id === uploadingTo.id
                ? { ...x, model_url: model.url || x.model_url, model_count: (x.model_count || 0) + 1 }
                : x
            ));
          }}
        />
      )}

      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[70] px-4 py-2 rounded-full bg-stone-800 border border-white/10 text-white text-sm shadow-2xl" data-testid="dt-toast">
          {toast}
        </div>
      )}
    </div>
  );
}
