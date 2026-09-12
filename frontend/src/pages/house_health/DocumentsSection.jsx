// House Health — Documents section.
import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { FileText, Upload, Link as LinkIcon, Plus, Loader2, Trash2 } from "lucide-react";
import { API } from "../DashShared";
import { DOC_CATEGORIES, EXT_TYPES, fmtDate } from "./constants";

export const DocumentsSection = ({ twinId }) => {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState("file");
  const [category, setCategory] = useState("carte_tehnica");
  const [description, setDescription] = useState("");
  const [docDate, setDocDate] = useState("");
  const [externalLink, setExternalLink] = useState("");
  const [externalType, setExternalType] = useState("google_drive");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/house-health/documents`, { params: { twin_project_id: twinId } });
      setDocs(r.data?.items || []);
    } finally { setLoading(false); }
  };
  useEffect(() => { if (twinId) load(); }, [twinId]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    setError("");
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("twin_project_id", twinId);
      fd.append("category", category);
      fd.append("description", description);
      fd.append("doc_date", docDate);
      if (mode === "file") {
        const f = fileRef.current?.files?.[0];
        if (!f) { setError("Selectează un fișier."); setUploading(false); return; }
        fd.append("file", f);
      } else {
        if (!externalLink) { setError("Introdu link-ul."); setUploading(false); return; }
        fd.append("external_link", externalLink);
        fd.append("external_type", externalType);
      }
      await axios.post(`${API}/house-health/documents`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      setDescription(""); setExternalLink(""); setDocDate("");
      if (fileRef.current) fileRef.current.value = "";
      await load();
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la încărcare");
    } finally { setUploading(false); }
  };

  const remove = async (id) => {
    if (!window.confirm("Ștergi documentul?")) return;
    await axios.delete(`${API}/house-health/documents/${id}`);
    await load();
  };

  return (
    <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-5" data-testid="hh-docs-section">
      <h2 className="text-lg font-bold mb-3">Documentație tehnică</h2>

      <div className="border border-stone-800 rounded-xl p-4 mb-4">
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setMode("file")}
            className={`text-xs px-3 py-1.5 rounded-lg inline-flex items-center gap-1.5 ${mode === "file" ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/40" : "bg-stone-800 text-stone-300 border border-stone-700"}`}
            data-testid="hh-doc-mode-file"
          ><Upload className="w-3 h-3" /> Fișier local</button>
          <button
            onClick={() => setMode("link")}
            className={`text-xs px-3 py-1.5 rounded-lg inline-flex items-center gap-1.5 ${mode === "link" ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40" : "bg-stone-800 text-stone-300 border border-stone-700"}`}
            data-testid="hh-doc-mode-link"
          ><LinkIcon className="w-3 h-3" /> Link extern</button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-2">
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-doc-category">
            {DOC_CATEGORIES.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
          </select>
          <input type="date" value={docDate} onChange={(e) => setDocDate(e.target.value)} className="bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" placeholder="Data document" data-testid="hh-doc-date" />
        </div>
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Descriere..."
          className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm mb-2"
          data-testid="hh-doc-description"
        />

        {mode === "file" ? (
          <input type="file" ref={fileRef} className="text-xs text-stone-300" data-testid="hh-doc-file" />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <select value={externalType} onChange={(e) => setExternalType(e.target.value)} className="bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-doc-extype">
              {EXT_TYPES.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
            </select>
            <input value={externalLink} onChange={(e) => setExternalLink(e.target.value)} placeholder="https://..." className="bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-doc-extlink" />
          </div>
        )}

        {error && <div className="text-xs text-rose-400 mt-2">{error}</div>}
        <button
          onClick={submit}
          disabled={uploading}
          className="mt-3 px-3 py-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-white text-xs font-semibold inline-flex items-center gap-1.5 disabled:opacity-50"
          data-testid="hh-doc-upload"
        >
          {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
          {uploading ? "Se încarcă..." : "Adaugă document"}
        </button>
      </div>

      {loading && <div className="text-xs text-stone-500">Se încarcă...</div>}
      {!loading && docs.length === 0 && <div className="text-xs text-stone-500 italic">Niciun document încă.</div>}
      <ul className="space-y-1.5" data-testid="hh-docs-list">
        {docs.map((d, i) => (
          <li key={d.id} className="flex items-center gap-3 text-sm px-3 py-2 rounded-lg bg-stone-800/40 border border-stone-700/40" data-testid={`hh-doc-${i}`}>
            <FileText className="w-4 h-4 text-stone-400 shrink-0" />
            <div className="min-w-0 flex-1">
              <div className="text-stone-100 truncate font-medium">
                {d.description || d.filename || "Document"}
              </div>
              <div className="text-[10px] text-stone-500 flex items-center gap-2 flex-wrap">
                <span className="uppercase tracking-wider">{d.category.replace(/_/g, " ")}</span>
                {d.doc_date && <span>· {fmtDate(d.doc_date)}</span>}
                <span>· {d.storage === "external" ? `link ${d.external_type}` : `local ${(d.size_bytes / 1024).toFixed(0)}kb`}</span>
              </div>
            </div>
            {d.storage === "external" ? (
              <a href={d.external_link} target="_blank" rel="noreferrer" className="text-xs text-cyan-400 hover:underline">Deschide</a>
            ) : (
              <a href={`${API}${d.file_url}`} target="_blank" rel="noreferrer" className="text-xs text-emerald-400 hover:underline">Descarcă</a>
            )}
            <button onClick={() => remove(d.id)} className="text-rose-400 hover:text-rose-300" data-testid={`hh-doc-delete-${i}`}>
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};
