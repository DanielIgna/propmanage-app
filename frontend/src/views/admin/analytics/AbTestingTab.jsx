import React, { useEffect, useState } from "react";
import axios from "axios";
import { FlaskConical, Plus, Trash2, Pause, Play, Trophy, Loader2 } from "lucide-react";
import { API } from "../../DashShared";
import { toast } from "sonner";

const GOALS = [
  ["signup_started", "Început înregistrare"],
  ["account_created", "Cont creat"],
  ["property_added", "Proprietate adăugată"],
  ["subscription", "Abonament"],
  ["specialist_request", "Solicitare specialist"],
];

const VariantCard = ({ label, v, winner }) => (
  <div className={`rounded-xl p-3 border-2 ${winner ? "border-emerald-400 bg-emerald-50 dark:bg-emerald-500/10" : "border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/30"}`}>
    <div className="flex items-center gap-1.5 text-xs font-bold text-slate-500">
      Varianta {label} {winner && <Trophy className="w-3.5 h-3.5 text-emerald-500" />}
    </div>
    <div className="mt-1 text-2xl font-black text-slate-900 dark:text-white">{v.rate_pct}%</div>
    <div className="text-[11px] text-slate-400">{v.conversions} conversii / {v.visitors} vizitatori</div>
  </div>
);

export const AbTestingTab = () => {
  const [items, setItems] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", page_path: "/", goal: "account_created", hypothesis: "" });

  const load = () => axios.get(`${API}/admin/analytics/ab`).then(r => setItems(r.data.items)).catch(() => {});
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.name.trim()) return toast.error("Numele experimentului e obligatoriu");
    try {
      await axios.post(`${API}/admin/analytics/ab`, form);
      toast.success("Experiment creat — variantele A/B se atribuie automat vizitatorilor");
      setShowCreate(false);
      setForm({ name: "", page_path: "/", goal: "account_created", hypothesis: "" });
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Eroare la creare"); }
  };

  const toggleStatus = async (exp) => {
    await axios.patch(`${API}/admin/analytics/ab/${exp.id}`, { status: exp.status === "active" ? "stopped" : "active" });
    load();
  };

  const remove = async (id) => {
    if (!window.confirm("Ștergi experimentul? Datele de expunere rămân în sesiuni.")) return;
    await axios.delete(`${API}/admin/analytics/ab/${id}`);
    load();
  };

  if (!items) return <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-slate-400" /></div>;

  return (
    <div className="space-y-4" data-testid="ag-ab-tab">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-500">Vizitatorii sunt împărțiți automat 50/50 (determinist). Semnificația statistică se calculează cu test z (p &lt; 0.05).</p>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-bold bg-blue-600 text-white" data-testid="ab-new-btn">
          <Plus className="w-4 h-4" /> Experiment nou
        </button>
      </div>

      {showCreate && (
        <div className="rounded-2xl border-2 border-blue-200 dark:border-blue-500/30 bg-white dark:bg-slate-800 p-4 grid md:grid-cols-2 gap-3" data-testid="ab-create-form">
          <label className="text-xs font-bold text-slate-500">Nume experiment *
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} data-testid="ab-form-name"
              placeholder="ex: Titlu hero landing" className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-transparent text-sm font-normal" />
          </label>
          <label className="text-xs font-bold text-slate-500">Pagina testată
            <input value={form.page_path} onChange={e => setForm(f => ({ ...f, page_path: e.target.value }))} data-testid="ab-form-path"
              className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-transparent text-sm font-mono font-normal" />
          </label>
          <label className="text-xs font-bold text-slate-500">Obiectiv (conversie măsurată)
            <select value={form.goal} onChange={e => setForm(f => ({ ...f, goal: e.target.value }))} data-testid="ab-form-goal"
              className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm font-normal">
              {GOALS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="text-xs font-bold text-slate-500">Ipoteză
            <input value={form.hypothesis} onChange={e => setForm(f => ({ ...f, hypothesis: e.target.value }))}
              placeholder="ex: Un CTA mai mare crește conversia" className="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-transparent text-sm font-normal" />
          </label>
          <div className="md:col-span-2 flex gap-2 justify-end">
            <button onClick={() => setShowCreate(false)} className="px-3 py-2 rounded-xl text-xs font-bold border border-slate-200 dark:border-slate-600">Anulează</button>
            <button onClick={create} className="px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 text-white" data-testid="ab-form-submit">Creează experiment</button>
          </div>
        </div>
      )}

      <div className="grid gap-3" data-testid="ab-list">
        {items.length === 0 && !showCreate && (
          <div className="text-center py-12 text-slate-400 text-sm">
            <FlaskConical className="w-10 h-10 mx-auto mb-2 opacity-40" />
            Niciun experiment încă. Creează primul test A/B și măsoară ce variantă convertește mai bine.
          </div>
        )}
        {items.map(exp => {
          const r = exp.results;
          return (
            <div key={exp.id} className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4" data-testid={`ab-exp-${exp.key}`}>
              <div className="flex flex-wrap items-center gap-2">
                <FlaskConical className="w-4 h-4 text-blue-500" />
                <span className="font-black text-slate-900 dark:text-white">{exp.name}</span>
                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${exp.status === "active" ? "bg-emerald-100 dark:bg-emerald-500/15 text-emerald-600" : "bg-slate-100 dark:bg-slate-700 text-slate-500"}`}>{exp.status === "active" ? "activ" : "oprit"}</span>
                <span className="text-xs text-slate-400 font-mono">{exp.page_path}</span>
                <span className="text-xs text-slate-400">· obiectiv: {GOALS.find(g => g[0] === exp.goal)?.[1] || exp.goal}</span>
                <div className="ml-auto flex items-center gap-1.5">
                  <button onClick={() => toggleStatus(exp)} className="p-1.5 rounded-lg bg-slate-50 dark:bg-slate-700/40 text-slate-500" title={exp.status === "active" ? "Oprește" : "Repornește"} data-testid={`ab-toggle-${exp.key}`}>
                    {exp.status === "active" ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </button>
                  <button onClick={() => remove(exp.id)} className="p-1.5 rounded-lg bg-rose-50 dark:bg-rose-500/15 text-rose-500" data-testid={`ab-delete-${exp.key}`}>
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              {exp.hypothesis && <p className="text-xs text-slate-500 mt-1 italic">„{exp.hypothesis}"</p>}
              <div className="mt-3 grid sm:grid-cols-3 gap-3">
                <VariantCard label="A" v={r.variants.A} winner={r.winner === "A"} />
                <VariantCard label="B" v={r.variants.B} winner={r.winner === "B"} />
                <div className="rounded-xl p-3 border-2 border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/30">
                  <div className="text-xs font-bold text-slate-500">Semnificație statistică</div>
                  {r.significance.significant ? (
                    <div className="mt-1 text-sm font-black text-emerald-600">✓ Semnificativ (p={r.significance.p_value}) — câștigător: {r.winner}</div>
                  ) : (
                    <div className="mt-1 text-sm font-bold text-slate-500">{r.significance.note || `Încă nesemnificativ${r.significance.p_value != null ? ` (p=${r.significance.p_value})` : ""}`}</div>
                  )}
                  {r.uplift_pct != null && <div className="text-[11px] text-slate-400 mt-1">Uplift B vs A: {r.uplift_pct > 0 ? "+" : ""}{r.uplift_pct}%</div>}
                  <div className="text-[10px] text-slate-400 mt-2 font-mono">cheie: {exp.key}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 p-4 text-xs text-slate-500">
        <span className="font-bold">Cum se folosește în cod:</span> în pagina testată apelezi <code className="font-mono bg-white dark:bg-slate-700 px-1.5 py-0.5 rounded">getAbVariant("cheia_experimentului")</code> din <code className="font-mono">lib/analytics.js</code> — primești „A" sau „B" și afișezi varianta corespunzătoare. Expunerea și conversiile se măsoară automat.
      </div>
    </div>
  );
};
