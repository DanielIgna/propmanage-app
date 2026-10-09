// OperatingManualPage — In-app manual for the founder. Renders the canonical
// /app/docs/OPERATING_MANUAL.md so you can read everything without leaving the
// admin panel. Includes search + section navigation.
import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import {
  BookOpenCheck, ChevronLeft, Loader2, Search, List, X,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const MD_COMPONENTS = {
  h1: (props) => <h1 className="text-3xl font-serif text-white mt-2 mb-4 pb-2 border-b border-white/10" {...props} />,
  h2: (props) => <h2 className="text-2xl font-serif text-amber-200 mt-8 mb-3 pb-1 border-b border-amber-500/20" {...props} />,
  h3: (props) => <h3 className="text-lg font-semibold text-white mt-5 mb-2" {...props} />,
  h4: (props) => <h4 className="text-sm font-semibold text-violet-200 mt-4 mb-1" {...props} />,
  p:  (props) => <p className="text-sm text-stone-300 leading-relaxed my-2.5" {...props} />,
  ul: (props) => <ul className="list-disc ml-6 text-sm text-stone-300 my-2 space-y-1" {...props} />,
  ol: (props) => <ol className="list-decimal ml-6 text-sm text-stone-300 my-2 space-y-1" {...props} />,
  li: (props) => <li className="leading-relaxed" {...props} />,
  a:  (props) => <a className="text-amber-300 hover:text-amber-200 underline" {...props} />,
  code: ({ inline, ...props }) => (
    inline
      ? <code className="bg-violet-500/10 text-violet-200 px-1.5 py-0.5 rounded text-[12px] font-mono" {...props} />
      : <code className="block bg-black/40 text-emerald-200 p-3 rounded-lg text-[12px] font-mono overflow-x-auto my-2 border border-white/5" {...props} />
  ),
  pre: (props) => <pre className="my-3" {...props} />,
  blockquote: (props) => <blockquote className="border-l-4 border-amber-500/40 bg-amber-500/5 pl-4 py-2 my-3 text-sm text-amber-100 italic" {...props} />,
  table: (props) => <div className="my-4 overflow-x-auto"><table className="min-w-full text-xs border border-white/10 rounded-lg" {...props} /></div>,
  thead: (props) => <thead className="bg-white/[0.04]" {...props} />,
  th: (props) => <th className="px-3 py-2 text-left text-stone-200 font-semibold border-b border-white/10" {...props} />,
  td: (props) => <td className="px-3 py-2 text-stone-300 border-b border-white/5" {...props} />,
  strong: (props) => <strong className="text-white font-semibold" {...props} />,
  em: (props) => <em className="text-stone-400" {...props} />,
  hr: (props) => <hr className="border-white/10 my-6" {...props} />,
};

const OperatingManualPage = () => {
  const [doc, setDoc] = useState("manual"); // "manual" | "tier-testing"
  const [content, setContent] = useState("");
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [tocOpen, setTocOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const url = doc === "tier-testing"
      ? "/api/admin/operating-manual/tier-testing"
      : "/api/admin/operating-manual";
    (async () => {
      setLoading(true);
      try {
        const { data } = await ax.get(url);
        if (cancelled) return;
        setContent(data.content || "");
        setMeta({ size: data.size_bytes, lines: data.line_count });
        setError(null);
      } catch (e) {
        if (!cancelled) setError(e?.response?.data?.detail || e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [doc]);

  // Extract TOC headings (## level 2)
  const toc = useMemo(() => {
    const lines = content.split("\n");
    const out = [];
    for (const line of lines) {
      const m = line.match(/^## (.+)$/);
      if (m) {
        const text = m[1].replace(/[#📌🛡️🔀🛡️🧭🎯🔔🐛🤖🚪💡🎓🗺️📞]/g, "").trim();
        const id = text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
        out.push({ text: m[1], id });
      }
    }
    return out;
  }, [content]);

  // Filter content by search (very simple — keeps surrounding paragraphs)
  const filteredContent = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q || q.length < 2) return content;
    const sections = content.split(/\n(?=## )/);
    const matched = sections.filter(s => s.toLowerCase().includes(q));
    return matched.length > 0 ? matched.join("\n\n") : `# Niciun rezultat pentru "${search}"\n\nÎncearcă alți termeni sau golește căutarea.`;
  }, [content, search]);

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-7xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="om-back">
          <ChevronLeft className="w-3.5 h-3.5" /> Înapoi la Admin Dashboard
        </Link>

        <div className="flex items-start gap-3 mb-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center shrink-0">
            <BookOpenCheck className="w-5 h-5 text-amber-300" />
          </div>
          <div className="flex-1">
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="om-title">
              Manual de <span className="italic gradient-text">Operare</span>
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-3xl">
              Documentația completă: cum coordonezi platforma 100% din Admin, fără cod, fără să strici nimic.
              {meta && <span className="ml-2 text-[10px] text-stone-600 font-mono">{meta.lines} linii · {Math.round(meta.size / 1024)} KB</span>}
            </p>
          </div>
          <button
            onClick={() => setTocOpen(v => !v)}
            className="lg:hidden inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-stone-300"
            data-testid="om-toc-toggle"
          >
            <List className="w-3.5 h-3.5" /> Cuprins
          </button>
        </div>

        {/* DOC SWITCHER */}
        <div className="flex gap-1 mb-4 border-b border-white/10" data-testid="om-doc-switch">
          <button
            onClick={() => { setDoc("manual"); setSearch(""); }}
            className={`px-3 py-2 text-xs uppercase tracking-wider transition-colors border-b-2 ${
              doc === "manual" ? "border-amber-400 text-white" : "border-transparent text-stone-500 hover:text-white"
            }`}
            data-testid="om-doc-manual"
          >
            Manual de Operare
          </button>
          <button
            onClick={() => { setDoc("tier-testing"); setSearch(""); }}
            className={`px-3 py-2 text-xs uppercase tracking-wider transition-colors border-b-2 ${
              doc === "tier-testing" ? "border-emerald-400 text-white" : "border-transparent text-stone-500 hover:text-white"
            }`}
            data-testid="om-doc-tier-testing"
          >
            Ghid testare Tiers + Pre-Deploy
          </button>
        </div>

        {/* SEARCH */}
        <div className="mb-6 relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-stone-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder='Caută în manual (ex: "deprecation", "rollback", "snapshot", "tier")...'
            className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-[#0e0e10] border border-white/10 text-sm text-white placeholder:text-stone-500 focus:outline-none focus:border-white/30"
            data-testid="om-search"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-500 hover:text-white"
              data-testid="om-search-clear"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {loading ? (
          <div className="text-center py-10 text-stone-400 flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă manualul...
          </div>
        ) : error ? (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-sm text-red-200" data-testid="om-error">
            Eroare la încărcare: {error}
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-6">
            {/* TOC */}
            <aside className={`${tocOpen ? "block" : "hidden lg:block"} bg-[#0e0e10] border border-white/10 rounded-2xl p-4 h-fit lg:sticky lg:top-24`} data-testid="om-toc">
              <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-2">Cuprins</div>
              <nav className="space-y-1">
                {toc.map((t, i) => (
                  <a
                    key={i}
                    href={`#${t.id}`}
                    onClick={() => setTocOpen(false)}
                    className="block text-xs text-stone-300 hover:text-amber-300 py-1 px-2 rounded hover:bg-white/5"
                    data-testid={`om-toc-${t.id}`}
                  >
                    {t.text}
                  </a>
                ))}
              </nav>
            </aside>

            {/* CONTENT */}
            <article className="bg-[#0e0e10] border border-white/10 rounded-2xl p-6 md:p-8 manual-content" data-testid="om-content">
              <ReactMarkdown components={MD_COMPONENTS}>
                {filteredContent}
              </ReactMarkdown>
            </article>
          </div>
        )}
      </div>
    </div>
  );
};

export default OperatingManualPage;
