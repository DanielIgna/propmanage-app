// Project Workspace (ClickUp-style) — viewable by designer (PM), client, and assigned specialists
import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { motion } from "framer-motion";
import {
  ArrowLeft, Plus, Users, CheckCircle2, Clock, AlertTriangle, MessageSquare,
  Trash2, X, Building2, Palette, Send, ListChecks, Loader2, Flag,
  Wallet, Calendar, Paperclip, Image as ImageIcon, ShieldCheck, Hourglass, AlertOctagon,
  Sparkles,
} from "lucide-react";
import { useAuth } from "../auth";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_COLS = [
  { id: "todo", label: "De făcut", icon: ListChecks, color: "stone" },
  { id: "in_progress", label: "În lucru", icon: Loader2, color: "amber" },
  { id: "review", label: "Verificare", icon: AlertTriangle, color: "cyan" },
  { id: "done", label: "Finalizate", icon: CheckCircle2, color: "emerald" },
];
const PRIORITY = {
  low: { label: "Scăzut", color: "stone" },
  normal: { label: "Normal", color: "white" },
  high: { label: "Înalt", color: "amber" },
  urgent: { label: "Urgent", color: "red" },
};

export const ProjectWorkspace = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("tasks");
  const [newTaskOpen, setNewTaskOpen] = useState(false);
  const [addMemberOpen, setAddMemberOpen] = useState(false);
  const [taskDetail, setTaskDetail] = useState(null);

  const load = async () => {
    try {
      const [p, t] = await Promise.all([
        axios.get(`${API}/projects/${id}`),
        axios.get(`${API}/projects/${id}/tasks`),
      ]);
      setProject(p.data);
      setTasks(t.data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Nu ai acces sau proiectul nu există.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [id]);

  if (loading) return <div className="min-h-screen flex items-center justify-center text-stone-400">Se încarcă proiectul...</div>;
  if (error) return (
    <div className="min-h-screen flex items-center justify-center flex-col gap-3 px-6 text-center">
      <AlertTriangle className="w-10 h-10 text-amber-400" />
      <div className="text-stone-300">{error}</div>
      <button onClick={() => navigate(-1)} className="px-4 py-2 bg-white/5 rounded-full text-sm" data-testid="back-btn">Înapoi</button>
    </div>
  );

  const isDesigner = project.designer_id === user?.id;
  const isClient = project.client_id === user?.id;
  const myMember = (project.members || []).find(m => m.user_id === user?.id);
  const role = isDesigner ? "designer" : (isClient ? "client" : (myMember?.role || "guest"));

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100">
      <header className="border-b border-white/5 sticky top-0 z-30 bg-[#0a0a0b]/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-3 flex-wrap">
          <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-sm text-stone-300 hover:text-white" data-testid="proj-back">
            <ArrowLeft className="w-4 h-4" />Înapoi
          </button>
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30">PROIECT · {role.toUpperCase()}</span>
            <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded-full border ${
              project.status === "active" ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" :
              project.status === "completed" ? "bg-blue-500/15 text-blue-300 border-blue-500/30" :
              "bg-stone-500/15 text-stone-300 border-stone-500/30"
            }`}>{project.status}</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        {/* Title block */}
        <div className="glass-strong rounded-3xl p-5 sm:p-6">
          <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-1">Proiect coordonat de {project.designer_name}</div>
          <h1 className="font-serif text-2xl sm:text-3xl mb-2" data-testid="proj-title">{project.name}</h1>
          {project.description && <p className="text-sm text-stone-400 leading-relaxed mb-3">{project.description}</p>}
          <div className="flex flex-wrap gap-2 text-[11px]">
            <span className="px-2 py-1 rounded-full bg-white/5 text-stone-300 flex items-center gap-1">
              <Building2 className="w-3 h-3 text-[#d4ff3a]" />Client: {project.client_name}
            </span>
            {project.style && (
              <span className="px-2 py-1 rounded-full bg-purple-500/10 text-purple-300 flex items-center gap-1 capitalize">
                <Palette className="w-3 h-3" />{project.style}
              </span>
            )}
            <button
              onClick={() => isDesigner ? setAddMemberOpen(true) : setTab("members")}
              className={`px-2 py-1 rounded-full bg-white/5 text-stone-300 flex items-center gap-1 transition ${isDesigner ? "hover:bg-purple-500/20 hover:text-purple-200 hover:border hover:border-purple-500/40 cursor-pointer" : ""}`}
              data-testid="header-members-chip"
              title={isDesigner ? "Click pentru a adăuga un membru nou" : "Vezi echipa"}>
              <Users className="w-3 h-3" />{(project.members?.length || 0) + 1} membri
              {isDesigner && <Plus className="w-3 h-3 ml-0.5 text-[#d4ff3a]" />}
            </button>
            <span className="px-2 py-1 rounded-full bg-white/5 text-stone-300 flex items-center gap-1">
              <ListChecks className="w-3 h-3" />{tasks.length} task-uri · {tasks.filter(t => t.status === "done").length} done
            </span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 text-sm flex-wrap items-center">
          {["tasks", "payments", "timeline", "members", "activity"].map(k => (
            <button key={k} onClick={() => setTab(k)}
              className={`px-4 py-2 rounded-full transition ${tab === k ? "bg-[#d4ff3a] text-black font-medium" : "bg-white/5 text-stone-400 hover:bg-white/10"}`}
              data-testid={`proj-tab-${k}`}>
              {{ tasks: "Task-uri", payments: "Plăți", timeline: "Timeline", members: "Echipa", activity: "Activitate" }[k]}
            </button>
          ))}
          {/* Quick action for designer on ANY tab */}
          {isDesigner && (
            <button
              onClick={() => setAddMemberOpen(true)}
              className="ml-auto px-4 py-2 rounded-full bg-gradient-to-r from-purple-500/20 to-pink-500/20 hover:from-purple-500/30 hover:to-pink-500/30 text-purple-200 border border-purple-500/40 text-xs flex items-center gap-1.5 font-medium transition"
              data-testid="quick-add-member-btn"
              title="Adaugă specialist în proiect">
              <Plus className="w-3.5 h-3.5" />+ Membru
            </button>
          )}
        </div>

        {tab === "tasks" && (
          <TasksBoard tasks={tasks} isDesigner={isDesigner} project={project}
            onNewTask={() => setNewTaskOpen(true)}
            onOpenTask={(t) => setTaskDetail(t)}
            onUpdate={load} />
        )}

        {tab === "payments" && (
          <PaymentsTab project={project} isDesigner={isDesigner} isClient={isClient} onUpdate={load} />
        )}

        {tab === "timeline" && (
          <TimelineTab tasks={tasks} project={project} onOpenTask={(t) => setTaskDetail(t)} />
        )}

        {tab === "members" && (
          <MembersList project={project} isDesigner={isDesigner}
            onAddMember={() => setAddMemberOpen(true)}
            onRemoved={load} />
        )}

        {tab === "activity" && (
          <ActivityFeed tasks={tasks} />
        )}
      </main>

      {newTaskOpen && (
        <NewTaskModal project={project} onClose={() => setNewTaskOpen(false)} onCreated={load} />
      )}
      {addMemberOpen && (
        <AddMemberModal project={project} onClose={() => setAddMemberOpen(false)} onAdded={load} />
      )}
      {taskDetail && (
        <TaskDetailModal task={taskDetail} project={project} onClose={() => setTaskDetail(null)} onUpdate={load} currentUser={user} />
      )}
    </div>
  );
};

// ============= TASKS BOARD (with HTML5 drag & drop) =============
const TasksBoard = ({ tasks, isDesigner, project, onNewTask, onOpenTask, onUpdate }) => {
  const [dragOver, setDragOver] = useState(null);
  const grouped = STATUS_COLS.reduce((acc, c) => ({ ...acc, [c.id]: tasks.filter(t => t.status === c.id) }), {});

  const handleDrop = async (e, colId) => {
    e.preventDefault();
    setDragOver(null);
    const taskId = e.dataTransfer.getData("text/plain");
    const task = tasks.find(t => t.id === taskId);
    if (!task || task.status === colId) return;
    // Permission: designer OR assignee can change status
    const canChange = isDesigner || task.assignee_id === project.designer_id;
    try {
      await axios.patch(`${API}/tasks/${taskId}`, { status: colId });
      onUpdate();
    } catch (err) {
      alert(err?.response?.data?.detail || "Mutarea task-ului nu este permisă (doar designerul sau persoana asignată poate schimba status-ul).");
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center flex-wrap gap-2">
        <div className="text-[11px] text-stone-500 italic hidden sm:block">💡 Trage task-urile între coloane (drag & drop)</div>
        {isDesigner && (
          <button onClick={onNewTask} className="btn-accent px-4 py-2 rounded-full text-sm flex items-center gap-1.5 ml-auto" data-testid="new-task-btn">
            <Plus className="w-4 h-4" />Task nou
          </button>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {STATUS_COLS.map(col => {
          const Icon = col.icon;
          return (
            <div key={col.id}
              onDragOver={e => { e.preventDefault(); setDragOver(col.id); }}
              onDragLeave={() => setDragOver(prev => prev === col.id ? null : prev)}
              onDrop={e => handleDrop(e, col.id)}
              className={`bg-white/[0.03] border rounded-2xl p-3 transition-all ${dragOver === col.id ? "border-[#d4ff3a]/60 bg-[#d4ff3a]/5 scale-[1.01]" : "border-white/5"}`}
              data-testid={`col-${col.id}`}>
              <div className={`flex items-center gap-2 mb-3 text-${col.color}-300`}>
                <Icon className="w-4 h-4" />
                <div className="text-[10px] uppercase tracking-wider font-medium">{col.label}</div>
                <span className="ml-auto text-xs text-stone-500">{grouped[col.id].length}</span>
              </div>
              <div className="space-y-2 min-h-[60px]">
                {grouped[col.id].length === 0 ? (
                  <div className="text-[11px] text-stone-600 italic py-2 text-center">— gol —</div>
                ) : grouped[col.id].map(t => (
                  <div key={t.id}
                    draggable
                    onDragStart={e => e.dataTransfer.setData("text/plain", t.id)}
                    onClick={() => onOpenTask(t)}
                    className="bg-white/5 hover:bg-white/10 border border-white/5 rounded-xl p-3 transition group cursor-grab active:cursor-grabbing"
                    data-testid={`task-card-${t.id}`}>
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="text-sm font-medium leading-tight">{t.title}</div>
                      {t.priority && t.priority !== "normal" && (
                        <Flag className={`w-3 h-3 shrink-0 text-${PRIORITY[t.priority].color}-400`} />
                      )}
                    </div>
                    {t.assignee_name && (
                      <div className="text-[10px] uppercase tracking-wider text-stone-500 mt-1">→ {t.assignee_name}</div>
                    )}
                    <div className="flex items-center gap-2 mt-1.5">
                      {t.attachments?.length > 0 && (
                        <div className="text-[10px] text-stone-500 flex items-center gap-1">
                          <Paperclip className="w-2.5 h-2.5" />{t.attachments.length}
                        </div>
                      )}
                      {t.comments_count > 0 && (
                        <div className="text-[10px] text-stone-500 flex items-center gap-1">
                          <MessageSquare className="w-2.5 h-2.5" />{t.comments_count}
                        </div>
                      )}
                      {t.due_date && (
                        <div className="text-[10px] text-stone-500 flex items-center gap-1 ml-auto">
                          <Calendar className="w-2.5 h-2.5" />{new Date(t.due_date).toLocaleDateString("ro-RO", { day: "2-digit", month: "short" })}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ============= PAYMENTS TAB (milestone-based escrow + 30-day warranty) =============
const MILESTONE_STATE = {
  pending_funding: { label: "Așteaptă plată", color: "stone", icon: Wallet },
  funded: { label: "În escrow", color: "amber", icon: ShieldCheck },
  released: { label: "Eliberat", color: "emerald", icon: CheckCircle2 },
  warranty_hold: { label: "Garanție 30 zile", color: "cyan", icon: Hourglass },
  warranty_released: { label: "Plătit final", color: "emerald", icon: CheckCircle2 },
};

const PaymentsTab = ({ project, isDesigner, isClient, onUpdate }) => {
  const milestones = project.milestones || [];
  const [showInit, setShowInit] = useState(false);
  const [busy, setBusy] = useState(null);
  const [claimFor, setClaimFor] = useState(null);

  const fund = async (mid) => {
    if (!window.confirm("Confirmi plata acestei tranșe din portofelul tău?")) return;
    setBusy(mid);
    try {
      await axios.post(`${API}/projects/${project.id}/milestones/${mid}/fund`, { confirm: true });
      onUpdate();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare la plată"); }
    finally { setBusy(null); }
  };
  const release = async (mid, isFinal) => {
    if (!window.confirm(isFinal
      ? "Marchezi lucrarea ca finalizată. Tranșa finală va intra în perioada de garanție 30 zile (clientul poate raporta probleme)."
      : "Eliberezi tranșa către specialiști?")) return;
    setBusy(mid);
    try {
      await axios.post(`${API}/projects/${project.id}/milestones/${mid}/release`, {});
      onUpdate();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare la eliberare"); }
    finally { setBusy(null); }
  };
  const resolve = async (mid) => {
    if (!window.confirm("Confirmi că problema a fost rezolvată? Banii se eliberează acum specialiștilor.")) return;
    setBusy(mid);
    try {
      await axios.post(`${API}/projects/${project.id}/milestones/${mid}/warranty-resolve`);
      onUpdate();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); }
    finally { setBusy(null); }
  };

  if (milestones.length === 0) {
    if (!isDesigner) {
      return (
        <div className="glass-strong rounded-3xl p-6 text-center text-stone-400">
          <Wallet className="w-10 h-10 mx-auto mb-3 opacity-30" />
          Designerul nu a configurat încă planul de plăți pentru acest proiect.
        </div>
      );
    }
    return (
      <>
        <div className="glass-strong rounded-3xl p-6 text-center">
          <Wallet className="w-10 h-10 mx-auto mb-3 text-[#d4ff3a]" />
          <h3 className="font-serif text-xl mb-2">Setează planul de plăți</h3>
          <p className="text-sm text-stone-400 mb-4 max-w-sm mx-auto">
            4 tranșe egale de 25% — avans, început, 75% finalizare, finalizare (garanție 30 zile).
          </p>
          <button onClick={() => setShowInit(true)} className="btn-accent px-5 py-2.5 rounded-full text-sm font-medium" data-testid="init-milestones-btn">
            Configurează tranșele
          </button>
        </div>
        {showInit && <InitMilestonesModal project={project} onClose={() => setShowInit(false)} onCreated={onUpdate} />}
      </>
    );
  }

  const totalFunded = milestones.filter(m => ["funded", "released", "warranty_hold", "warranty_released"].includes(m.status)).reduce((s, m) => s + m.amount, 0);
  const totalReleased = milestones.filter(m => ["released", "warranty_released"].includes(m.status)).reduce((s, m) => s + m.amount, 0);

  return (
    <div className="space-y-4">
      {/* Progress overview */}
      <div className="glass-strong rounded-3xl p-5">
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-stone-500">Buget total</div>
            <div className="font-serif text-xl text-[#d4ff3a]">{project.total_budget?.toFixed(0)} RON</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-stone-500">Plătit în escrow</div>
            <div className="font-serif text-xl text-amber-300">{totalFunded.toFixed(0)} RON</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-stone-500">Eliberat</div>
            <div className="font-serif text-xl text-emerald-300">{totalReleased.toFixed(0)} RON</div>
          </div>
        </div>
        <div className="h-2 bg-white/5 rounded-full overflow-hidden flex">
          {milestones.map(m => (
            <div key={m.id}
              className={`h-full ${
                m.status === "warranty_released" || m.status === "released" ? "bg-emerald-400" :
                m.status === "warranty_hold" ? "bg-cyan-400" :
                m.status === "funded" ? "bg-amber-400" :
                "bg-stone-700"
              }`}
              style={{ width: `${m.pct}%` }}
              title={`${m.name}: ${m.status}`}
            />
          ))}
        </div>
      </div>

      {/* Renegotiation panel (designer or client can propose) */}
      <RenegotiatePanel project={project} isDesigner={isDesigner} isClient={isClient} onUpdate={onUpdate} />

      {/* Milestone cards */}
      <div className="space-y-2.5">
        {milestones.map((m, idx) => {
          const stateInfo = MILESTONE_STATE[m.status] || MILESTONE_STATE.pending_funding;
          const Icon = stateInfo.icon;
          const prevReleased = idx === 0 || ["released", "warranty_hold", "warranty_released"].includes(milestones[idx - 1]?.status);
          const daysLeft = m.warranty_release_at ? Math.max(0, Math.ceil((new Date(m.warranty_release_at) - new Date()) / 86400000)) : null;
          return (
            <div key={m.id}
              className={`glass-strong rounded-2xl p-4 border ${m.warranty_dispute_open ? "border-red-500/50" : "border-white/10"}`}
              data-testid={`milestone-${idx + 1}`}>
              <div className="flex items-start justify-between gap-3 mb-2 flex-wrap">
                <div className="flex items-center gap-3 min-w-0">
                  <div className={`w-9 h-9 rounded-xl bg-${stateInfo.color}-500/15 border border-${stateInfo.color}-500/30 flex items-center justify-center shrink-0`}>
                    <Icon className={`w-4 h-4 text-${stateInfo.color}-300`} />
                  </div>
                  <div className="min-w-0">
                    <div className="text-[10px] uppercase tracking-wider text-stone-500">Tranșa {idx + 1}/4 · {m.pct}%</div>
                    <div className="font-medium text-sm">{m.name}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-${stateInfo.color}-500/15 text-${stateInfo.color}-300 border border-${stateInfo.color}-500/30`}>
                    {stateInfo.label}
                  </span>
                  <span className="font-serif text-lg text-[#d4ff3a]">{m.amount} RON</span>
                </div>
              </div>
              <p className="text-xs text-stone-400 leading-relaxed mb-3">{m.description}</p>

              {m.warranty_dispute_open && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 mb-3 flex items-start gap-2">
                  <AlertOctagon className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <div className="flex-1 text-xs">
                    <div className="font-medium text-red-300 mb-1">Reclamație garanție deschisă</div>
                    <div className="text-stone-400">{m.warranty_dispute_reason}</div>
                  </div>
                </div>
              )}

              {m.status === "warranty_hold" && !m.warranty_dispute_open && daysLeft !== null && (
                <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-3 mb-3 text-xs flex items-center gap-2">
                  <Hourglass className="w-3.5 h-3.5 text-cyan-300" />
                  <span className="text-cyan-200">Eliberare automată în <b>{daysLeft} zile</b> (fără reclamații)</span>
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                {/* Client actions */}
                {isClient && m.status === "pending_funding" && prevReleased && (
                  <button onClick={() => fund(m.id)} disabled={busy === m.id}
                    className="btn-accent px-4 py-2 rounded-full text-xs font-medium disabled:opacity-50 flex items-center gap-1.5"
                    data-testid={`fund-${idx + 1}`}>
                    <Wallet className="w-3.5 h-3.5" />{busy === m.id ? "..." : `Plătește ${m.amount} RON`}
                  </button>
                )}
                {isClient && m.status === "pending_funding" && !prevReleased && (
                  <span className="text-[11px] text-stone-500 italic">Așteaptă eliberarea tranșei anterioare.</span>
                )}
                {isClient && m.status === "warranty_hold" && !m.warranty_dispute_open && (
                  <button onClick={() => setClaimFor(m)}
                    className="px-4 py-2 rounded-full text-xs bg-red-500/15 hover:bg-red-500/25 text-red-300 border border-red-500/40 flex items-center gap-1.5"
                    data-testid={`claim-${idx + 1}`}>
                    <AlertOctagon className="w-3.5 h-3.5" />Raportează problemă
                  </button>
                )}
                {(isClient || isDesigner) && m.status === "warranty_hold" && m.warranty_dispute_open && (
                  <button onClick={() => resolve(m.id)} disabled={busy === m.id}
                    className="px-4 py-2 rounded-full text-xs bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5"
                    data-testid={`resolve-${idx + 1}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" />Marchează rezolvat
                  </button>
                )}

                {/* Designer actions */}
                {isDesigner && m.status === "funded" && (
                  <button onClick={() => release(m.id, m.is_final)} disabled={busy === m.id}
                    className="px-4 py-2 rounded-full text-xs bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5"
                    data-testid={`release-${idx + 1}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" />{m.is_final ? "Marchează finalizat (intră garanție)" : "Eliberează către specialiști"}
                  </button>
                )}

                {/* Timestamps */}
                {m.funded_at && <span className="text-[10px] text-stone-500 ml-auto">Finanțat: {new Date(m.funded_at).toLocaleDateString("ro-RO")}</span>}
                {m.released_at && <span className="text-[10px] text-emerald-400/70">Eliberat: {new Date(m.released_at).toLocaleDateString("ro-RO")}</span>}
              </div>
            </div>
          );
        })}
      </div>

      {claimFor && <WarrantyClaimModal project={project} milestone={claimFor} onClose={() => setClaimFor(null)} onSubmitted={onUpdate} />}
    </div>
  );
};

// ============= MILESTONE RENEGOTIATION =============
const RenegotiatePanel = ({ project, isDesigner, isClient, onUpdate }) => {
  const [proposals, setProposals] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const milestones = project.milestones || [];
  const unfunded = milestones.filter(m => m.status === "pending_funding");

  const load = () => axios.get(`${API}/projects/${project.id}/milestones/renegotiate`).then(r => setProposals(r.data.proposals || [])).catch(() => {});
  React.useEffect(() => { load(); }, [project.id, project.updated_at]);

  const pending = proposals.filter(p => p.status === "pending");
  const history = proposals.filter(p => p.status !== "pending").slice(-3);

  const respond = async (proposalId, accept) => {
    const note = accept ? null : (window.prompt("Motiv respingere (opțional):") || null);
    if (accept && !window.confirm("Confirmi noua împărțire a tranșelor? Această acțiune este definitivă.")) return;
    try {
      await axios.post(`${API}/projects/${project.id}/milestones/renegotiate/${proposalId}/respond`, { accept, note });
      await load(); onUpdate();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); }
  };

  if (unfunded.length < 2 && pending.length === 0 && history.length === 0) return null;

  return (
    <>
      <div className="glass-strong rounded-2xl p-4" data-testid="renegotiate-panel">
        <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-300" />
            <span className="text-sm font-medium">Modificare tranșe</span>
            {pending.length > 0 && <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">{pending.length} în așteptare</span>}
          </div>
          {(isClient || isDesigner) && unfunded.length >= 2 && (
            <button onClick={() => setShowModal(true)} className="px-3 py-1.5 rounded-full text-xs bg-white/5 hover:bg-white/10 border border-white/10 flex items-center gap-1.5" data-testid="renegotiate-open-btn">
              Cere modificare
            </button>
          )}
        </div>

        {pending.map(p => (
          <PendingProposalCard key={p.id} proposal={p} canRespond={(isClient && p.proposed_by_role === "designer") || (isDesigner && p.proposed_by_role === "client")} onRespond={respond} />
        ))}

        {history.length > 0 && (
          <details className="mt-2">
            <summary className="text-[11px] text-stone-500 cursor-pointer hover:text-stone-300">Istoric propuneri ({history.length})</summary>
            <div className="mt-2 space-y-1">
              {history.map(p => (
                <div key={p.id} className="text-[11px] text-stone-400 flex justify-between bg-white/[0.03] rounded-lg p-2">
                  <span>{p.proposed_by_name} → {p.pcts.map(x => `${x}%`).join("/")} </span>
                  <span className={p.status === "accepted" ? "text-emerald-400" : "text-red-400"}>{p.status === "accepted" ? "Acceptată" : p.status === "rejected" ? "Respinsă" : "Anulată"}</span>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>

      {showModal && <RenegotiateModal project={project} unfunded={unfunded} onClose={() => setShowModal(false)} onCreated={() => { setShowModal(false); load(); onUpdate(); }} />}
    </>
  );
};

const PendingProposalCard = ({ proposal, canRespond, onRespond }) => (
  <div className="bg-amber-500/5 border border-amber-500/30 rounded-xl p-3 mt-2" data-testid={`proposal-${proposal.id}`}>
    <div className="flex justify-between items-center text-xs mb-2">
      <span><b>{proposal.proposed_by_name}</b> propune o nouă împărțire</span>
      <span className="text-[10px] text-stone-500">{new Date(proposal.created_at).toLocaleString("ro-RO")}</span>
    </div>
    {proposal.note && <div className="text-xs italic text-stone-300 mb-2">"{proposal.note}"</div>}
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 mb-2">
      {proposal.preview.map((v, i) => (
        <div key={i} className="bg-black/30 rounded-lg p-2 text-center">
          <div className="text-[9px] text-stone-500 uppercase truncate">{v.name}</div>
          <div className="font-serif text-sm text-amber-200">{v.pct}%</div>
          <div className="text-[10px] text-stone-400">{v.amount} RON</div>
        </div>
      ))}
    </div>
    {canRespond ? (
      <div className="flex gap-2 mt-2">
        <button onClick={() => onRespond(proposal.id, true)} className="flex-1 btn-accent py-1.5 rounded-full text-xs font-medium" data-testid={`accept-proposal-${proposal.id}`}>Acceptă</button>
        <button onClick={() => onRespond(proposal.id, false)} className="px-3 py-1.5 rounded-full text-xs bg-red-500/15 hover:bg-red-500/25 text-red-300 border border-red-500/40" data-testid={`reject-proposal-${proposal.id}`}>Respinge</button>
      </div>
    ) : (
      <div className="text-[11px] text-stone-500 italic mt-1">Așteptăm răspunsul celeilalte părți...</div>
    )}
  </div>
);

const RenegotiateModal = ({ project, unfunded, onClose, onCreated }) => {
  const [pcts, setPcts] = useState(() => {
    const eq = +(100 / unfunded.length).toFixed(2);
    const arr = Array(unfunded.length).fill(eq);
    // Adjust last to make sum exact 100
    arr[arr.length - 1] = +(100 - eq * (unfunded.length - 1)).toFixed(2);
    return arr;
  });
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const total = pcts.reduce((s, p) => s + parseFloat(p || 0), 0);
  const valid = Math.abs(total - 100) < 0.05 && pcts.every(p => parseFloat(p) > 0);
  const remaining = unfunded.reduce((s, m) => s + m.amount, 0);

  const submit = async (e) => {
    e.preventDefault();
    if (!valid) return;
    setBusy(true);
    try {
      await axios.post(`${API}/projects/${project.id}/milestones/renegotiate`, {
        pcts: pcts.map(p => parseFloat(p)),
        note: note || null,
      });
      onCreated();
    } catch (err) { alert(err?.response?.data?.detail || "Eroare"); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-end sm:items-center justify-center p-3" onClick={onClose}>
      <form onSubmit={submit} onClick={e => e.stopPropagation()} className="glass-strong rounded-3xl p-6 max-w-md w-full" data-testid="renegotiate-modal">
        <h3 className="font-serif text-2xl mb-2">Modifică tranșe</h3>
        <p className="text-xs text-stone-400 mb-4">
          Buget rămas: <b className="text-[#d4ff3a]">{remaining.toFixed(0)} RON</b> ({unfunded.length} tranșe nefinanțate).<br />
          Trimite o propunere către cealaltă parte. Va trebui acceptată ca să intre în vigoare.
        </p>

        <div className="space-y-2 mb-4">
          {unfunded.map((m, i) => {
            const pct = parseFloat(pcts[i] || 0);
            const amount = remaining * pct / 100;
            return (
              <div key={m.id} className="flex items-center gap-2 bg-white/5 rounded-xl p-2.5">
                <span className="text-[10px] uppercase tracking-wider text-stone-500 w-24 truncate">{m.name}</span>
                <input
                  type="number"
                  step="0.01" min="0.01" max="100"
                  value={pcts[i]}
                  onChange={e => setPcts(p => p.map((v, j) => j === i ? e.target.value : v))}
                  className="w-20 px-2 py-1 bg-white/5 rounded-lg text-sm text-center"
                  data-testid={`renegotiate-pct-${i}`}
                />
                <span className="text-xs text-stone-500">%</span>
                <span className="ml-auto text-sm text-[#d4ff3a]">{amount.toFixed(0)} RON</span>
              </div>
            );
          })}
        </div>

        <div className={`flex items-center justify-between text-xs mb-4 px-3 py-2 rounded-lg ${valid ? "bg-emerald-500/10 text-emerald-300" : "bg-red-500/10 text-red-300"}`}>
          <span>Sumă procente:</span>
          <b>{total.toFixed(2)}% {valid ? "✓" : `(trebuie 100%)`}</b>
        </div>

        <textarea
          value={note}
          onChange={e => setNote(e.target.value)}
          placeholder="Notă opțională (ex: 'Mărim avansul pentru a comanda materialele mai devreme')"
          rows={2}
          className="w-full bg-white/5 rounded-xl px-3 py-2 text-sm mb-4"
          data-testid="renegotiate-note"
          maxLength={1000}
        />

        <div className="flex gap-2">
          <button type="button" onClick={onClose} className="flex-1 px-4 py-2.5 rounded-full bg-white/5 hover:bg-white/10 text-sm">Anulează</button>
          <button type="submit" disabled={!valid || busy} className="flex-1 btn-accent py-2.5 rounded-full text-sm font-medium disabled:opacity-50" data-testid="renegotiate-submit">
            {busy ? "..." : "Trimite propunere"}
          </button>
        </div>
      </form>
    </div>
  );
};

const InitMilestonesModal = ({ project, onClose, onCreated }) => {
  const [budget, setBudget] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await axios.post(`${API}/projects/${project.id}/milestones/init`, { total_budget: parseFloat(budget) });
      onCreated(); onClose();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-end sm:items-center justify-center p-3" onClick={onClose}>
      <form onSubmit={submit} onClick={e => e.stopPropagation()}
        className="bg-stone-950 border border-white/10 rounded-3xl p-5 w-full max-w-md space-y-3" data-testid="init-milestones-modal">
        <h3 className="font-serif text-xl">Configurează plățile</h3>
        <p className="text-xs text-stone-400">Bugetul se împarte automat în 4 tranșe egale (25% fiecare). Tranșa finală are 30 zile de garanție.</p>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-stone-400 mb-1 block">Buget total (RON)</label>
          <input type="number" required min="100" step="100" value={budget} onChange={e => setBudget(e.target.value)}
            placeholder="ex: 12000"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="init-budget-input" />
        </div>
        {budget && parseFloat(budget) > 0 && (
          <div className="bg-white/5 rounded-xl p-3 text-xs space-y-1">
            <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-1">Previzualizare tranșe</div>
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="flex justify-between">
                <span>Tranșa {i} (25%)</span>
                <span className="text-[#d4ff3a]">{(parseFloat(budget) / 4).toFixed(0)} RON</span>
              </div>
            ))}
          </div>
        )}
        <div className="flex gap-2 pt-2">
          <button type="button" onClick={onClose} className="flex-1 py-2 bg-white/5 rounded-full text-sm">Anulează</button>
          <button type="submit" disabled={busy || !budget} className="flex-1 py-2 btn-accent rounded-full text-sm disabled:opacity-40" data-testid="init-milestones-submit">
            {busy ? "..." : "Setează planul"}
          </button>
        </div>
      </form>
    </div>
  );
};

const WarrantyClaimModal = ({ project, milestone, onClose, onSubmitted }) => {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await axios.post(`${API}/projects/${project.id}/milestones/${milestone.id}/warranty-claim`, { reason });
      onSubmitted(); onClose();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-end sm:items-center justify-center p-3" onClick={onClose}>
      <form onSubmit={submit} onClick={e => e.stopPropagation()}
        className="bg-stone-950 border border-red-500/40 rounded-3xl p-5 w-full max-w-md space-y-3" data-testid="warranty-claim-modal">
        <h3 className="font-serif text-xl text-red-300">Raportează o problemă de garanție</h3>
        <p className="text-xs text-stone-400">Descrie clar problema apărută. Specialiștii vor fi notificați automat. Banii rămân blocați până la rezolvare.</p>
        <textarea required rows={4} minLength={10} value={reason} onChange={e => setReason(e.target.value)}
          placeholder="Ex: După 5 zile de la finalizare, 2 plăci de gresie din baie s-au crăpat și un întrerupător nu mai funcționează corect..."
          className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="warranty-reason" />
        <div className="flex gap-2 pt-2">
          <button type="button" onClick={onClose} className="flex-1 py-2 bg-white/5 rounded-full text-sm">Anulează</button>
          <button type="submit" disabled={busy || reason.length < 10}
            className="flex-1 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-200 border border-red-500/40 rounded-full text-sm disabled:opacity-40" data-testid="warranty-claim-submit">
            {busy ? "..." : "Trimite reclamația"}
          </button>
        </div>
      </form>
    </div>
  );
};

// ============= TIMELINE TAB (simple chronological bar chart) =============
const TimelineTab = ({ tasks, project, onOpenTask }) => {
  const tasksWithDates = tasks.filter(t => t.due_date).sort((a, b) => (a.due_date || "").localeCompare(b.due_date || ""));
  const tasksWithoutDates = tasks.filter(t => !t.due_date);

  if (tasks.length === 0) return (
    <div className="glass-strong rounded-3xl p-6 text-center text-stone-400">
      <Calendar className="w-10 h-10 mx-auto mb-3 opacity-30" />Niciun task încă.
    </div>
  );

  // Determine date range
  const allDates = tasksWithDates.map(t => new Date(t.due_date));
  const startDates = tasksWithDates.map(t => new Date(t.created_at));
  const minDate = startDates.length ? new Date(Math.min(...startDates)) : new Date();
  const maxDate = allDates.length ? new Date(Math.max(...allDates)) : new Date();
  const totalSpan = Math.max(1, (maxDate - minDate) / 86400000) || 1;

  return (
    <div className="space-y-4">
      {tasksWithDates.length > 0 && (
        <div className="glass-strong rounded-3xl p-5" data-testid="timeline-chart">
          <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-4 flex justify-between">
            <span>{minDate.toLocaleDateString("ro-RO", { day: "numeric", month: "short" })}</span>
            <span>Timeline · {tasksWithDates.length} task-uri cu termen</span>
            <span>{maxDate.toLocaleDateString("ro-RO", { day: "numeric", month: "short" })}</span>
          </div>
          <div className="space-y-2">
            {tasksWithDates.map(t => {
              const start = new Date(t.created_at);
              const end = new Date(t.due_date);
              const startPct = Math.max(0, ((start - minDate) / 86400000) / totalSpan * 100);
              const widthPct = Math.max(3, ((end - start) / 86400000) / totalSpan * 100);
              const isDone = t.status === "done";
              const overdue = !isDone && end < new Date();
              return (
                <button key={t.id} onClick={() => onOpenTask(t)}
                  className="w-full text-left group" data-testid={`timeline-task-${t.id}`}>
                  <div className="flex items-center gap-3 hover:bg-white/5 rounded-xl p-2 transition">
                    <div className="text-xs w-32 sm:w-40 truncate text-stone-300">{t.title}</div>
                    <div className="flex-1 relative h-5 bg-white/[0.03] rounded-full overflow-hidden">
                      <div
                        className={`absolute top-0 h-full rounded-full ${
                          isDone ? "bg-emerald-400/70" : overdue ? "bg-red-400/70" :
                          t.status === "in_progress" ? "bg-amber-400/70" : "bg-stone-400/40"
                        }`}
                        style={{ left: `${startPct}%`, width: `${Math.min(100 - startPct, widthPct)}%` }}
                      />
                    </div>
                    <div className="text-[10px] text-stone-500 w-20 text-right shrink-0">
                      {new Date(t.due_date).toLocaleDateString("ro-RO", { day: "2-digit", month: "short" })}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
      {tasksWithoutDates.length > 0 && (
        <div className="glass-strong rounded-3xl p-5">
          <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-3">Fără termen · {tasksWithoutDates.length}</div>
          <div className="space-y-1.5">
            {tasksWithoutDates.map(t => (
              <button key={t.id} onClick={() => onOpenTask(t)}
                className="w-full text-left bg-white/[0.03] hover:bg-white/[0.07] rounded-xl px-3 py-2 text-sm flex items-center justify-between transition">
                <span>{t.title}</span>
                <span className="text-[10px] text-stone-500 capitalize">{t.status.replace("_", " ")}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ============= MEMBERS LIST =============
const MembersList = ({ project, isDesigner, onAddMember, onRemoved }) => {
  const allMembers = [
    { user_id: project.designer_id, name: project.designer_name, role: "designer", is_designer: true },
    ...(project.members || []),
  ];
  const remove = async (uid) => {
    if (!window.confirm("Sigur elimini acest membru?")) return;
    try {
      await axios.delete(`${API}/projects/${project.id}/members/${uid}`);
      onRemoved();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); }
  };
  return (
    <div className="glass-strong rounded-3xl p-5">
      <div className="flex justify-between items-center mb-4">
        <div className="text-[10px] uppercase tracking-wider text-stone-400">Echipa proiectului · {allMembers.length}</div>
        {isDesigner && (
          <button onClick={onAddMember} className="text-xs px-3 py-1.5 rounded-full bg-purple-500/15 hover:bg-purple-500/25 text-purple-300 border border-purple-500/40 flex items-center gap-1" data-testid="add-member-btn">
            <Plus className="w-3 h-3" />Adaugă specialist
          </button>
        )}
      </div>
      <div className="space-y-2">
        {allMembers.map(m => (
          <div key={m.user_id} className="bg-white/5 border border-white/5 rounded-2xl p-3 flex items-center gap-3" data-testid={`member-row-${m.user_id}`}>
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500/30 to-pink-500/30 flex items-center justify-center font-medium text-purple-200">
              {(m.name || "?").charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{m.name}</div>
              <div className="text-[10px] uppercase tracking-wider text-stone-500 capitalize">
                {m.is_designer ? "Coordonator (designer)" : m.role}
                {m.specialty && ` · ${m.specialty}`}
              </div>
            </div>
            {isDesigner && !m.is_designer && m.role !== "client" && (
              <button onClick={() => remove(m.user_id)} className="text-stone-500 hover:text-red-400 p-2" data-testid={`remove-${m.user_id}`}>
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

// ============= ACTIVITY FEED (recent tasks/updates) =============
const ActivityFeed = ({ tasks }) => {
  const sorted = [...tasks].sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || "")).slice(0, 20);
  return (
    <div className="glass-strong rounded-3xl p-5">
      <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-4">Activitate recentă</div>
      {sorted.length === 0 ? (
        <div className="text-sm text-stone-500 text-center py-6">Niciun task încă.</div>
      ) : (
        <div className="space-y-2">
          {sorted.map(t => (
            <div key={t.id} className="bg-white/5 border border-white/5 rounded-2xl p-3 text-sm flex items-center justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="font-medium truncate">{t.title}</div>
                <div className="text-[10px] uppercase tracking-wider text-stone-500 mt-1">
                  {t.status} · {t.assignee_name || "neasignat"} · {new Date(t.updated_at).toLocaleDateString("ro-RO")}
                </div>
              </div>
              <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${
                t.status === "done" ? "bg-emerald-500/15 text-emerald-300" :
                t.status === "in_progress" ? "bg-amber-500/15 text-amber-300" :
                "bg-stone-500/15 text-stone-300"
              }`}>{t.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ============= MODALS =============
const NewTaskModal = ({ project, onClose, onCreated }) => {
  const members = [
    { user_id: project.designer_id, name: project.designer_name },
    ...(project.members || []),
  ];
  const [form, setForm] = useState({ title: "", description: "", assignee_id: "", priority: "normal", due_date: "" });
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await axios.post(`${API}/projects/${project.id}/tasks`, { ...form, assignee_id: form.assignee_id || null });
      onCreated(); onClose();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-end sm:items-center justify-center p-3" onClick={onClose}>
      <motion.form initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} onSubmit={submit} onClick={e => e.stopPropagation()}
        className="bg-stone-950 border border-white/10 rounded-3xl p-5 w-full max-w-md space-y-3" data-testid="new-task-modal">
        <h3 className="font-serif text-xl mb-2">Task nou</h3>
        <input required placeholder="Titlu task..." value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="new-task-title" />
        <textarea rows={3} placeholder="Descriere (opțional)" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" />
        <select value={form.assignee_id} onChange={e => setForm({ ...form, assignee_id: e.target.value })}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="new-task-assignee">
          <option value="">— Neasignat —</option>
          {members.map(m => <option key={m.user_id} value={m.user_id}>{m.name} {m.specialty ? `(${m.specialty})` : ""}</option>)}
        </select>
        <div className="grid grid-cols-2 gap-2">
          <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm">
            <option value="low">Scăzut</option><option value="normal">Normal</option>
            <option value="high">Înalt</option><option value="urgent">Urgent</option>
          </select>
          <input type="date" value={form.due_date} onChange={e => setForm({ ...form, due_date: e.target.value })}
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" />
        </div>
        <div className="flex gap-2 pt-2">
          <button type="button" onClick={onClose} className="flex-1 py-2 bg-white/5 rounded-full text-sm">Anulează</button>
          <button type="submit" disabled={busy} className="flex-1 py-2 btn-accent rounded-full text-sm" data-testid="new-task-submit">
            {busy ? "..." : "Creează"}
          </button>
        </div>
      </motion.form>
    </div>
  );
};

const AddMemberModal = ({ project, onClose, onAdded }) => {
  const [specialists, setSpecialists] = useState([]);
  const [pick, setPick] = useState(null);
  const [specialty, setSpecialty] = useState("parchet");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    axios.get(`${API}/marketplace/specialists?verified_only=true&sort=rating`).then(r => setSpecialists(r.data || [])).catch(() => setSpecialists([]));
  }, []);
  const existing = new Set([
    project.designer_id, project.client_id,
    ...(project.members || []).map(m => m.user_id),
  ]);
  const available = specialists.filter(s => !existing.has(s.id));
  const submit = async () => {
    if (!pick) return;
    setBusy(true);
    try {
      await axios.post(`${API}/projects/${project.id}/members`, { user_id: pick, role: "specialist", specialty });
      onAdded(); onClose();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-end sm:items-center justify-center p-3" onClick={onClose}>
      <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} onClick={e => e.stopPropagation()}
        className="bg-stone-950 border border-white/10 rounded-3xl p-5 w-full max-w-md space-y-3 max-h-[80vh] overflow-y-auto" data-testid="add-member-modal">
        <h3 className="font-serif text-xl mb-2">Adaugă specialist</h3>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-1.5">Specialitate</div>
          <select value={specialty} onChange={e => setSpecialty(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm">
            <option value="parchet">Parchet</option>
            <option value="zugravit">Zugrăvit</option>
            <option value="faianta">Faianță / Gresie</option>
            <option value="handyman">Handyman</option>
            <option value="gips_carton">Gips-carton</option>
            <option value="electric">Electric</option>
            <option value="plumbing">Sanitar</option>
            <option value="hvac">HVAC</option>
            <option value="carpentry">Dulgherie</option>
          </select>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-1.5">Specialist disponibil</div>
          <div className="space-y-1.5 max-h-60 overflow-y-auto">
            {available.length === 0 ? (
              <div className="text-xs text-stone-500 text-center py-4">Niciun specialist disponibil.</div>
            ) : available.map(s => (
              <button key={s.id} onClick={() => setPick(s.id)} type="button"
                className={`w-full text-left p-3 rounded-xl border transition ${pick === s.id ? "bg-purple-500/20 border-purple-500/50" : "bg-white/5 border-white/10 hover:bg-white/10"}`}
                data-testid={`pick-member-${s.id}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium">{s.name}</div>
                    <div className="text-[10px] uppercase tracking-wider text-stone-500">{(s.service_categories || []).slice(0, 3).join(" · ")}</div>
                  </div>
                  <div className="text-xs text-amber-300">★ {s.rating?.toFixed(1) || "—"}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
        <div className="flex gap-2 pt-2">
          <button onClick={onClose} className="flex-1 py-2 bg-white/5 rounded-full text-sm">Anulează</button>
          <button onClick={submit} disabled={!pick || busy} className="flex-1 py-2 btn-accent rounded-full text-sm disabled:opacity-50" data-testid="add-member-submit">
            {busy ? "..." : "Adaugă"}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

const TaskDetailModal = ({ task, project, onClose, onUpdate, currentUser }) => {
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [attachments, setAttachments] = useState(task.attachments || []);
  const fileInputRef = React.useRef(null);
  const isDesigner = project.designer_id === currentUser?.id;
  const isAssignee = task.assignee_id === currentUser?.id;
  const canEditStatus = isDesigner || isAssignee;

  useEffect(() => {
    axios.get(`${API}/tasks/${task.id}/comments`).then(r => setComments(r.data || [])).catch(() => setComments([]));
  }, [task.id]);

  const setStatus = async (status) => {
    try {
      await axios.patch(`${API}/tasks/${task.id}`, { status });
      onUpdate();
      onClose();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); }
  };

  const submitComment = async () => {
    if (!newComment.trim()) return;
    setBusy(true);
    try {
      const { data } = await axios.post(`${API}/tasks/${task.id}/comments`, { body: newComment });
      setComments([...comments, data]);
      setNewComment("");
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); }
    finally { setBusy(false); }
  };

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2_500_000) { alert("Fișier prea mare (max 2.5MB)"); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const { data } = await axios.post(`${API}/tasks/${task.id}/attachments`, {
          url: reader.result, name: file.name, mime: file.type,
        });
        setAttachments([...(attachments || []), data.attachment]);
      } catch (err) { alert(err?.response?.data?.detail || "Eroare upload"); }
    };
    reader.readAsDataURL(file);
  };

  const removeAttachment = async (attId) => {
    if (!window.confirm("Ștergi acest atașament?")) return;
    try {
      await axios.delete(`${API}/tasks/${task.id}/attachments/${attId}`);
      setAttachments(attachments.filter(a => a.id !== attId));
    } catch (e) { alert(e?.response?.data?.detail || "Eroare"); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-end sm:items-center justify-center p-3" onClick={onClose}>
      <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} onClick={e => e.stopPropagation()}
        className="bg-stone-950 border border-white/10 rounded-3xl p-5 w-full max-w-lg max-h-[90vh] overflow-y-auto" data-testid="task-detail-modal">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-stone-400 mb-1">Task · {task.assignee_name || "neasignat"}</div>
            <h3 className="font-serif text-xl">{task.title}</h3>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center" data-testid="task-close"><X className="w-4 h-4" /></button>
        </div>
        {task.description && <p className="text-sm text-stone-400 mb-3 leading-relaxed">{task.description}</p>}
        <div className="flex gap-2 flex-wrap mb-4">
          <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-${PRIORITY[task.priority]?.color || "stone"}-500/15 text-${PRIORITY[task.priority]?.color || "stone"}-300 border border-${PRIORITY[task.priority]?.color || "stone"}-500/30`}>
            {PRIORITY[task.priority]?.label || task.priority}
          </span>
          {task.due_date && <span className="text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-white/5 text-stone-300">Termen: {task.due_date}</span>}
        </div>
        {canEditStatus && (
          <div className="flex gap-2 mb-4 flex-wrap">
            {STATUS_COLS.map(c => (
              <button key={c.id} onClick={() => setStatus(c.id)} disabled={task.status === c.id}
                className={`text-xs px-3 py-1.5 rounded-full border transition ${task.status === c.id ? "bg-[#d4ff3a] text-black border-[#d4ff3a]" : "bg-white/5 text-stone-300 border-white/10 hover:bg-white/10"}`}
                data-testid={`set-status-${c.id}`}>
                {c.label}
              </button>
            ))}
          </div>
        )}

        {/* Attachments */}
        <div className="border-t border-white/5 pt-3 mb-3">
          <div className="flex items-center justify-between mb-2">
            <div className="text-[10px] uppercase tracking-wider text-stone-400 flex items-center gap-1">
              <Paperclip className="w-3 h-3" />Atașamente ({attachments.length})
            </div>
            <button onClick={() => fileInputRef.current?.click()}
              className="text-xs px-2.5 py-1 rounded-full bg-purple-500/15 hover:bg-purple-500/25 text-purple-300 border border-purple-500/30 flex items-center gap-1" data-testid="upload-attachment-btn">
              <ImageIcon className="w-3 h-3" />Adaugă foto/fișier
            </button>
            <input type="file" ref={fileInputRef} onChange={handleFile} accept="image/*,application/pdf" className="hidden" data-testid="attachment-file-input" />
          </div>
          {attachments.length === 0 ? (
            <div className="text-[11px] text-stone-500 italic">Nicio fotografie încă. Adaugă poze de progres pentru lucrare.</div>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              {attachments.map(a => {
                const isImg = (a.mime || "").startsWith("image/") || /\.(jpg|jpeg|png|gif|webp)$/i.test(a.name);
                return (
                  <div key={a.id} className="relative group bg-white/5 rounded-xl overflow-hidden aspect-square" data-testid={`attachment-${a.id}`}>
                    {isImg ? (
                      <img src={a.url} alt={a.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center text-stone-400 p-2 text-center">
                        <Paperclip className="w-5 h-5 mb-1" />
                        <div className="text-[9px] truncate w-full">{a.name}</div>
                      </div>
                    )}
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/70 transition flex items-end p-1.5 opacity-0 group-hover:opacity-100">
                      <div className="text-[9px] text-white truncate flex-1">{a.uploaded_by_name}</div>
                      <button onClick={(e) => { e.stopPropagation(); removeAttachment(a.id); }}
                        className="text-red-300 hover:text-red-200">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="border-t border-white/5 pt-3 space-y-2">
          <div className="text-[10px] uppercase tracking-wider text-stone-400">Comentarii ({comments.length})</div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {comments.map(c => (
              <div key={c.id} className="bg-white/5 rounded-xl p-2.5">
                <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-0.5">{c.author_name} · {c.author_role}</div>
                <div className="text-sm">{c.body}</div>
              </div>
            ))}
            {comments.length === 0 && <div className="text-xs text-stone-500 italic">Niciun comentariu încă.</div>}
          </div>
          <div className="flex gap-2 mt-2">
            <input value={newComment} onChange={e => setNewComment(e.target.value)} placeholder="Scrie un comentariu..."
              onKeyDown={e => e.key === "Enter" && submitComment()}
              className="flex-1 bg-white/5 border border-white/10 rounded-full px-3 py-2 text-sm" data-testid="task-comment-input" />
            <button onClick={submitComment} disabled={busy || !newComment.trim()}
              className="px-3 py-2 btn-accent rounded-full disabled:opacity-40" data-testid="task-comment-send">
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

// ============= PROJECT LIST CARD (reusable for client + specialist dashboards) =============
export const ProjectListSection = ({ title = "Proiecte de coordonare" }) => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    axios.get(`${API}/projects`)
      .then(r => setProjects(r.data || []))
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
  }, []);
  if (loading) return null;
  if (projects.length === 0) return null;
  return (
    <div className="glass-strong rounded-3xl p-5 sm:p-6" data-testid="projects-list">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-9 h-9 rounded-2xl bg-gradient-to-br from-cyan-500/30 to-purple-500/30 border border-purple-500/40 flex items-center justify-center">
          <ListChecks className="w-4 h-4 text-purple-200" />
        </div>
        <div>
          <h3 className="font-serif text-lg leading-tight">{title}</h3>
          <div className="text-[10px] uppercase tracking-wider text-stone-400">{projects.length} {projects.length === 1 ? "proiect activ" : "proiecte active"}</div>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {projects.map(p => {
          const totalT = p.tasks_count?.total || 0;
          const doneT = p.tasks_count?.done || 0;
          const pct = totalT > 0 ? Math.round((doneT / totalT) * 100) : 0;
          return (
            <button key={p.id} onClick={() => navigate(`/projects/${p.id}`)}
              className="text-left bg-white/5 hover:bg-white/10 border border-white/10 hover:border-purple-500/40 rounded-2xl p-4 transition"
              data-testid={`project-card-${p.id}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="font-medium text-sm truncate">{p.name}</div>
                <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${
                  p.status === "active" ? "bg-emerald-500/15 text-emerald-300" : "bg-stone-500/15 text-stone-300"
                }`}>{p.status}</span>
              </div>
              <div className="text-[10px] uppercase tracking-wider text-stone-500">
                Coord: {p.designer_name} · Client: {p.client_name}
              </div>
              <div className="mt-2 text-[11px] text-stone-400">
                {totalT > 0 ? `${doneT}/${totalT} task-uri · ${pct}%` : "Niciun task încă"}
              </div>
              {totalT > 0 && (
                <div className="h-1 bg-white/5 rounded mt-1.5 overflow-hidden">
                  <div className="h-full bg-emerald-400" style={{ width: `${pct}%` }} />
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
