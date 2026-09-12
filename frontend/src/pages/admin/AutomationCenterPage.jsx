// AutomationCenterPage — reguli Dacă → Atunci cu executor real + log execuții.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { Workflow, Play, ArrowDown, History, RefreshCw } from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { DSButton, EmptyState, DSSkeleton } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });

const RuleCard = ({ rule, onPatch, onRun, running }) => {
  const [param, setParam] = useState(rule.param);
  useEffect(() => { setParam(rule.param); }, [rule.param]);
  return (
    <div className={`rounded-2xl border p-4 space-y-3 ${rule.enabled ? "border-lime-300 dark:border-lime-500/40 bg-lime-50/50 dark:bg-lime-500/5" : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"}`} data-testid={`ac-rule-${rule.key}`}>
      <div className="flex items-center justify-between gap-2">
        <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded ${rule.enabled ? "bg-lime-400 text-slate-900" : "bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-300"}`}>
          {rule.enabled ? "ACTIVĂ" : "INACTIVĂ"}
        </span>
        <button
          onClick={() => onPatch(rule.key, { enabled: !rule.enabled })}
          className={`relative w-10 h-5.5 h-6 rounded-full transition-colors ${rule.enabled ? "bg-lime-400" : "bg-slate-300 dark:bg-slate-600"}`}
          data-testid={`ac-toggle-${rule.key}`}
        >
          <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${rule.enabled ? "left-[18px]" : "left-0.5"}`} />
        </button>
      </div>

      <div className="space-y-1.5">
        <div className="p-2.5 rounded-xl bg-cyan-50 dark:bg-cyan-500/10 border border-cyan-200 dark:border-cyan-500/30">
          <div className="text-[9px] font-black uppercase text-cyan-700 dark:text-cyan-300">Dacă</div>
          <div className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            {rule.if_label.replace("{param}", "")}
            <input
              type="number" min={rule.param_min} max={rule.param_max} value={param}
              onChange={(e) => setParam(e.target.value)}
              onBlur={() => Number(param) !== rule.param && onPatch(rule.key, { param: Number(param) })}
              className="inline-block w-16 mx-1 px-1.5 py-0.5 text-center rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm font-black"
              data-testid={`ac-param-${rule.key}`}
            /> {rule.param_label}
          </div>
        </div>
        <div className="flex justify-center"><ArrowDown className="w-4 h-4 text-slate-400" /></div>
        <div className="p-2.5 rounded-xl bg-lime-50 dark:bg-lime-500/10 border border-lime-200 dark:border-lime-500/30">
          <div className="text-[9px] font-black uppercase text-lime-700 dark:text-lime-300">Atunci</div>
          <div className="text-sm font-semibold text-slate-800 dark:text-slate-100">{rule.then_label}</div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-[10px] text-slate-400">
          {rule.runs_count || 0} rulări{rule.last_run_at ? ` · ultima: ${new Date(rule.last_run_at).toLocaleString("ro-RO")}` : ""}
        </span>
        <DSButton variant="primary" icon={running === rule.key ? RefreshCw : Play} disabled={!!running} onClick={() => onRun(rule.key)} data-testid={`ac-run-${rule.key}`}>
          {running === rule.key ? "Rulează…" : "Rulează acum"}
        </DSButton>
      </div>
    </div>
  );
};

export default function AutomationCenterPage() {
  const [rules, setRules] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(null);
  const [flash, setFlash] = useState(null);

  const load = useCallback(async () => {
    try {
      const [r, e] = await Promise.all([
        ax.get("/admin/automation/rules"),
        ax.get("/admin/automation/executions"),
      ]);
      setRules(r.data.rules || []);
      setExecutions(e.data.executions || []);
    } catch (e) { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const onPatch = async (key, patch) => {
    try { await ax.patch(`/admin/automation/rules/${key}`, patch); load(); } catch (e) { /* silent */ }
  };

  const onRun = async (key) => {
    setRunning(key);
    setFlash(null);
    try {
      const r = await ax.post(`/admin/automation/rules/${key}/run`);
      setFlash({ ok: true, text: `${r.data.actions} (${r.data.matched} potriviri)` });
      load();
    } catch (e) {
      setFlash({ ok: false, text: e?.response?.data?.detail || "Eroare la rulare." });
    }
    setRunning(null);
  };

  return (
    <AdminLayoutMetronic
      title="Automation Center"
      subtitle="Reguli Dacă → Atunci cu executor real — remindere, badge-uri, reactivare clienți"
    >
      {loading ? <DSSkeleton kpis={0} blocks={2} /> : (
        <div className="space-y-6" data-testid="automation-center-root">
          {flash && (
            <div className={`p-3 rounded-xl text-sm border ${flash.ok ? "bg-lime-50 dark:bg-lime-500/10 border-lime-300 dark:border-lime-500/30 text-lime-800 dark:text-lime-200" : "bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300"}`} data-testid="ac-flash">
              {flash.text}
            </div>
          )}

          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {rules.map((r) => <RuleCard key={r.key} rule={r} onPatch={onPatch} onRun={onRun} running={running} />)}
          </div>

          <AdminCard title={<span className="flex items-center gap-2"><History className="w-4 h-4 text-lime-500" /> Istoric execuții</span>} testid="ac-executions">
            {!executions.length && <EmptyState icon={Workflow} title="Nicio execuție încă" hint="Apasă «Rulează acum» pe o regulă pentru a vedea rezultatele aici." />}
            <div className="space-y-1.5">
              {executions.map((e) => (
                <div key={e.id} className="flex items-center justify-between gap-2 p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 text-sm" data-testid={`ac-exec-${e.id}`}>
                  <span className="font-semibold text-slate-800 dark:text-slate-100">{e.actions}</span>
                  <span className="text-[10px] text-slate-400 shrink-0">{e.rule_key} · {new Date(e.ran_at).toLocaleString("ro-RO")}</span>
                </div>
              ))}
            </div>
          </AdminCard>
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
