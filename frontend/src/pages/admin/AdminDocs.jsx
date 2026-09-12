// Admin → Documentație & Training panel.
// - List all available docs (Client, Specialist, Operator, Admin, QA)
// - Preview each one (inline, using DocViewer)
// - Download PDF
// - Send to a custom list of recipients (email + name pairs)
// - Bulk-send to an entire role (e.g. "all clients", "all specialists")
// - View recent send-event history
import React, { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { FileText, Send, Download, Eye, X, Plus, Users, History, Loader2, Search, FileCode } from "lucide-react";
import { AdminCard } from "./AdminLayoutMetronic";
import DocViewer from "../../components/DocViewer";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ROLES_FOR_BULK = [
  { value: "client",     label: "Toți clienții" },
  { value: "specialist", label: "Toți specialiștii" },
  { value: "operator",   label: "Toți operatorii" },
  { value: "admin",      label: "Toți adminii" },
];

// ---- Preview modal ----
const PreviewModal = ({ slug, onClose }) => {
  const [doc, setDoc] = useState(null);
  useEffect(() => {
    if (!slug) return;
    axios.get(`${API}/admin/docs/${slug}`).then(r => setDoc(r.data)).catch(() => {});
  }, [slug]);
  if (!slug) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm overflow-y-auto" onClick={onClose}>
      <div className="min-h-screen flex items-start justify-center p-4">
        <div className="bg-[#0a0a0b] text-stone-100 rounded-2xl border border-white/10 max-w-4xl w-full my-8" onClick={e => e.stopPropagation()}>
          <div className="flex items-center justify-between px-5 py-3 border-b border-white/5 sticky top-0 bg-[#0a0a0b]/95 backdrop-blur z-10 rounded-t-2xl">
            <div className="text-sm font-medium">Preview: {slug}</div>
            <div className="flex items-center gap-2">
              <a href={`${API}/admin/docs/${slug}/pdf`} target="_blank" rel="noopener noreferrer"
                className="text-xs flex items-center gap-1 bg-white/5 hover:bg-white/10 rounded-full px-3 py-1.5"
                data-testid="docs-preview-pdf">
                <Download className="w-3 h-3" /> PDF
              </a>
              <button onClick={onClose} className="p-1 hover:bg-white/5 rounded" data-testid="docs-preview-close"><X className="w-4 h-4" /></button>
            </div>
          </div>
          <div className="px-5 py-6">
            {doc ? <DocViewer doc={doc} /> : <div className="text-center py-20 text-stone-500">Se încarcă...</div>}
          </div>
        </div>
      </div>
    </div>
  );
};

// ---- Send modal ----
const SendModal = ({ slug, onClose, onSent }) => {
  const [mode, setMode] = useState("custom");  // "custom" or "role"
  const [emails, setEmails] = useState("");
  const [role, setRole] = useState("client");
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [includePdf, setIncludePdf] = useState(true);
  const [sending, setSending] = useState(false);

  if (!slug) return null;

  const submit = async () => {
    setSending(true);
    try {
      let res;
      if (mode === "custom") {
        const lines = emails.split(/[\n,;]+/).map(s => s.trim()).filter(Boolean);
        const recipients = lines.map(l => {
          // Allow "Name <email>" format
          const m = l.match(/^(.+?)\s*<(.+)>$/);
          return m ? { name: m[1].trim(), email: m[2].trim() } : { email: l };
        });
        if (!recipients.length) return toast.error("Adaugă cel puțin un email.");
        res = await axios.post(`${API}/admin/docs/${slug}/send`, { recipients, include_pdf: includePdf });
      } else {
        res = await axios.post(`${API}/admin/docs/${slug}/send-to-role`, { role, verified_only: verifiedOnly, include_pdf: includePdf });
      }
      const d = res.data || {};
      toast.success(`Trimis: ${d.sent}/${d.total}`);
      onSent && onSent();
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la trimitere");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 rounded-2xl border border-slate-200 dark:border-slate-700 max-w-lg w-full" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 dark:border-slate-700">
          <div className="text-sm font-medium">Trimite ghidul: <span className="text-[#7cb342]">{slug}</span></div>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-5 space-y-4">
          {/* Mode switch */}
          <div className="flex gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
            <button onClick={() => setMode("custom")} className={`flex-1 text-xs py-1.5 rounded ${mode === "custom" ? "bg-white dark:bg-slate-700 shadow-sm font-medium" : "text-slate-500"}`} data-testid="docs-send-mode-custom">
              Email-uri specifice
            </button>
            <button onClick={() => setMode("role")} className={`flex-1 text-xs py-1.5 rounded ${mode === "role" ? "bg-white dark:bg-slate-700 shadow-sm font-medium" : "text-slate-500"}`} data-testid="docs-send-mode-role">
              Toți utilizatorii cu un rol
            </button>
          </div>

          {mode === "custom" ? (
            <div>
              <label className="text-xs text-slate-500 block mb-1.5">Email-uri (unul per linie sau separate prin virgulă)</label>
              <textarea
                value={emails}
                onChange={e => setEmails(e.target.value)}
                rows={6}
                placeholder="ion@example.com&#10;Maria Pop <maria@example.com>&#10;andrei@example.com"
                className="w-full text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 font-mono"
                data-testid="docs-send-emails-textarea"
              />
              <div className="text-[11px] text-slate-500 mt-1">Format acceptat: <code>email@ex.com</code> sau <code>Nume Prenume &lt;email@ex.com&gt;</code></div>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-500 block mb-1.5">Rol destinatar</label>
                <select value={role} onChange={e => setRole(e.target.value)} className="w-full text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2" data-testid="docs-send-role-select">
                  {ROLES_FOR_BULK.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                <input type="checkbox" checked={verifiedOnly} onChange={e => setVerifiedOnly(e.target.checked)} />
                Doar utilizatori verificați (VERIFIED)
              </label>
              <div className="text-[11px] text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-500/10 rounded-lg p-2">
                ⚠️ Trimitere bulk: maxim 500 destinatari pe acțiune. Folosește cu grijă.
              </div>
            </div>
          )}

          <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
            <input type="checkbox" checked={includePdf} onChange={e => setIncludePdf(e.target.checked)} data-testid="docs-send-include-pdf" />
            Atașează PDF (recomandat — pentru offline / printare)
          </label>
        </div>
        <div className="px-5 py-3 border-t border-slate-200 dark:border-slate-700 flex items-center justify-end gap-2">
          <button onClick={onClose} className="text-xs px-4 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800">Anulează</button>
          <button onClick={submit} disabled={sending} className="text-xs px-4 py-2 rounded-lg bg-[#d4ff3a] text-black font-semibold hover:bg-[#bfe632] disabled:opacity-50 flex items-center gap-1.5" data-testid="docs-send-submit">
            {sending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
            {sending ? "Se trimite..." : "Trimite"}
          </button>
        </div>
      </div>
    </div>
  );
};

// ---- Search palette (Cmd+K / Ctrl+K) ----
const SearchPalette = ({ open, onClose, onJump }) => {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState([]);
  const [loading, setLoading] = useState(false);
  const inputRef = React.useRef(null);

  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
      setQ("");
      setHits([]);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    if (q.trim().length < 2) { setHits([]); return; }
    setLoading(true);
    const t = setTimeout(() => {
      axios.get(`${API}/admin/docs/admin/search?q=${encodeURIComponent(q)}`)
        .then(r => setHits(r.data?.hits || []))
        .catch(() => setHits([]))
        .finally(() => setLoading(false));
    }, 200);
    return () => clearTimeout(t);
  }, [q, open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-24 px-4" onClick={onClose} data-testid="docs-search-palette">
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 max-w-2xl w-full overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-3 px-5 py-3 border-b border-slate-200 dark:border-slate-700">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            ref={inputRef}
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Caută în documentație... (escrow, dispute, twin, etc.)"
            className="flex-1 bg-transparent outline-none text-sm text-slate-800 dark:text-slate-100 placeholder:text-slate-400"
            data-testid="docs-search-input"
          />
          <kbd className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500 rounded px-1.5 py-0.5">ESC</kbd>
        </div>
        <div className="max-h-[60vh] overflow-y-auto">
          {loading && <div className="px-5 py-6 text-center text-xs text-slate-500"><Loader2 className="w-4 h-4 animate-spin inline" /></div>}
          {!loading && q.length >= 2 && hits.length === 0 && (
            <div className="px-5 py-10 text-center text-sm text-slate-500">Niciun rezultat pentru &quot;<span className="text-slate-700 dark:text-slate-300">{q}</span>&quot;.</div>
          )}
          {!loading && q.length < 2 && (
            <div className="px-5 py-8 text-center text-xs text-slate-500">
              Tastează cel puțin 2 caractere.
              <div className="mt-3 flex flex-wrap gap-1.5 justify-center">
                {["escrow", "dispute", "twin", "verificare", "garanție"].map(s => (
                  <button key={s} onClick={() => setQ(s)} className="text-[11px] bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-full px-2.5 py-1">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {hits.map((h, i) => (
            <button
              key={i}
              onClick={() => { onJump(h); onClose(); }}
              className="w-full text-left px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-800 border-b border-slate-100 dark:border-slate-800 last:border-b-0"
              data-testid={`docs-search-hit-${i}`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] uppercase tracking-wider font-bold text-[#7cb342]">{h.doc_slug}</span>
                <span className="text-[10px] text-slate-400">›</span>
                <span className="text-[11px] text-slate-500">{h.section_heading}</span>
                <span className="text-[9px] ml-auto bg-slate-100 dark:bg-slate-800 text-slate-500 rounded px-1.5 py-0.5">{h.kind}</span>
              </div>
              <div className="text-sm text-slate-700 dark:text-slate-200 line-clamp-2">{h.snippet}</div>
            </button>
          ))}
        </div>
        <div className="px-5 py-2 border-t border-slate-200 dark:border-slate-700 text-[10px] text-slate-500 flex items-center justify-between">
          <span>Click pe un rezultat pentru a-l deschide în Preview</span>
          <span><kbd className="bg-slate-100 dark:bg-slate-800 rounded px-1.5 py-0.5">⌘K</kbd> · <kbd className="bg-slate-100 dark:bg-slate-800 rounded px-1.5 py-0.5">Ctrl+K</kbd></span>
        </div>
      </div>
    </div>
  );
};


// ---- Send history (recent events) ----
const SendHistory = () => {
  const [items, setItems] = useState([]);
  useEffect(() => {
    axios.get(`${API}/admin/docs/admin/send-events?limit=20`).then(r => setItems(r.data.items || [])).catch(() => {});
  }, []);
  return (
    <AdminCard title="Istoric trimiteri" action={<History className="w-3.5 h-3.5 text-slate-400" />}>
      {items.length === 0 ? (
        <div className="text-xs text-slate-500 py-4">Niciun email trimis încă.</div>
      ) : (
        <div className="divide-y divide-slate-200 dark:divide-slate-800">
          {items.map((e, i) => (
            <div key={i} className="py-2 flex items-center justify-between text-xs">
              <div>
                <div className="font-medium text-slate-700 dark:text-slate-300">{e.doc_slug} → {e.recipient_email}</div>
                <div className="text-slate-500">{new Date(e.sent_at).toLocaleString("ro-RO")} · de {e.sent_by}</div>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${e.ok ? "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300" : "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300"}`}>
                {e.ok ? "TRIMIS" : "EȘUAT"}
              </span>
            </div>
          ))}
        </div>
      )}
    </AdminCard>
  );
};

// ---- Main panel ----
export const AdminDocs = () => {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [previewSlug, setPreviewSlug] = useState(null);
  const [sendSlug, setSendSlug] = useState(null);
  const [searchOpen, setSearchOpen] = useState(false);

  const load = () => {
    setLoading(true);
    axios.get(`${API}/admin/docs`).then(r => setDocs(r.data.docs || [])).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(load, []);

  // Cmd+K / Ctrl+K global hotkey
  useEffect(() => {
    const h = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
      } else if (e.key === "Escape" && searchOpen) {
        setSearchOpen(false);
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [searchOpen]);

  const copyMarkdown = async (slug) => {
    try {
      const r = await axios.get(`${API}/admin/docs/${slug}/markdown`, { responseType: "text" });
      await navigator.clipboard.writeText(typeof r.data === "string" ? r.data : "");
      toast.success("Markdown copiat în clipboard");
    } catch (e) {
      toast.error("Eroare la copiere markdown");
    }
  };

  const roleLabel = {
    client: "Client", specialist: "Specialist", operator: "Operator", admin: "Admin", qa: "QA / Testare",
  };

  return (
    <div className="space-y-5" data-testid="admin-docs-panel">
      <AdminCard
        title={`Documentație & Training (${docs.length})`}
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSearchOpen(true)}
              className="text-[11px] flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-full px-2.5 py-1 text-slate-600 dark:text-slate-300"
              data-testid="docs-open-search"
              title="Cmd+K / Ctrl+K"
            >
              <Search className="w-3 h-3" /> Caută
              <kbd className="text-[9px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded px-1">⌘K</kbd>
            </button>
            <FileText className="w-3.5 h-3.5 text-slate-400" />
          </div>
        }
      >
        {loading ? (
          <div className="text-center py-8 text-slate-500"><Loader2 className="w-5 h-5 animate-spin inline" /></div>
        ) : (
          <div className="grid md:grid-cols-2 gap-3">
            {docs.map(d => (
              <div key={d.slug} className="rounded-2xl border border-slate-200 dark:border-slate-700 p-4 bg-white dark:bg-slate-900" data-testid={`docs-card-${d.slug}`}>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="text-[10px] uppercase tracking-wider font-bold text-[#7cb342]">{roleLabel[d.role] || d.role}</div>
                    <div className="font-medium text-slate-900 dark:text-slate-100 mt-0.5 text-sm leading-snug">{d.title}</div>
                  </div>
                  <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500 px-2 py-0.5 rounded-full">v{d.version}</span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed mb-3 line-clamp-2">{d.subtitle}</p>
                <div className="flex items-center gap-3 text-[10px] text-slate-500 mb-3">
                  <span>{d.sections_count} secțiuni</span>
                  <span>·</span>
                  <span>{d.faq_count} întrebări FAQ</span>
                  <span>·</span>
                  <span>Actualizat {d.updated_at}</span>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  <button onClick={() => setPreviewSlug(d.slug)} className="flex-1 min-w-[80px] text-xs flex items-center justify-center gap-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg py-2" data-testid={`docs-preview-${d.slug}`}>
                    <Eye className="w-3 h-3" /> Preview
                  </button>
                  <a href={`${API}/admin/docs/${d.slug}/pdf`} target="_blank" rel="noopener noreferrer" className="text-xs flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg py-2 px-2.5" data-testid={`docs-pdf-${d.slug}`} title="Descarcă PDF">
                    <Download className="w-3 h-3" /> PDF
                  </a>
                  <button onClick={() => copyMarkdown(d.slug)} className="text-xs flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg py-2 px-2.5" data-testid={`docs-md-${d.slug}`} title="Copiază Markdown în clipboard">
                    <FileCode className="w-3 h-3" /> MD
                  </button>
                  <button onClick={() => setSendSlug(d.slug)} className="flex-1 min-w-[80px] text-xs flex items-center justify-center gap-1.5 bg-[#d4ff3a] text-black font-semibold hover:bg-[#bfe632] rounded-lg py-2" data-testid={`docs-send-${d.slug}`}>
                    <Send className="w-3 h-3" /> Trimite
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </AdminCard>

      <SendHistory />

      <PreviewModal slug={previewSlug} onClose={() => setPreviewSlug(null)} />
      <SendModal slug={sendSlug} onClose={() => setSendSlug(null)} onSent={load} />
      <SearchPalette
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onJump={(hit) => setPreviewSlug(hit.doc_slug)}
      />
    </div>
  );
};

export default AdminDocs;
