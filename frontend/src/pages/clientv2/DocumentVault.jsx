import React, { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import {
  FileText, Upload, X, Search, Download, Trash2, Pencil, ShieldCheck, Sparkles,
  ChevronRight, ChevronDown, Image as ImageIcon, FileUp, BadgeCheck, History,
  Camera, FolderOpen,
} from "lucide-react";
import { API } from "../DashShared";
import { formatApiError } from "../../auth";
import { GREEN, Sheet, CTA } from "./ui";
import { StorageUsageCard } from "../../components/StorageUsageCard";

const CAT_ICONS = { foto: ImageIcon, video: ImageIcon };
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString("ro-RO", { day: "numeric", month: "short", year: "numeric" }) : "—");
const fmtSize = (b) => (b > 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);
const SOURCE_LABEL = { owner_upload: "Declarat de proprietar", specialist: "Adăugat de specialist", platform: "Verificat de platformă" };

// ── Celebrarea primului document — moment semnătură (EO CX-2) ────────────────
const MemoryCelebration = ({ score, onClose }) => (
  <div className="fixed inset-0 z-[90] flex items-center justify-center p-6" data-testid="memory-celebration"
    style={{ background: "rgba(6, 40, 22, 0.92)", backdropFilter: "blur(8px)" }}>
    <div className="max-w-sm w-full text-center cv2-fade">
      <div className="mx-auto w-20 h-20 rounded-full flex items-center justify-center animate-bounce"
        style={{ background: "linear-gradient(135deg, #a3e635, #d4ff3a)" }}>
        <Sparkles className="w-9 h-9 text-black" />
      </div>
      <h2 className="mt-6 text-3xl font-black text-white leading-tight">Casa ta are acum memorie.</h2>
      <p className="mt-3 text-sm text-lime-100/80">Istoria proprietății tale a început oficial. Fiecare document rămâne salvat permanent în cartea casei.</p>
      {score != null && (
        <div className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 text-white text-sm font-bold" data-testid="celebration-score">
          <BadgeCheck className="w-4 h-4 text-[#d4ff3a]" /> Casa ta e {score}% documentată
        </div>
      )}
      <button onClick={onClose} data-testid="celebration-continue"
        className="mt-7 w-full py-4 rounded-full text-base font-black text-black active:scale-[0.98] transition-transform"
        style={{ background: "#d4ff3a" }}>
        Continuă
      </button>
    </div>
  </div>
);

// ── Upload sheet: doar categoria e obligatorie (progressive disclosure) ─────
const UploadSheet = ({ prop, presetCategory, onClose, onDone }) => {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState(presetCategory || "");
  const [more, setMore] = useState(false);
  const [meta, setMeta] = useState({ building_system: "", room: "", doc_date: "", company: "", warranty_end: "", tags: "", notes: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [cats, setCats] = useState([]);
  const [showSource, setShowSource] = useState(false);
  const galleryRef = useRef(null);
  const cameraRef = useRef(null);
  const isTouch = typeof window !== "undefined" && window.matchMedia?.("(pointer: coarse)").matches;
  const openPicker = () => (isTouch ? setShowSource(true) : galleryRef.current?.click());

  useEffect(() => {
    axios.get(`${API}/properties/${prop.id}/documents`).then(r => setCats(r.data.categories || [])).catch(() => {});
  }, [prop.id]);

  const pick = (f) => {
    if (!f) return;
    setFile(f);
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
    if (!category && f.type.startsWith("image/")) setCategory("foto");
  };

  const submit = () => {
    if (!file || !category) return;
    setBusy(true); setErr("");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("title", title);
    fd.append("category", category);
    Object.entries(meta).forEach(([k, v]) => v && fd.append(k, v));
    axios.post(`${API}/properties/${prop.id}/documents`, fd)
      .then(({ data }) => onDone(data))
      .catch(e => { setErr(formatApiError(e)); setBusy(false); });
  };

  return (
    <Sheet title="Adaugă în cartea casei" onClose={onClose} testid="vault-upload-sheet">
      {/* BUGFIX-001: inputurile sunt frați ai butonului (input în button = HTML invalid, tap mort pe mobil) */}
      <input ref={galleryRef} type="file" className="hidden" data-testid="vault-file-input"
        accept=".pdf,.jpg,.jpeg,.png,.webp,.gif,.heic,.mp4,.mov" onChange={e => { pick(e.target.files?.[0]); e.target.value = ""; }} />
      <input ref={cameraRef} type="file" className="hidden" data-testid="vault-camera-input"
        accept="image/*" capture="environment" onChange={e => { pick(e.target.files?.[0]); e.target.value = ""; }} />
      <button type="button" onClick={openPicker} data-testid="vault-file-pick"
        className={`w-full rounded-3xl border-2 border-dashed p-6 text-center transition-colors ${file ? "border-[#34C759] bg-[#F0FBF4]" : "border-slate-200 hover:border-slate-300"}`}>
        <FileUp className="w-7 h-7 mx-auto" style={{ color: file ? GREEN : "#94a3b8" }} />
        <div className="mt-2 text-sm font-bold text-slate-700" data-testid="vault-file-name">
          {file ? file.name : "Alege fișierul"}
        </div>
        <div className="mt-0.5 text-[11px] text-slate-400">{file ? fmtSize(file.size) : "PDF, poze, planuri, facturi — max. 25MB"}</div>
      </button>

      {showSource && (
        <div className="fixed inset-0 z-[60] flex items-end sm:items-center justify-center bg-black/40" onClick={() => setShowSource(false)} data-testid="vault-source-sheet">
          <div className="w-full sm:max-w-md bg-white rounded-t-3xl sm:rounded-3xl p-4" style={{ paddingBottom: "calc(1rem + env(safe-area-inset-bottom, 0px))" }} onClick={e => e.stopPropagation()}>
            <div className="mx-auto w-10 h-1 rounded-full bg-slate-200 mb-3 sm:hidden" />
            <div className="text-sm font-black text-slate-900 px-1 pb-2">De unde adaugi documentul?</div>
            <button type="button" data-testid="vault-source-camera"
              onClick={() => { cameraRef.current?.click(); setShowSource(false); }}
              className="w-full flex items-center gap-3 p-4 rounded-2xl border border-slate-100 bg-white text-left active:bg-slate-50">
              <span className="w-10 h-10 rounded-xl bg-[#F0FBF4] flex items-center justify-center shrink-0"><Camera className="w-5 h-5" style={{ color: GREEN }} /></span>
              <span className="flex-1">
                <span className="block text-sm font-black text-slate-900">Fotografiază document</span>
                <span className="block text-[11px] text-slate-400">deschide camera telefonului</span>
              </span>
              <ChevronRight className="w-4 h-4 text-slate-300" />
            </button>
            <button type="button" data-testid="vault-source-gallery"
              onClick={() => { galleryRef.current?.click(); setShowSource(false); }}
              className="mt-2 w-full flex items-center gap-3 p-4 rounded-2xl border border-slate-100 bg-white text-left active:bg-slate-50">
              <span className="w-10 h-10 rounded-xl bg-[#F0FBF4] flex items-center justify-center shrink-0"><FolderOpen className="w-5 h-5" style={{ color: GREEN }} /></span>
              <span className="flex-1">
                <span className="block text-sm font-black text-slate-900">Alege din galerie</span>
                <span className="block text-[11px] text-slate-400">poze, PDF-uri și fișiere existente</span>
              </span>
              <ChevronRight className="w-4 h-4 text-slate-300" />
            </button>
            <button type="button" data-testid="vault-source-cancel" onClick={() => setShowSource(false)}
              className="mt-3 w-full py-3 rounded-full text-sm font-bold text-slate-500 bg-slate-50">Anulează</button>
          </div>
        </div>
      )}

      <label className="mt-4 block text-[11px] font-black uppercase tracking-wider text-slate-400">Ce este documentul?</label>
      <div className="mt-2 flex flex-wrap gap-1.5" data-testid="vault-category-chips">
        {cats.map(c => (
          <button key={c.id} onClick={() => setCategory(c.id)} data-testid={`vault-cat-${c.id}`}
            className={`px-3 py-1.5 rounded-full text-xs font-bold border-2 transition-colors ${category === c.id ? "text-black border-transparent" : "text-slate-600 border-slate-200"}`}
            style={category === c.id ? { background: "#d4ff3a" } : {}}>
            {c.label}
          </button>
        ))}
      </div>

      <label className="mt-4 block text-[11px] font-black uppercase tracking-wider text-slate-400">Denumire</label>
      <input value={title} onChange={e => setTitle(e.target.value)} data-testid="vault-title-input"
        className="mt-1.5 w-full px-4 py-3 rounded-2xl border-2 border-slate-200 text-sm outline-none focus:border-[#34C759]"
        placeholder="ex: Act de proprietate apartament" />

      <button onClick={() => setMore(!more)} data-testid="vault-more-toggle"
        className="mt-3 flex items-center gap-1 text-xs font-bold text-slate-500">
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${more ? "rotate-180" : ""}`} /> Detalii opționale (sistem, cameră, garanție)
      </button>
      {more && (
        <div className="mt-2 grid grid-cols-2 gap-2" data-testid="vault-more-fields">
          <select value={meta.building_system} onChange={e => setMeta({ ...meta, building_system: e.target.value })} data-testid="vault-system"
            className="px-3 py-2.5 rounded-2xl border-2 border-slate-200 text-xs bg-white">
            <option value="">Sistem (opțional)</option>
            {["electric", "sanitar", "incalzire", "climatizare", "structura", "acoperis", "tamplarie", "finisaje", "altele"].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <input placeholder="Cameră" value={meta.room} onChange={e => setMeta({ ...meta, room: e.target.value })} data-testid="vault-room"
            className="px-3 py-2.5 rounded-2xl border-2 border-slate-200 text-xs" />
          <input type="date" value={meta.doc_date} onChange={e => setMeta({ ...meta, doc_date: e.target.value })} data-testid="vault-doc-date"
            className="px-3 py-2.5 rounded-2xl border-2 border-slate-200 text-xs" title="Data documentului" />
          <input placeholder="Firmă / emitent" value={meta.company} onChange={e => setMeta({ ...meta, company: e.target.value })} data-testid="vault-company"
            className="px-3 py-2.5 rounded-2xl border-2 border-slate-200 text-xs" />
          <label className="col-span-2 text-[10px] font-bold text-slate-400 -mb-1.5 mt-1">Garanție valabilă până la (dacă e cazul)</label>
          <input type="date" value={meta.warranty_end} onChange={e => setMeta({ ...meta, warranty_end: e.target.value })} data-testid="vault-warranty-end"
            className="px-3 py-2.5 rounded-2xl border-2 border-slate-200 text-xs" />
          <input placeholder="Etichete (virgulă)" value={meta.tags} onChange={e => setMeta({ ...meta, tags: e.target.value })} data-testid="vault-tags"
            className="px-3 py-2.5 rounded-2xl border-2 border-slate-200 text-xs" />
          <textarea placeholder="Note" value={meta.notes} onChange={e => setMeta({ ...meta, notes: e.target.value })} data-testid="vault-notes"
            className="col-span-2 px-3 py-2.5 rounded-2xl border-2 border-slate-200 text-xs" rows={2} />
        </div>
      )}

      {err && <div className="mt-3 text-xs font-bold text-red-500" data-testid="vault-upload-error">{err}</div>}
      <div className="mt-4">
        <CTA onClick={submit} disabled={!file || !category || busy} testid="vault-upload-submit">
          {busy ? "Se salvează în cartea casei…" : "Salvează documentul"}
        </CTA>
      </div>
    </Sheet>
  );
};

// ── Detaliu document: preview, metadate, trust, istoric, versiuni ────────────
const DocSheet = ({ docId, onClose, onChanged }) => {
  const [data, setData] = useState(null);
  const [editing, setEditing] = useState(false);
  const [edit, setEdit] = useState({});
  const load = useCallback(() => {
    axios.get(`${API}/documents/${docId}`).then(r => setData(r.data)).catch(() => {});
  }, [docId]);
  useEffect(() => { load(); }, [load]);
  if (!data) return null;
  const d = data.document;
  const isImg = (d.content_type || "").startsWith("image/");
  const fileUrl = `${API}/documents/${d.id}/file`;

  const save = () => {
    axios.patch(`${API}/documents/${d.id}`, edit)
      .then(() => { setEditing(false); setEdit({}); load(); onChanged(); })
      .catch(e => alert(formatApiError(e)));
  };
  const remove = () => {
    if (!window.confirm("Ștergi documentul din cartea casei? (istoricul se păstrează)")) return;
    axios.delete(`${API}/documents/${d.id}`).then(() => { onChanged(); onClose(); }).catch(e => alert(formatApiError(e)));
  };

  const Meta = ({ label, value }) => (value ? <div><dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</dt><dd className="text-xs font-bold text-slate-700">{value}</dd></div> : null);

  return (
    <Sheet title={d.title} onClose={onClose} testid="vault-doc-sheet">
      {isImg ? (
        <img src={fileUrl} alt={d.title} className="w-full max-h-56 object-cover rounded-2xl border border-slate-100" data-testid="vault-doc-preview" />
      ) : (
        <div className="flex items-center gap-3 p-4 rounded-2xl bg-slate-50 border border-slate-100" data-testid="vault-doc-preview">
          <FileText className="w-8 h-8" style={{ color: GREEN }} />
          <div className="min-w-0">
            <div className="text-sm font-black text-slate-800 truncate">{d.filename}</div>
            <div className="text-[11px] text-slate-400">{d.category_label} · {fmtSize(d.size || 0)} · v{d.version}</div>
          </div>
        </div>
      )}

      <div className="mt-3 flex items-center gap-2 flex-wrap" data-testid="vault-doc-trust">
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wide bg-[#F0FBF4] text-[#166534]">
          <ShieldCheck className="w-3 h-3" /> {SOURCE_LABEL[d.source] || d.source}
        </span>
        <span className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wide ${d.verification_status === "verified" ? "bg-[#d4ff3a] text-black" : "bg-slate-100 text-slate-500"}`}>
          {d.verification_status === "verified" ? "Verificat" : "Neverificat"}
        </span>
        <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wide bg-slate-100 text-slate-500">
          {d.provenance === "documented" ? "Documentat" : "Declarat"}
        </span>
      </div>

      {!editing ? (
        <dl className="mt-4 grid grid-cols-2 gap-3" data-testid="vault-doc-meta">
          <Meta label="Categorie" value={d.category_label} />
          <Meta label="Data documentului" value={d.doc_date ? fmtDate(d.doc_date) : null} />
          <Meta label="Adăugat" value={`${fmtDate(d.uploaded_at)} · ${d.author_name || ""}`} />
          <Meta label="Sistem" value={d.building_system} />
          <Meta label="Cameră" value={d.room} />
          <Meta label="Firmă" value={d.company} />
          <Meta label="Furnizor" value={d.supplier} />
          <Meta label="Garanție până la" value={d.warranty_end ? fmtDate(d.warranty_end) : null} />
          <Meta label="Etichete" value={(d.tags || []).join(", ") || null} />
          <Meta label="Note" value={d.notes} />
        </dl>
      ) : (
        <div className="mt-4 space-y-2" data-testid="vault-doc-edit">
          <input value={edit.title ?? d.title} onChange={e => setEdit({ ...edit, title: e.target.value })} data-testid="vault-edit-title"
            className="w-full px-3 py-2.5 rounded-2xl border-2 border-slate-200 text-sm" placeholder="Denumire" />
          <input value={edit.room ?? (d.room || "")} onChange={e => setEdit({ ...edit, room: e.target.value })}
            className="w-full px-3 py-2.5 rounded-2xl border-2 border-slate-200 text-sm" placeholder="Cameră" />
          <textarea value={edit.notes ?? (d.notes || "")} onChange={e => setEdit({ ...edit, notes: e.target.value })}
            className="w-full px-3 py-2.5 rounded-2xl border-2 border-slate-200 text-sm" rows={2} placeholder="Note" />
          <div className="flex gap-2">
            <button onClick={save} className="flex-1 py-2.5 rounded-full text-sm font-black text-black" style={{ background: "#d4ff3a" }} data-testid="vault-edit-save">Salvează</button>
            <button onClick={() => setEditing(false)} className="px-4 py-2.5 rounded-full text-sm font-bold border-2 border-slate-200 text-slate-500">Anulează</button>
          </div>
        </div>
      )}

      {(data.previous_versions || []).length > 0 && (
        <div className="mt-4" data-testid="vault-doc-versions">
          <div className="text-[11px] font-black uppercase tracking-wider text-slate-400">Versiuni anterioare</div>
          {data.previous_versions.map(v => (
            <div key={v.id} className="mt-1 text-xs text-slate-500">v{v.version} · {fmtDate(v.uploaded_at)} · {fmtSize(v.size || 0)}</div>
          ))}
        </div>
      )}

      {(d.history || []).length > 0 && (
        <div className="mt-4" data-testid="vault-doc-history">
          <div className="flex items-center gap-1 text-[11px] font-black uppercase tracking-wider text-slate-400"><History className="w-3 h-3" /> Istoric</div>
          {(d.history || []).slice(-4).reverse().map((h, i) => (
            <div key={i} className="mt-1 text-[11px] text-slate-500">{fmtDate(h.at)} · {h.by} · {h.event}</div>
          ))}
        </div>
      )}

      <div className="mt-5 grid grid-cols-3 gap-2">
        <a href={`${fileUrl}?download=1`} data-testid="vault-doc-download"
          className="flex items-center justify-center gap-1.5 py-3 rounded-full text-xs font-black text-black" style={{ background: "#d4ff3a" }}>
          <Download className="w-3.5 h-3.5" /> Descarcă
        </a>
        <button onClick={() => setEditing(true)} data-testid="vault-doc-edit-btn"
          className="flex items-center justify-center gap-1.5 py-3 rounded-full text-xs font-bold border-2 border-slate-200 text-slate-600">
          <Pencil className="w-3.5 h-3.5" /> Editează
        </button>
        <button onClick={remove} data-testid="vault-doc-delete"
          className="flex items-center justify-center gap-1.5 py-3 rounded-full text-xs font-bold border-2 border-red-100 text-red-500">
          <Trash2 className="w-3.5 h-3.5" /> Șterge
        </button>
      </div>
    </Sheet>
  );
};

// ── Lista completă cu căutare + filtre pe cunoaștere (nu pe nume de fișier) ─
const VaultSheet = ({ prop, onClose, onUpload, refreshKey }) => {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [data, setData] = useState(null);
  const [openDoc, setOpenDoc] = useState(null);
  const load = useCallback(() => {
    axios.get(`${API}/properties/${prop.id}/documents`, { params: { q, category: cat } })
      .then(r => setData(r.data)).catch(() => {});
  }, [prop.id, q, cat]);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load, refreshKey]);

  return (
    <Sheet title="Cartea casei — documente" onClose={onClose} testid="vault-sheet">
      <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-full border-2 border-slate-200">
        <Search className="w-4 h-4 text-slate-400" />
        <input value={q} onChange={e => setQ(e.target.value)} data-testid="vault-search"
          className="flex-1 text-sm outline-none bg-transparent" placeholder="Caută după cameră, firmă, etichetă…" />
        {q && <button onClick={() => setQ("")} data-testid="vault-search-clear"><X className="w-4 h-4 text-slate-400" /></button>}
      </div>
      <div className="mt-3 flex gap-1.5 overflow-x-auto pb-1" data-testid="vault-facets">
        <button onClick={() => setCat("")} className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-bold border-2 ${!cat ? "text-black border-transparent" : "text-slate-500 border-slate-200"}`}
          style={!cat ? { background: "#d4ff3a" } : {}}>Toate {data ? `(${data.total})` : ""}</button>
        {(data?.facets || []).map(f => (
          <button key={f.category} onClick={() => setCat(cat === f.category ? "" : f.category)} data-testid={`vault-facet-${f.category}`}
            className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-bold border-2 ${cat === f.category ? "text-black border-transparent" : "text-slate-500 border-slate-200"}`}
            style={cat === f.category ? { background: "#d4ff3a" } : {}}>
            {f.label} ({f.count})
          </button>
        ))}
      </div>

      <div className="mt-3 space-y-2" data-testid="vault-doc-list">
        {(data?.documents || []).map(d => {
          const Icon = CAT_ICONS[d.category] || FileText;
          return (
            <button key={d.id} onClick={() => setOpenDoc(d.id)} data-testid={`vault-doc-${d.id}`}
              className="w-full flex items-center gap-3 p-3 rounded-2xl border border-slate-100 bg-white text-left active:bg-slate-50">
              {(d.content_type || "").startsWith("image/")
                ? <img src={`${API}/documents/${d.id}/file`} alt="" className="w-10 h-10 rounded-xl object-cover" loading="lazy" />
                : <span className="w-10 h-10 rounded-xl bg-[#F0FBF4] flex items-center justify-center"><Icon className="w-5 h-5" style={{ color: GREEN }} /></span>}
              <span className="flex-1 min-w-0">
                <span className="block text-sm font-black text-slate-800 truncate">{d.title}</span>
                <span className="block text-[11px] text-slate-400">{d.category_label} · {fmtDate(d.doc_date || d.uploaded_at)}{d.room ? ` · ${d.room}` : ""}</span>
              </span>
              <ChevronRight className="w-4 h-4 text-slate-300" />
            </button>
          );
        })}
        {data && data.documents.length === 0 && (
          <div className="py-8 text-center text-sm text-slate-400" data-testid="vault-empty">Niciun document {q || cat ? "pentru acest filtru" : "încă"}.</div>
        )}
      </div>
      <div className="mt-4"><CTA onClick={onUpload} testid="vault-sheet-upload"><Upload className="w-4 h-4 inline mr-1.5 -mt-0.5" />Adaugă document</CTA></div>
      {openDoc && <DocSheet docId={openDoc} onClose={() => setOpenDoc(null)} onChanged={load} />}
    </Sheet>
  );
};

// ── Cardul principal din Property Hub: scor + next step + ultimele documente ─
export const DocumentVaultCard = ({ prop }) => {
  const [compl, setCompl] = useState(null);
  const [docs, setDocs] = useState([]);
  const [showUpload, setShowUpload] = useState(false);
  const [showVault, setShowVault] = useState(false);
  const [celebrate, setCelebrate] = useState(null);
  const [presetCat, setPresetCat] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(() => {
    axios.get(`${API}/properties/${prop.id}/completeness`).then(r => setCompl(r.data)).catch(() => {});
    axios.get(`${API}/properties/${prop.id}/documents`).then(r => setDocs((r.data.documents || []).slice(0, 3))).catch(() => {});
  }, [prop.id]);
  useEffect(() => { load(); }, [load]);

  const onUploaded = (data) => {
    setShowUpload(false);
    setCompl(data.completeness);
    setRefreshKey(k => k + 1);
    load();
    if (data.first_upload) setCelebrate(data.completeness?.score);
    window.dispatchEvent(new CustomEvent("propmanage:doc-uploaded"));
  };

  const nextStep = compl?.next_step;
  const openUploadFor = (action) => {
    setPresetCat(action?.startsWith("upload:") ? action.split(":")[1] : "");
    setShowUpload(true);
  };

  return (
    <div className="mt-4 rounded-3xl border border-slate-100 bg-white shadow-sm p-4" data-testid="vault-card">
      <div className="flex items-center gap-2">
        <span className="w-9 h-9 rounded-2xl bg-[#F0FBF4] flex items-center justify-center"><FileText className="w-4.5 h-4.5" style={{ color: GREEN, width: 18, height: 18 }} /></span>
        <div className="flex-1">
          <div className="text-sm font-black text-slate-900">Cartea casei</div>
          <div className="text-[11px] text-slate-400">memoria permanentă a proprietății</div>
        </div>
        {compl && (
          <div className="text-right" data-testid="vault-score">
            <div className="text-xl font-black" style={{ color: GREEN }}>{compl.score}%</div>
            <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">documentată</div>
          </div>
        )}
      </div>

      {compl && (
        <div className="mt-3 h-2 rounded-full bg-slate-100 overflow-hidden">
          <div className="h-full rounded-full transition-all duration-700" data-testid="vault-progress"
            style={{ width: `${compl.score}%`, background: "linear-gradient(90deg, #34C759, #d4ff3a)" }} />
        </div>
      )}

      {nextStep && (
        <button onClick={() => nextStep.action?.startsWith("upload") ? openUploadFor(nextStep.action) : setShowVault(true)}
          data-testid="vault-next-step"
          className="mt-3 w-full flex items-center gap-2 p-3 rounded-2xl bg-[#F0FBF4] border border-[#D2F2DC] text-left">
          <Sparkles className="w-4 h-4 shrink-0 text-[#166534]" />
          <span className="flex-1 text-xs font-bold text-slate-700">Pasul următor: {nextStep.label}</span>
          <span className="shrink-0 text-[10px] font-black px-2 py-0.5 rounded-full text-black" style={{ background: "#d4ff3a" }}>+{nextStep.expected_gain}%</span>
        </button>
      )}

      {docs.length > 0 && (
        <div className="mt-3 space-y-1.5" data-testid="vault-recent">
          {docs.map(d => (
            <button key={d.id} onClick={() => setShowVault(true)} className="w-full flex items-center gap-2.5 text-left">
              {(d.content_type || "").startsWith("image/")
                ? <img src={`${API}/documents/${d.id}/file`} alt="" className="w-8 h-8 rounded-lg object-cover" loading="lazy" />
                : <span className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center"><FileText className="w-4 h-4 text-slate-400" /></span>}
              <span className="flex-1 min-w-0">
                <span className="block text-xs font-bold text-slate-700 truncate">{d.title}</span>
                <span className="block text-[10px] text-slate-400">{d.category_label} · {fmtDate(d.doc_date || d.uploaded_at)}</span>
              </span>
            </button>
          ))}
        </div>
      )}

      <div className="mt-3 flex gap-2">
        <button onClick={() => openUploadFor("")} data-testid="vault-add-btn"
          className="flex-1 py-3 rounded-full text-sm font-black text-black active:scale-[0.98] transition-transform" style={{ background: "#d4ff3a" }}>
          <Upload className="w-4 h-4 inline mr-1.5 -mt-0.5" />Adaugă document
        </button>
        {compl?.docs_count > 0 && (
          <button onClick={() => setShowVault(true)} data-testid="vault-open-all"
            className="px-4 py-3 rounded-full text-sm font-bold border-2 border-slate-200 text-slate-600">
            Toate ({compl.docs_count})
          </button>
        )}
      </div>

      <div className="mt-3">
        <StorageUsageCard />
      </div>

      {showUpload && <UploadSheet prop={prop} presetCategory={presetCat} onClose={() => setShowUpload(false)} onDone={onUploaded} />}
      {showVault && <VaultSheet prop={prop} onClose={() => setShowVault(false)} onUpload={() => { setShowVault(false); openUploadFor(""); }} refreshKey={refreshKey} />}
      {celebrate != null && <MemoryCelebration score={celebrate} onClose={() => setCelebrate(null)} />}
    </div>
  );
};
