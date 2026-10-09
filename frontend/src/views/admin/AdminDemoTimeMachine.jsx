// Demo Payment Time Machine — admin tools to fast-forward project/request lifecycle.
import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  Zap, RefreshCw, RotateCcw, CreditCard, UserCheck, Play, CheckCircle2,
  ShieldCheck, AlertOctagon, Undo2, FastForward, Wallet, Layers
} from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

const STATUS_COLOR = {
  open: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  assigned: "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300",
  in_progress: "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300",
  completed: "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300",
  confirmed: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300",
  disputed: "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300",
  refunded: "bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300",
};

const MS_STATUS_COLOR = {
  pending_funding: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
  funded: "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300",
  released: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300",
  warranty_hold: "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300",
  warranty_released: "bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300",
};

const ActionBtn = ({ onClick, icon: Icon, label, color, disabled, testid }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed ${color}`}
    data-testid={testid}
  >
    <Icon className="w-3.5 h-3.5" />
    {label}
  </button>
);

const RequestsSection = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState({});

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/demo-tools/requests`);
      setItems(r.data?.items || []);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const act = async (id, action, body = null) => {
    setBusy(prev => ({ ...prev, [id]: true }));
    try {
      await axios.post(`${API}/admin/demo-tools/requests/${id}/${action}`, body || {});
      await load();
    } catch (e) {
      window.alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setBusy(prev => ({ ...prev, [id]: false }));
    }
  };

  return (
    <AdminCard
      title={<div className="flex items-center gap-2"><Zap className="w-4 h-4 text-amber-500" /> Simulator cereri (1 escrow)</div>}
      action={<AdminBtn variant="secondary" onClick={load}><RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /></AdminBtn>}
    >
      {items.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm italic">Nicio cerere de demonstrat</div>
      ) : (
        <div className="space-y-2 max-h-[500px] overflow-y-auto" data-testid="demo-tools-requests-list">
          {items.map(r => {
            const isBusy = busy[r.id];
            const s = r.status;
            return (
              <div key={r.id} className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 text-xs" data-testid={`demo-req-${r.id}`}>
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  <span className="font-medium text-slate-800 dark:text-slate-200 truncate max-w-[220px]" title={r.title}>{r.title}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider font-bold ${STATUS_COLOR[s] || STATUS_COLOR.open}`}>{s || "open"}</span>
                  {r.escrow_amount > 0 && (
                    <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 dark:text-emerald-400 font-semibold">
                      <Wallet className="w-3 h-3" /> {r.escrow_amount} RON
                    </span>
                  )}
                  <span className="ml-auto text-[10px] text-slate-400">{r.client_name} → {r.specialist_name || "—"}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {s === "open" && (
                    <>
                      <ActionBtn onClick={() => act(r.id, "simulate-payment")} icon={CreditCard} label="Plătește (virtual)" color="bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:hover:bg-emerald-500/25 dark:text-emerald-300" disabled={isBusy} testid={`sim-pay-${r.id}`} />
                      <ActionBtn onClick={() => act(r.id, "simulate-specialist-accept", {})} icon={UserCheck} label="Specialist acceptă" color="bg-blue-50 hover:bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:hover:bg-blue-500/25 dark:text-blue-300" disabled={isBusy} testid={`sim-accept-${r.id}`} />
                    </>
                  )}
                  {s === "assigned" && (
                    <ActionBtn onClick={() => act(r.id, "simulate-start")} icon={Play} label="Începe lucrul" color="bg-indigo-50 hover:bg-indigo-100 text-indigo-700 dark:bg-indigo-500/15 dark:hover:bg-indigo-500/25 dark:text-indigo-300" disabled={isBusy} testid={`sim-start-${r.id}`} />
                  )}
                  {s === "in_progress" && (
                    <ActionBtn onClick={() => act(r.id, "simulate-complete")} icon={CheckCircle2} label="Specialist livrează" color="bg-amber-50 hover:bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:hover:bg-amber-500/25 dark:text-amber-300" disabled={isBusy} testid={`sim-complete-${r.id}`} />
                  )}
                  {s === "completed" && (
                    <>
                      <ActionBtn onClick={() => act(r.id, "simulate-confirm")} icon={ShieldCheck} label="Client confirmă (release 95/5)" color="bg-emerald-600 hover:bg-emerald-700 text-white" disabled={isBusy} testid={`sim-confirm-${r.id}`} />
                      <ActionBtn onClick={() => { const reason = window.prompt("Motiv dispută:", "Lucrare incompletă"); if (reason) act(r.id, "simulate-dispute", { reason }); }} icon={AlertOctagon} label="Deschide dispută" color="bg-red-50 hover:bg-red-100 text-red-700 dark:bg-red-500/15 dark:hover:bg-red-500/25 dark:text-red-300" disabled={isBusy} testid={`sim-dispute-${r.id}`} />
                    </>
                  )}
                  {(s === "completed" || s === "assigned" || s === "in_progress") && r.escrow_status === "paid" && (
                    <ActionBtn onClick={() => act(r.id, "simulate-refund")} icon={Undo2} label="Refund către client" color="bg-purple-50 hover:bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:hover:bg-purple-500/25 dark:text-purple-300" disabled={isBusy} testid={`sim-refund-${r.id}`} />
                  )}
                  <ActionBtn onClick={() => { if (window.confirm("Resetez cererea la status 'open' pentru replay?")) act(r.id, "reset"); }} icon={RotateCcw} label="Reset" color="bg-slate-100 hover:bg-slate-200 text-slate-600 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-400 ml-auto" disabled={isBusy} testid={`sim-reset-${r.id}`} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </AdminCard>
  );
};

const ProjectsSection = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState({});

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/demo-tools/projects`);
      setItems(r.data?.items || []);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const act = async (pid, mid, action) => {
    const key = `${pid}_${mid}_${action}`;
    setBusy(prev => ({ ...prev, [key]: true }));
    try {
      const url = mid
        ? `${API}/admin/demo-tools/projects/${pid}/milestones/${mid}/${action}`
        : `${API}/admin/demo-tools/projects/${pid}/${action}`;
      await axios.post(url, {});
      await load();
    } catch (e) {
      window.alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setBusy(prev => ({ ...prev, [key]: false }));
    }
  };

  return (
    <AdminCard
      title={<div className="flex items-center gap-2"><Layers className="w-4 h-4 text-purple-500" /> Simulator proiecte (4 milestone-uri)</div>}
      action={<AdminBtn variant="secondary" onClick={load}><RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /></AdminBtn>}
    >
      {items.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm italic">Niciun proiect cu milestone-uri</div>
      ) : (
        <div className="space-y-3 max-h-[600px] overflow-y-auto" data-testid="demo-tools-projects-list">
          {items.map(p => (
            <div key={p.id} className="rounded-xl border border-slate-200 dark:border-slate-700 p-3" data-testid={`demo-proj-${p.id}`}>
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <span className="font-semibold text-sm text-slate-800 dark:text-slate-200">{p.name}</span>
                <span className="text-[10px] text-emerald-700 dark:text-emerald-400 font-semibold inline-flex items-center gap-1">
                  <Wallet className="w-3 h-3" /> {p.total_budget} RON
                </span>
                <button
                  onClick={() => { if (window.confirm("Reset toate milestone-urile la pending_funding?")) act(p.id, null, "sim-reset"); }}
                  className="ml-auto inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
                  data-testid={`proj-reset-${p.id}`}
                >
                  <RotateCcw className="w-3 h-3" /> Reset proiect
                </button>
              </div>
              <div className="grid sm:grid-cols-2 gap-2">
                {p.milestones.map((m) => {
                  const k = `${p.id}_${m.id}`;
                  return (
                    <div key={m.id} className="rounded-lg border border-slate-100 dark:border-slate-800 p-2 text-xs">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="font-medium text-slate-700 dark:text-slate-300 truncate">{m.name}</span>
                        <span className="text-[10px] text-slate-400">{m.pct}% · {m.amount} RON</span>
                        <span className={`ml-auto px-1.5 py-0.5 rounded text-[9px] uppercase font-bold ${MS_STATUS_COLOR[m.status] || ""}`}>{m.status}</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {m.status === "pending_funding" && (
                          <ActionBtn onClick={() => act(p.id, m.id, "sim-fund")} icon={CreditCard} label="Finanțează" color="bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:hover:bg-emerald-500/25 dark:text-emerald-300" disabled={busy[`${k}_sim-fund`]} testid={`ms-fund-${m.id}`} />
                        )}
                        {m.status === "funded" && (
                          <ActionBtn onClick={() => act(p.id, m.id, "sim-release")} icon={ShieldCheck} label="Eliberează (95/5)" color="bg-emerald-600 hover:bg-emerald-700 text-white" disabled={busy[`${k}_sim-release`]} testid={`ms-release-${m.id}`} />
                        )}
                        {m.status === "warranty_hold" && (
                          <ActionBtn onClick={() => act(p.id, m.id, "sim-warranty-fast-forward")} icon={FastForward} label="Skip 30 zile" color="bg-purple-50 hover:bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:hover:bg-purple-500/25 dark:text-purple-300" disabled={busy[`${k}_sim-warranty-fast-forward`]} testid={`ms-warranty-ff-${m.id}`} />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </AdminCard>
  );
};

export const AdminDemoTimeMachine = () => (
  <div className="space-y-4" data-testid="admin-demo-time-machine">
    <div className="rounded-xl border border-amber-200 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 p-3 text-xs text-amber-900 dark:text-amber-200 flex items-start gap-2" data-testid="demo-tools-disclaimer">
      <Zap className="w-4 h-4 mt-0.5 shrink-0" />
      <div>
        <div className="font-bold mb-0.5">Demo Payment Time Machine — bypass total al rolurilor</div>
        <div>Aici simulezi întreg ciclul plății (Stripe demo → escrow → eliberare 95/5 → garanție → dispute) fără bani reali. Toate acțiunile sunt loggate cu flag <code>demo_simulated:true</code> în audit log.</div>
      </div>
    </div>
    <RequestsSection />
    <ProjectsSection />
  </div>
);

export default AdminDemoTimeMachine;
