// A/B Tests admin page: edit variants + view live stats.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { RefreshCw, Save, Trophy, Trash2 } from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

export const AdminABTests = () => {
  const [stats, setStats] = useState([]);
  const [cms, setCms] = useState({});
  const [edits, setEdits] = useState({});
  const [saving, setSaving] = useState({});
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const [s, c] = await Promise.all([
      axios.get(`${API}/admin/ab/stats`),
      axios.get(`${API}/admin/cms`),
    ]);
    setStats(s.data);
    const map = {};
    c.data.forEach(i => { map[i.key] = i.value; });
    setCms(map);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const saveKey = async (k) => {
    if (edits[k] === undefined) return;
    setSaving(s => ({ ...s, [k]: true }));
    try {
      await axios.put(`${API}/admin/cms`, { key: k, value: edits[k] });
      setEdits(e => { const n = { ...e }; delete n[k]; return n; });
      await load();
    } finally {
      setSaving(s => { const n = { ...s }; delete n[k]; return n; });
    }
  };

  const resetExperiment = async (exp) => {
    if (!window.confirm(`Resetează TOATE statisticile pentru "${exp}"? Această acțiune e ireversibilă.`)) return;
    await axios.delete(`${API}/admin/ab/${exp}/reset`);
    await load();
  };

  if (loading && !stats.length) return <div className="text-slate-500 p-6">Se încarcă...</div>;

  return (
    <div className="space-y-4">
      <AdminCard testid="ab-info-card">
        <div className="flex items-start gap-3">
          <div className="text-2xl">🧪</div>
          <div className="flex-1">
            <div className="font-semibold mb-1">Cum funcționează A/B testing</div>
            <div className="text-sm text-slate-500 dark:text-slate-400 space-y-1">
              <div>• Fiecare vizitator nou primește random varianta <b>A</b> sau <b>B</b> (50/50, persistent în browser).</div>
              <div>• Impressions = câți useri au văzut varianta. Clicks = câți au apăsat. CTR = clicks/impressions × 100.</div>
              <div>• <Trophy className="w-3.5 h-3.5 inline text-amber-500" /> <b>Câștigătorul</b> e marcat doar când ambele variante au ≥30 impressions și CTR diferit.</div>
            </div>
          </div>
          <AdminBtn variant="secondary" onClick={load} data-testid="ab-refresh">
            <RefreshCw className="w-3.5 h-3.5 inline mr-1" /> Refresh
          </AdminBtn>
        </div>
      </AdminCard>

      {stats.map(exp => (
        <AdminCard key={exp.experiment} title={exp.label} testid={`ab-exp-${exp.experiment}`}
          action={
            <AdminBtn variant="ghost" onClick={() => resetExperiment(exp.experiment)} data-testid={`ab-reset-${exp.experiment}`}>
              <Trash2 className="w-3.5 h-3.5 inline mr-1" /> Reset stats
            </AdminBtn>
          }>
          <div className="grid md:grid-cols-2 gap-4">
            {exp.variants.map((v, i) => {
              const key = exp.keys[i];
              const value = edits[key] !== undefined ? edits[key] : (cms[key] || "");
              const dirty = edits[key] !== undefined && edits[key] !== cms[key];
              const isWinner = exp.winner === v.variant;
              return (
                <div key={v.variant} className={`p-4 rounded-xl border-2 ${isWinner ? "border-emerald-400 bg-emerald-50 dark:bg-emerald-500/5" : "border-slate-200 dark:border-slate-800"}`} data-testid={`ab-variant-${exp.experiment}-${v.variant}`}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${v.variant === "a" ? "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400" : "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400"}`}>
                        {v.variant.toUpperCase()}
                      </div>
                      <span className="text-sm font-medium">Varianta {v.variant.toUpperCase()}</span>
                    </div>
                    {isWinner && (
                      <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/20 px-2 py-1 rounded-full">
                        <Trophy className="w-3 h-3" /> CÂȘTIGĂTOR
                      </span>
                    )}
                  </div>

                  {/* Editable text */}
                  <label className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Text afișat</label>
                  <div className="flex gap-2 mt-1 mb-3">
                    <input
                      value={value}
                      onChange={e => setEdits(s => ({ ...s, [key]: e.target.value }))}
                      className={`flex-1 px-3 py-2 rounded-lg border text-sm bg-white dark:bg-slate-800 ${dirty ? "border-amber-400" : "border-slate-200 dark:border-slate-700"}`}
                      data-testid={`ab-input-${exp.experiment}-${v.variant}`}
                    />
                    <AdminBtn
                      variant={dirty ? "primary" : "secondary"}
                      onClick={() => saveKey(key)}
                      disabled={!dirty || saving[key]}
                      data-testid={`ab-save-${exp.experiment}-${v.variant}`}
                    >
                      <Save className="w-3.5 h-3.5" />
                    </AdminBtn>
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-3 gap-2">
                    <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-2 text-center">
                      <div className="text-[10px] uppercase tracking-wider text-slate-500">Impressions</div>
                      <div className="text-xl font-bold tabular-nums">{v.impressions}</div>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-2 text-center">
                      <div className="text-[10px] uppercase tracking-wider text-slate-500">Clicks</div>
                      <div className="text-xl font-bold tabular-nums">{v.clicks}</div>
                    </div>
                    <div className={`rounded-lg p-2 text-center ${isWinner ? "bg-emerald-100 dark:bg-emerald-500/10" : "bg-slate-50 dark:bg-slate-800/50"}`}>
                      <div className="text-[10px] uppercase tracking-wider text-slate-500">CTR</div>
                      <div className={`text-xl font-bold tabular-nums ${isWinner ? "text-emerald-700 dark:text-emerald-400" : ""}`}>{v.ctr}%</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          {!exp.winner && exp.variants.every(v => v.impressions >= 30) && (
            <div className="mt-3 text-xs text-slate-500 text-center">CTR egal — niciun câștigător încă</div>
          )}
          {!exp.winner && !exp.variants.every(v => v.impressions >= 30) && (
            <div className="mt-3 text-xs text-slate-500 text-center">
              Strânge mai multe impressions (minim 30 pe variantă) pentru a vedea câștigătorul
            </div>
          )}
        </AdminCard>
      ))}
    </div>
  );
};
