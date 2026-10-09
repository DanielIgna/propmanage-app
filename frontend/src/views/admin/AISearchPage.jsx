// AISearchPage — vorbești cu datele platformei în limba română.
import React, { useState } from "react";
import axios from "axios";
import { Search, Sparkles, RefreshCw } from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { DSButton, EmptyState, DSSkeleton } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const EXAMPLES = [
  "cereri peste 5.000 lei",
  "specialiști fără portofoliu",
  "cereri din Cluj",
  "plăți peste 500 lei",
  "specialiști verificați din București",
];

const fmt = (v) => {
  if (v === true) return "✓";
  if (v === false) return "—";
  if (v == null) return "";
  if (typeof v === "number") return v.toLocaleString("ro-RO");
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T/.test(v)) return new Date(v).toLocaleDateString("ro-RO");
  return String(v);
};

export default function AISearchPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async (q) => {
    const text = (q || query).trim();
    if (!text) return;
    setQuery(text);
    setLoading(true);
    try {
      const r = await ax.post("/admin/ai-search", { query: text });
      setResult(r.data);
    } catch (e) { /* silent */ }
    setLoading(false);
  };

  return (
    <AdminLayoutMetronic
      title="AI Search"
      subtitle="Nu mai filtrezi — vorbești cu sistemul. Întrebări în română, rezultate live din date."
    >
      <div className="space-y-6" data-testid="ai-search-root">
        <AdminCard testid="ais-input-card">
          <div className="flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run()}
              placeholder="ex: arată-mi cererile peste 20.000 lei din Cluj…"
              className="flex-1 px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white"
              data-testid="ais-input"
            />
            <DSButton variant="primary" icon={loading ? RefreshCw : Sparkles} disabled={loading} onClick={() => run()} data-testid="ais-run-btn">
              {loading ? "Caută…" : "Caută"}
            </DSButton>
          </div>
          <div className="flex gap-2 flex-wrap mt-3">
            {EXAMPLES.map((ex) => (
              <button key={ex} onClick={() => run(ex)} className="px-3 py-1.5 rounded-full text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-lime-50 dark:hover:bg-lime-500/10 hover:text-lime-700" data-testid={`ais-example-${EXAMPLES.indexOf(ex)}`}>
                {ex}
              </button>
            ))}
          </div>
        </AdminCard>

        {loading && <DSSkeleton kpis={0} blocks={1} />}
        {!loading && !result && <EmptyState icon={Search} title="Pune o întrebare" hint="AI-ul traduce întrebarea în filtre sigure și îți aduce datele." />}
        {!loading && result && (
          <AdminCard
            title={`${result.collection_label} — ${result.total} rezultate`}
            testid="ais-results"
          >
            <div className="text-xs text-slate-500 mb-3" data-testid="ais-explain">
              <Sparkles className="w-3 h-3 inline mr-1 text-lime-500" />
              {result.explain} {result.ai_generated ? "· interpretat de Claude" : "· interpretare determinist (fallback)"}
            </div>
            {!result.rows.length && <EmptyState icon={Search} title="Zero rezultate" hint="Încearcă o formulare diferită sau alte praguri." />}
            {result.rows.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[10px] uppercase font-black text-slate-400 border-b border-slate-200 dark:border-slate-700">
                      {result.columns.map((c) => <th key={c} className="py-2 pr-4">{c.replace(/_/g, " ")}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, i) => (
                      <tr key={i} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50" data-testid={`ais-row-${i}`}>
                        {result.columns.map((c) => (
                          <td key={c} className="py-2 pr-4 text-slate-700 dark:text-slate-200 whitespace-nowrap max-w-[240px] truncate">{fmt(row[c])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </AdminCard>
        )}
      </div>
    </AdminLayoutMetronic>
  );
}
