// FutureIdeasVault — strategic proposals catalog.
//
// READ-ONLY catalog of dev/business proposals that REQUIRE explicit validation
// before any code is written. Each idea is fully documented (architecture,
// backend spec, frontend spec, DB schema, risks, phases, ROI) so the founder
// can decide whether the cost/benefit warrants implementation.
//
// CRITICAL: this is NOT a ToDo board. Status changes here DO NOT trigger any
// implementation. Approval here just means "we can consider scheduling it".
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Lightbulb, ShieldAlert, Lock, Sparkles, ChevronRight, ChevronLeft,
  Loader2, Save, Coins, TrendingUp, AlertTriangle, CheckCircle2,
  Code2, Database, Layout, GitBranch, Brain, Clock, FileText,
  BarChart3, X as XIcon, History, ArrowRight, Mail, Send,
} from "lucide-react";
import { FUTURE_IDEAS } from "../../data/futureIdeas";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const STATUS_META = {
  pending_validation: { label: "În evaluare", color: "amber",   icon: Clock },
  in_discussion:      { label: "În discuție", color: "blue",    icon: FileText },
  approved:           { label: "Aprobat",     color: "emerald", icon: CheckCircle2 },
  rejected:           { label: "Respins",     color: "red",     icon: AlertTriangle },
  on_hold:            { label: "Pe pauză",    color: "stone",   icon: Lock },
};

const colorClasses = (c) => ({
  amber:   "bg-amber-500/10 border-amber-500/40 text-amber-300",
  blue:    "bg-blue-500/10 border-blue-500/40 text-blue-300",
  emerald: "bg-emerald-500/10 border-emerald-500/40 text-emerald-300",
  red:     "bg-red-500/10 border-red-500/40 text-red-300",
  stone:   "bg-stone-500/10 border-stone-500/40 text-stone-300",
}[c]);

// Relative time helper — "acum 2h", "acum 3 zile"
const relativeTime = (iso) => {
  if (!iso) return "";
  const diffMs = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(diffMs / 1000);
  if (sec < 60) return "acum câteva secunde";
  const min = Math.floor(sec / 60);
  if (min < 60) return `acum ${min} min`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `acum ${hr}h`;
  const days = Math.floor(hr / 24);
  if (days < 7) return `acum ${days} zile`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `acum ${weeks} săpt.`;
  const months = Math.floor(days / 30);
  if (months < 12) return `acum ${months} luni`;
  return `acum ${Math.floor(days / 365)} ani`;
};

// Aggregate recent decisions across all proposals (newest first, top N)
const aggregateRecentDecisions = (ideas, statuses, limit = 5) => {
  const all = [];
  ideas.forEach((idea) => {
    const log = statuses[idea.id]?.decision_log || [];
    log.forEach((entry) => {
      all.push({ ...entry, idea_id: idea.id, idea_code: idea.code, idea_title: idea.title, idea_icon: idea.icon });
    });
  });
  all.sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime());
  return all.slice(0, limit);
};

const FutureIdeasVault = () => {
  const [statuses, setStatuses] = useState({}); // idea_id -> status doc
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null); // idea object
  const [showComparator, setShowComparator] = useState(false);
  const [showDigest, setShowDigest] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await ax.get("/api/admin/future-ideas");
      const map = {};
      (data.items || []).forEach(s => { map[s.idea_id] = s; });
      setStatuses(map);
    } catch (_) { /* allow empty */ }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const getStatus = (id) => statuses[id]?.status || "pending_validation";

  if (selected) {
    return (
      <IdeaDetail
        idea={selected}
        status={statuses[selected.id]}
        onBack={() => setSelected(null)}
        onSaved={(s) => setStatuses(prev => ({ ...prev, [selected.id]: s }))}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-6xl mx-auto px-6 pt-28 pb-16">
        <Link to="/admin" className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="fi-back">
          <ChevronLeft className="w-3.5 h-3.5" /> Înapoi la Admin Dashboard
        </Link>

        <div className="flex items-start gap-3 mb-2">
          <div className="w-12 h-12 rounded-2xl bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 flex items-center justify-center shrink-0">
            <Lightbulb className="w-5 h-5 text-[#d4ff3a]" />
          </div>
          <div className="flex-1">
            <h1 className="font-serif text-4xl md:text-5xl tracking-tight" data-testid="fi-title">
              Idei de <span className="italic gradient-text">Dezvoltare</span> Viitoare
            </h1>
            <p className="text-sm text-stone-400 mt-2 max-w-3xl">
              Catalog de propuneri arhitecturale ce <strong className="text-stone-200">NU au fost încă implementate</strong>.
              Fiecare propunere include documentație completă pentru echipa IT (backend, frontend, DB, riscuri, faze, ROI estimat).
            </p>
          </div>
          <div className="flex flex-col gap-2 shrink-0 mt-2">
            <button
              onClick={() => setShowComparator(true)}
              className="hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500/10 border border-violet-500/40 text-violet-200 text-sm font-semibold hover:bg-violet-500/20 transition-colors"
              data-testid="fi-open-comparator"
            >
              <BarChart3 className="w-4 h-4" /> Comparator propuneri
            </button>
            <button
              onClick={() => setShowDigest(true)}
              className="hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-500/10 border border-blue-500/40 text-blue-200 text-sm font-semibold hover:bg-blue-500/20 transition-colors"
              data-testid="fi-open-digest"
            >
              <Mail className="w-4 h-4" /> Digest email
            </button>
          </div>
        </div>

        {/* Mobile-only comparator button */}
        <div className="sm:hidden mt-4 grid grid-cols-2 gap-2">
          <button
            onClick={() => setShowComparator(true)}
            className="inline-flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl bg-violet-500/10 border border-violet-500/40 text-violet-200 text-sm font-semibold hover:bg-violet-500/20 transition-colors"
            data-testid="fi-open-comparator-mobile"
          >
            <BarChart3 className="w-4 h-4" /> Comparator
          </button>
          <button
            onClick={() => setShowDigest(true)}
            className="inline-flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl bg-blue-500/10 border border-blue-500/40 text-blue-200 text-sm font-semibold hover:bg-blue-500/20 transition-colors"
            data-testid="fi-open-digest-mobile"
          >
            <Mail className="w-4 h-4" /> Digest
          </button>
        </div>

        {/* WARNING BANNER — most prominent */}
        <div className="mt-6 rounded-2xl border border-red-500/40 bg-gradient-to-r from-red-500/10 via-red-500/5 to-amber-500/5 p-5 flex items-start gap-3" data-testid="fi-warning">
          <ShieldAlert className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />
          <div className="text-sm leading-relaxed">
            <div className="text-base font-semibold text-red-300 mb-1">ATENȚIE — Zonă strategică, NU operativă</div>
            <ul className="list-disc list-inside text-stone-300 space-y-0.5">
              <li>Aceste idei sunt <strong className="text-white">propuneri în evaluare</strong> — nu apar în ToDo Board și nu sunt în coada de dezvoltare.</li>
              <li><strong className="text-white">NU începeți implementarea</strong> niciunei idei fără aprobarea explicită a founder-ului.</li>
              <li>Schimbarea statusului aici <strong className="text-white">NU declanșează</strong> nicio acțiune automată — este doar pentru tracking decizional.</li>
              <li>Implementarea, când va începe, va fi <strong className="text-white">strict pe etape</strong>, izolată prin feature flags, fără modificări la modulele existente.</li>
            </ul>
          </div>
        </div>

        {/* RECENT CROSS-PROPOSAL ACTIVITY — top 5 decisions across all ideas */}
        {!loading && <RecentActivity ideas={FUTURE_IDEAS} statuses={statuses} onOpen={(idea) => setSelected(idea)} />}

        {loading ? (
          <div className="mt-10 text-center text-stone-400 flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă propunerile...
          </div>
        ) : (
          <div className="mt-8 space-y-4">
            {[...FUTURE_IDEAS]
              .sort((a, b) => (a.priority === "high" ? -1 : 0) - (b.priority === "high" ? -1 : 0))
              .map((idea) => {
              const st = getStatus(idea.id);
              const meta = STATUS_META[st];
              const Icon = meta.icon;
              return (
                <button
                  key={idea.id}
                  onClick={() => setSelected(idea)}
                  className={`w-full text-left bg-[#0e0e10] border rounded-2xl p-5 transition-all group ${
                    idea.priority === "high" ? "border-red-500/40 hover:border-red-500/60" : "border-white/10 hover:border-white/20"
                  }`}
                  data-testid={`fi-card-${idea.id}`}
                >
                  <div className="flex items-start gap-4">
                    <div className={`w-12 h-12 rounded-xl border flex items-center justify-center shrink-0 ${
                      idea.priority === "high" ? "bg-red-500/10 border-red-500/30" : "bg-white/5 border-white/10"
                    }`}>
                      <idea.icon className={`w-5 h-5 ${idea.priority === "high" ? "text-red-300" : "text-stone-300"}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="font-mono text-[10px] uppercase tracking-wider text-stone-500">{idea.code}</span>
                        {idea.priority === "high" && (
                          <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border bg-red-500/15 border-red-500/40 text-red-300 font-bold animate-pulse">
                            <ShieldAlert className="w-3 h-3" /> Prioritate Înaltă
                          </span>
                        )}
                        <span className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border ${colorClasses(meta.color)}`}>
                          <Icon className="w-3 h-3" /> {meta.label}
                        </span>
                        <span className="text-[10px] text-stone-500">Risc {idea.risk}/10 · {idea.timelineDays}z (freelance ref.)</span>
                      </div>
                      <div className="text-lg font-semibold text-white">{idea.title}</div>
                      <div className="text-sm text-stone-400 mt-1 line-clamp-2">{idea.summary}</div>
                      <div className="flex items-center gap-3 mt-3 text-[11px] text-stone-500 flex-wrap">
                        <span className="inline-flex items-center gap-1"><Coins className="w-3 h-3" /> Freelance ~{idea.estCostEur}€</span>
                        <span className="inline-flex items-center gap-1 text-violet-300"><Brain className="w-3 h-3" /> Emergent: {idea.emergentCreditsEstimate || "—"}</span>
                        <span className="inline-flex items-center gap-1"><TrendingUp className="w-3 h-3" /> Venit {idea.estRevenueRange}</span>
                        <span className="inline-flex items-center gap-1"><GitBranch className="w-3 h-3" /> {idea.phases.length} faze</span>
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-stone-500 group-hover:text-white shrink-0 mt-2" />
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* SAFETY FOOTER */}
        <div className="mt-10 bg-amber-500/5 border border-amber-500/30 rounded-2xl p-4 text-xs text-amber-100 flex items-start gap-3">
          <Lock className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
          <div>
            <strong>Convenție de siguranță:</strong> Acest catalog nu se sincronizează cu ToDo Board.
            Trecerea unei idei pe <em>Aprobat</em> indică doar decizia de business — NU adaugă automat task-uri în coadă.
            Când o idee este aprobată oficial, founder-ul va crea explicit fazele necesare în ToDo Board.
          </div>
        </div>
      </div>

      {showComparator && (
        <ComparatorModal
          ideas={FUTURE_IDEAS}
          statuses={statuses}
          onClose={() => setShowComparator(false)}
        />
      )}

      {showDigest && (
        <DigestModal onClose={() => setShowDigest(false)} />
      )}
    </div>
  );
};

// ============================================================================
// RECENT ACTIVITY — cross-proposal decision timeline (top 5)
// ============================================================================
const RecentActivity = ({ ideas, statuses, onOpen }) => {
  const recent = aggregateRecentDecisions(ideas, statuses, 5);
  if (recent.length === 0) {
    return (
      <div className="mt-6 bg-[#0e0e10] border border-white/10 rounded-2xl p-5" data-testid="fi-recent-activity-empty">
        <div className="flex items-center gap-2 text-sm uppercase tracking-wider text-stone-400 mb-2">
          <History className="w-4 h-4 text-violet-300" /> Activitate recentă cross-propuneri
        </div>
        <div className="text-xs text-stone-500">
          Nicio decizie încă. Pe măsură ce marchezi statusul propunerilor (cu motiv), ultimele 5 modificări apar aici pentru o vedere rapidă.
        </div>
      </div>
    );
  }

  return (
    <div className="mt-6 bg-[#0e0e10] border border-violet-500/20 rounded-2xl overflow-hidden" data-testid="fi-recent-activity">
      <div className="px-5 py-3 border-b border-white/10 bg-violet-500/5 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 text-sm uppercase tracking-wider text-violet-200">
          <History className="w-4 h-4 text-violet-300" /> Activitate recentă cross-propuneri
        </div>
        <span className="text-[10px] text-stone-500 font-mono">Ultimele {recent.length} decizii</span>
      </div>
      <div className="divide-y divide-white/5">
        {recent.map((entry, i) => {
          const fromMeta = STATUS_META[entry.from_status] || STATUS_META.pending_validation;
          const toMeta = STATUS_META[entry.to_status] || STATUS_META.pending_validation;
          const Icon = entry.idea_icon;
          return (
            <button
              key={i}
              onClick={() => onOpen(ideas.find((idea) => idea.id === entry.idea_id))}
              className="w-full text-left px-5 py-3 hover:bg-white/[0.03] transition-colors flex items-start gap-3 group"
              data-testid={`fi-recent-entry-${i}`}
            >
              <div className="w-9 h-9 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center shrink-0 group-hover:border-violet-500/40">
                <Icon className="w-4 h-4 text-stone-300" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-stone-500">{entry.idea_code}</span>
                  <span className="text-sm text-white font-semibold truncate max-w-[300px] sm:max-w-[400px]">{entry.idea_title}</span>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap text-[10px] mb-1">
                  <span className={`inline-block uppercase px-1.5 py-0.5 rounded border ${colorClasses(fromMeta.color)}`}>{fromMeta.label}</span>
                  <ArrowRight className="w-3 h-3 text-stone-500" />
                  <span className={`inline-block uppercase px-1.5 py-0.5 rounded border ${colorClasses(toMeta.color)}`}>{toMeta.label}</span>
                  <span className="ml-1 text-stone-500">· {relativeTime(entry.at)}</span>
                  <span className="text-stone-600">· {entry.by}</span>
                </div>
                <div className="text-xs text-stone-300 line-clamp-2 italic">"{entry.reason}"</div>
              </div>
              <ChevronRight className="w-4 h-4 text-stone-600 group-hover:text-violet-300 shrink-0 mt-2" />
            </button>
          );
        })}
      </div>
    </div>
  );
};

// ============================================================================
// IDEA DETAIL VIEW
// ============================================================================
const TABS = [
  { id: "overview", label: "Overview",        icon: Lightbulb },
  { id: "questions", label: "Decizii Pending", icon: AlertTriangle, conditional: "openQuestions" },
  { id: "phases",   label: "Faze (Etape)",    icon: GitBranch },
  { id: "backend",  label: "Backend Spec",    icon: Code2 },
  { id: "frontend", label: "Frontend Spec",   icon: Layout },
  { id: "db",       label: "Database Schema", icon: Database },
  { id: "risks",    label: "Riscuri",         icon: AlertTriangle },
  { id: "ai",       label: "AI Touchpoints",  icon: Brain },
  { id: "roi",      label: "Cost vs Venit",   icon: TrendingUp },
  { id: "history",  label: "Istoric Decizii", icon: History },
];

const IdeaDetail = ({ idea, status, onBack, onSaved }) => {
  const [tab, setTab] = useState("overview");
  const [draft, setDraft] = useState({
    status: status?.status || "pending_validation",
    notes: status?.notes || "",
    estimated_cost_eur: status?.estimated_cost_eur ?? "",
    estimated_revenue_eur_monthly: status?.estimated_revenue_eur_monthly ?? "",
    emergent_credits_used: status?.emergent_credits_used ?? "",
    emergent_credits_notes: status?.emergent_credits_notes ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [saveOk, setSaveOk] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [reasonModal, setReasonModal] = useState(null); // {fromStatus, toStatus, reason}

  const prevStatus = status?.status || "pending_validation";
  const statusChanged = draft.status !== prevStatus;

  const doSave = async (decisionReason = null) => {
    setSaving(true);
    setSaveOk(false);
    setSaveError(null);
    try {
      const payload = {
        status: draft.status,
        notes: draft.notes,
        estimated_cost_eur: draft.estimated_cost_eur === "" ? null : Number(draft.estimated_cost_eur),
        estimated_revenue_eur_monthly: draft.estimated_revenue_eur_monthly === "" ? null : Number(draft.estimated_revenue_eur_monthly),
        emergent_credits_used: draft.emergent_credits_used === "" ? null : Number(draft.emergent_credits_used),
        emergent_credits_notes: draft.emergent_credits_notes,
      };
      if (decisionReason) payload.decision_reason = decisionReason;
      const { data } = await ax.put(`/api/admin/future-ideas/${idea.id}`, payload);
      onSaved(data);
      setSaveOk(true);
      setReasonModal(null);
      setTimeout(() => setSaveOk(false), 2200);
    } catch (e) {
      setSaveError(e?.response?.data?.detail || "Eroare la salvare");
    } finally { setSaving(false); }
  };

  const save = () => {
    if (statusChanged) {
      // Open reason modal
      setReasonModal({
        fromStatus: prevStatus,
        toStatus: draft.status,
        reason: "",
      });
    } else {
      doSave();
    }
  };

  const stMeta = STATUS_META[draft.status];

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-6xl mx-auto px-6 pt-28 pb-16">
        <button onClick={onBack} className="text-xs text-stone-400 hover:text-white inline-flex items-center gap-1 mb-3" data-testid="fi-detail-back">
          <ChevronLeft className="w-3.5 h-3.5" /> Înapoi la catalog
        </button>

        <div className="flex items-start gap-4 mb-4">
          <div className="w-14 h-14 rounded-2xl bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 flex items-center justify-center shrink-0">
            <idea.icon className="w-6 h-6 text-[#d4ff3a]" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-mono text-[10px] uppercase tracking-wider text-stone-500">{idea.code} · Risc {idea.risk}/10 · Complexitate Emergent: {idea.emergentComplexity || "—"}</div>
            <h1 className="font-serif text-3xl md:text-4xl tracking-tight mt-1" data-testid="fi-detail-title">{idea.title}</h1>
            <p className="text-sm text-stone-400 mt-2 max-w-3xl">{idea.summary}</p>
            {idea.riskExplanation && (
              <div className="mt-3 bg-blue-500/5 border border-blue-500/30 rounded-xl p-3 text-xs text-blue-100 flex items-start gap-2 max-w-3xl">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-blue-400" />
                <div><strong className="text-blue-300">Ce înseamnă Risc {idea.risk}/10:</strong> {idea.riskExplanation}</div>
              </div>
            )}
          </div>
        </div>

        {/* STATUS PANEL */}
        <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5 mb-6">
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <label className="text-[10px] uppercase tracking-wider text-stone-400">Status decizie business</label>
              <div className="flex flex-wrap gap-2 mt-2">
                {Object.entries(STATUS_META).map(([key, m]) => (
                  <button
                    key={key}
                    onClick={() => setDraft(d => ({ ...d, status: key }))}
                    className={`text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-full border transition-colors ${
                      draft.status === key ? colorClasses(m.color) : "bg-white/5 border-white/10 text-stone-400 hover:border-white/20"
                    }`}
                    data-testid={`fi-status-${key}`}
                  >{m.label}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-stone-400">Cost estimat (€ one-time)</label>
              <input
                type="number"
                value={draft.estimated_cost_eur}
                onChange={(e) => setDraft(d => ({ ...d, estimated_cost_eur: e.target.value }))}
                className="mt-2 w-full bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm font-mono"
                placeholder={`ex: ${idea.estCostEur}`}
                data-testid="fi-cost-input"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-stone-400">Venit estimat (€ / lună)</label>
              <input
                type="number"
                value={draft.estimated_revenue_eur_monthly}
                onChange={(e) => setDraft(d => ({ ...d, estimated_revenue_eur_monthly: e.target.value }))}
                className="mt-2 w-full bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm font-mono"
                placeholder={`ex: ${idea.estRevenueMonthly}`}
                data-testid="fi-revenue-input"
              />
            </div>
          </div>

          <label className="text-[10px] uppercase tracking-wider text-stone-400 block mt-4">Note decizionale (interne)</label>
          <textarea
            value={draft.notes}
            onChange={(e) => setDraft(d => ({ ...d, notes: e.target.value }))}
            rows={3}
            className="mt-2 w-full bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm"
            placeholder="ex: așteptăm validare cu 3 clienți pilot înainte de a aproba Phase ES-2..."
            data-testid="fi-notes-input"
          />

          {/* EMERGENT CREDITS TRACKING — populated during/after implementation */}
          <div className="mt-5 border-t border-white/10 pt-5">
            <div className="text-[10px] uppercase tracking-wider text-violet-300 mb-2 flex items-center gap-2">
              <Brain className="w-3 h-3" /> Tracking credite Emergent (actualizat pe parcurs)
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] uppercase tracking-wider text-stone-400">Credite consumate până acum</label>
                <input
                  type="number"
                  value={draft.emergent_credits_used}
                  onChange={(e) => setDraft(d => ({ ...d, emergent_credits_used: e.target.value }))}
                  className="mt-2 w-full bg-[#0a0a0b] border border-violet-500/30 rounded-lg px-3 py-2 text-sm font-mono"
                  placeholder="ex: 12 (după primul task)"
                  data-testid="fi-credits-used"
                />
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-wider text-stone-400">Note credite (per task)</label>
                <textarea
                  value={draft.emergent_credits_notes}
                  onChange={(e) => setDraft(d => ({ ...d, emergent_credits_notes: e.target.value }))}
                  rows={2}
                  className="mt-2 w-full bg-[#0a0a0b] border border-violet-500/30 rounded-lg px-3 py-2 text-xs font-mono"
                  placeholder="ex: ES-0 foundation ~15 cred, ES-1 spaces ~25 cred"
                  data-testid="fi-credits-notes"
                />
              </div>
            </div>
            <div className="text-[10px] text-stone-500 mt-2">
              💡 Câmpurile se completează pe parcursul implementării. Eu îți voi raporta aproximativ după fiecare fază pentru tracking acuratețe estimări.
            </div>
          </div>

          <div className="flex items-center justify-between mt-4 flex-wrap gap-3">
            <div className="text-xs text-stone-500">
              Status curent: <span className={`px-2 py-0.5 rounded-full border ${colorClasses(stMeta.color)}`}>{stMeta.label}</span>
              {status?.updated_at && (
                <span className="ml-2">· Modificat: {new Date(status.updated_at).toLocaleString("ro-RO")} de {status.updated_by}</span>
              )}
              {statusChanged && (
                <span className="ml-2 inline-flex items-center gap-1 text-amber-300">
                  <AlertTriangle className="w-3 h-3" /> Status modificat — va cere motivul la salvare
                </span>
              )}
            </div>
            <button
              onClick={save}
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#d4ff3a] text-black text-sm font-semibold hover:bg-[#c0eb2a] disabled:opacity-60"
              data-testid="fi-save"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : saveOk ? <CheckCircle2 className="w-4 h-4" /> : <Save className="w-4 h-4" />}
              {saveOk ? "Salvat" : statusChanged ? "Continuă & adaugă motiv" : "Salvează"}
            </button>
          </div>
          {saveError && (
            <div className="mt-3 bg-red-500/10 border border-red-500/30 rounded-lg p-2 text-xs text-red-300 flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5" /> {saveError}
            </div>
          )}
        </div>

        {/* TABS */}
        <div className="flex flex-wrap gap-2 mb-4">
          {TABS.filter(t => !t.conditional || idea[t.conditional]).map(t => {
            const Icon = t.icon;
            const isQuestions = t.id === "questions";
            const pendingCount = isQuestions ? (idea.openQuestions || []).filter(q => !q.founderDecision).length : 0;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`inline-flex items-center gap-2 px-3 py-2 rounded-xl text-sm border transition-colors ${
                  tab === t.id
                    ? (isQuestions ? "bg-red-500/15 border-red-500/40 text-red-200" : "bg-white/10 border-white/30 text-white")
                    : (isQuestions ? "bg-red-500/5 border-red-500/30 text-red-300 hover:bg-red-500/10" : "bg-[#0e0e10] border-white/10 text-stone-400 hover:text-white")
                }`}
                data-testid={`fi-tab-${t.id}`}
              >
                <Icon className="w-4 h-4" /> {t.label}
                {isQuestions && pendingCount > 0 && (
                  <span className="ml-1 px-1.5 py-0 rounded-full bg-red-500 text-white text-[10px] font-bold">{pendingCount}</span>
                )}
              </button>
            );
          })}
        </div>

        {/* TAB CONTENT */}
        <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-6">
          {tab === "overview"  && <SectionOverview idea={idea} />}
          {tab === "questions" && <SectionOpenQuestions idea={idea} />}
          {tab === "phases"   && <SectionPhases idea={idea} />}
          {tab === "backend"  && <SectionBackend idea={idea} />}
          {tab === "frontend" && <SectionFrontend idea={idea} />}
          {tab === "db"       && <SectionDB idea={idea} />}
          {tab === "risks"    && <SectionRisks idea={idea} />}
          {tab === "ai"       && <SectionAI idea={idea} />}
          {tab === "roi"      && <SectionROI idea={idea} />}
          {tab === "history"  && <SectionHistory status={status} />}
        </div>
      </div>

      {reasonModal && (
        <DecisionReasonModal
          fromStatus={reasonModal.fromStatus}
          toStatus={reasonModal.toStatus}
          ideaTitle={idea.title}
          saving={saving}
          error={saveError}
          onCancel={() => { setReasonModal(null); setSaveError(null); }}
          onConfirm={(reason) => doSave(reason)}
        />
      )}
    </div>
  );
};

const H = ({ children }) => <h3 className="text-sm uppercase tracking-wider text-stone-400 mb-3">{children}</h3>;
const Pre = ({ children }) => (
  <pre className="bg-black/60 border border-white/10 rounded-lg p-3 text-[11px] leading-relaxed font-mono text-stone-300 overflow-x-auto whitespace-pre-wrap">{children}</pre>
);

const SectionOverview = ({ idea }) => (
  <div className="space-y-5">
    <div>
      <H>Problemă & Oportunitate</H>
      <p className="text-sm text-stone-300 leading-relaxed">{idea.problemAndOpportunity}</p>
    </div>
    <div>
      <H>Principii arhitecturale (negociabile)</H>
      <ul className="space-y-1.5 text-sm text-stone-300">
        {idea.principles.map((p, i) => (
          <li key={i} className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>{p}</span>
          </li>
        ))}
      </ul>
    </div>
    <div>
      <H>Anti-patterns (DE EVITAT)</H>
      <ul className="space-y-1.5 text-sm text-stone-300">
        {idea.antiPatterns.map((a, i) => (
          <li key={i} className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <span>{a}</span>
          </li>
        ))}
      </ul>
    </div>
  </div>
);

// ============================================================================
// OPEN QUESTIONS — decisions pending from founder before implementation
// ============================================================================
const SectionOpenQuestions = ({ idea }) => {
  const questions = idea.openQuestions || [];
  const pendingCount = questions.filter(q => !q.founderDecision).length;
  return (
    <div className="space-y-5">
      <div className="bg-red-500/10 border border-red-500/40 rounded-xl p-4 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-red-300 shrink-0 mt-0.5" />
        <div className="text-sm">
          <div className="font-semibold text-red-200 mb-1">⚠️ Decizii necesare ÎNAINTE de implementare ({pendingCount} pending)</div>
          <div className="text-stone-300 text-xs">
            Această propunere este marcată cu <strong className="text-red-300">PRIORITATE ÎNALTĂ</strong> dar nu poate fi implementată până nu primim răspunsuri la întrebările de mai jos.
            Răspunsurile tale vor fi folosite pentru a configura scope-ul exact al implementării.
          </div>
        </div>
      </div>

      {questions.map((q, i) => (
        <div key={i} className="border border-white/10 rounded-xl bg-white/[0.02] overflow-hidden">
          <div className="px-4 py-3 bg-white/[0.03] border-b border-white/10 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-red-500/15 border border-red-500/40 flex items-center justify-center text-[10px] font-bold text-red-300">{i + 1}</span>
            <div className="font-semibold text-white text-sm flex-1">{q.title}</div>
            {q.founderDecision ? (
              <span className="text-[10px] uppercase px-2 py-0.5 rounded-full border bg-emerald-500/10 border-emerald-500/40 text-emerald-300">
                <CheckCircle2 className="w-3 h-3 inline mr-1" /> Decis
              </span>
            ) : (
              <span className="text-[10px] uppercase px-2 py-0.5 rounded-full border bg-amber-500/10 border-amber-500/40 text-amber-300">
                <Clock className="w-3 h-3 inline mr-1" /> Pending
              </span>
            )}
          </div>
          <div className="px-4 py-3 space-y-3">
            <div className="text-xs text-stone-400 leading-relaxed">{q.context}</div>
            <div className="space-y-1.5">
              {q.options.map((opt, j) => (
                <div key={j} className={`text-sm px-3 py-2 rounded-lg border ${
                  q.founderDecision === opt
                    ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-200"
                    : "bg-white/[0.02] border-white/10 text-stone-300"
                }`}>
                  {q.founderDecision === opt && <CheckCircle2 className="w-3.5 h-3.5 inline mr-1.5 text-emerald-400" />}
                  {opt}
                </div>
              ))}
            </div>
            {q.founderDecision && (
              <div className="text-[11px] text-stone-500 italic">
                Decizie founder: {q.founderDecision}
              </div>
            )}
          </div>
        </div>
      ))}

      <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-3 text-xs text-blue-100 flex items-start gap-2">
        <Lightbulb className="w-3.5 h-3.5 shrink-0 mt-0.5 text-blue-300" />
        <div>
          Pentru a răspunde la aceste întrebări, scrie-mi în chat: <code className="bg-white/10 px-1 rounded">"Decizii FOUNDER-GATE: 1=a, 2=b, 3=a, 4=c"</code> sau direct cu detalii. Voi actualiza propunerea cu deciziile tale.
        </div>
      </div>
    </div>
  );
};

const SectionPhases = ({ idea }) => (
  <div className="space-y-3">
    <H>Roadmap pe etape (implementare strict secvențială)</H>
    {idea.phases.map((p, i) => (
      <div key={i} className="border border-white/10 rounded-xl p-4 bg-white/[0.02]">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 text-[#d4ff3a]">{p.code}</span>
          <div className="font-semibold text-white">{p.title}</div>
          <span className="text-[10px] text-stone-500 ml-auto">{p.days}z dev</span>
        </div>
        <div className="text-sm text-stone-400 mt-2">{p.description}</div>
        <ul className="mt-2 list-disc list-inside text-xs text-stone-500 space-y-0.5">
          {p.deliverables.map((d, j) => <li key={j}>{d}</li>)}
        </ul>
      </div>
    ))}
  </div>
);

const SectionBackend = ({ idea }) => (
  <div className="space-y-5">
    <div>
      <H>Structură director backend</H>
      <Pre>{idea.backend.structure}</Pre>
    </div>
    <div>
      <H>Endpoint-uri API ({idea.backend.endpoints.length})</H>
      <div className="space-y-1">
        {idea.backend.endpoints.map((e, i) => (
          <div key={i} className="flex items-start gap-3 text-[12px] font-mono py-1 border-b border-white/5">
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
              e.method === "GET"    ? "bg-blue-500/10 text-blue-300" :
              e.method === "POST"   ? "bg-emerald-500/10 text-emerald-300" :
              e.method === "PUT"    ? "bg-amber-500/10 text-amber-300" :
              e.method === "DELETE" ? "bg-red-500/10 text-red-300" :
                                      "bg-stone-500/10 text-stone-300"
            }`}>{e.method}</span>
            <span className="text-stone-200">{e.path}</span>
            <span className="text-stone-500 text-[11px] ml-2">{e.note}</span>
          </div>
        ))}
      </div>
    </div>
    <div>
      <H>Middleware & Security</H>
      <ul className="space-y-1.5 text-sm text-stone-300">
        {idea.backend.security.map((s, i) => (
          <li key={i} className="flex items-start gap-2">
            <span className="text-stone-500">•</span><span>{s}</span>
          </li>
        ))}
      </ul>
    </div>
    <div>
      <H>Dependențe noi (Python)</H>
      <Pre>{idea.backend.dependencies.join("\n")}</Pre>
    </div>
  </div>
);

const SectionFrontend = ({ idea }) => (
  <div className="space-y-5">
    <div>
      <H>Structură director frontend</H>
      <Pre>{idea.frontend.structure}</Pre>
    </div>
    <div>
      <H>Rute publice & autenticate ({idea.frontend.routes.length})</H>
      <div className="space-y-1">
        {idea.frontend.routes.map((r, i) => (
          <div key={i} className="flex items-start gap-3 text-[12px] font-mono py-1 border-b border-white/5">
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
              r.scope === "public" ? "bg-emerald-500/10 text-emerald-300" :
              r.scope === "auth"   ? "bg-blue-500/10 text-blue-300" :
                                     "bg-amber-500/10 text-amber-300"
            }`}>{r.scope}</span>
            <span className="text-stone-200">{r.path}</span>
            <span className="text-stone-500 text-[11px] ml-2">{r.note}</span>
          </div>
        ))}
      </div>
    </div>
    <div>
      <H>Design system reuse</H>
      <ul className="space-y-1.5 text-sm text-stone-300">
        {idea.frontend.designReuse.map((d, i) => (
          <li key={i} className="flex items-start gap-2"><span className="text-stone-500">•</span><span>{d}</span></li>
        ))}
      </ul>
    </div>
    <div>
      <H>Dependențe noi (npm/yarn)</H>
      <Pre>{idea.frontend.dependencies.join("\n")}</Pre>
    </div>
  </div>
);

const SectionDB = ({ idea }) => (
  <div className="space-y-5">
    <div>
      <H>Convenție de izolare</H>
      <p className="text-sm text-stone-300">{idea.db.isolationRule}</p>
    </div>
    <div>
      <H>Colecții MongoDB noi ({idea.db.collections.length})</H>
      <div className="space-y-3">
        {idea.db.collections.map((c, i) => (
          <div key={i} className="border border-white/10 rounded-xl p-4 bg-white/[0.02]">
            <div className="flex items-center justify-between mb-2">
              <code className="text-sm text-[#d4ff3a]">{c.name}</code>
              <span className="text-[10px] text-stone-500">{c.purpose}</span>
            </div>
            <Pre>{c.schema}</Pre>
            {c.indexes && (
              <div className="mt-2 text-[11px] text-stone-500">
                <strong className="text-stone-400">Indecși:</strong> {c.indexes.join(" · ")}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  </div>
);

const SectionRisks = ({ idea }) => (
  <div className="space-y-3">
    <H>Riscuri identificate (cu mitigare)</H>
    {idea.risks.map((r, i) => (
      <div key={i} className="border border-white/10 rounded-xl p-4 bg-white/[0.02]">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-[10px] text-stone-500">{r.id}</span>
          <span className={`text-[10px] uppercase px-2 py-0.5 rounded-full border ${
            r.severity === "CRITICAL" ? "bg-red-500/10 border-red-500/40 text-red-300" :
            r.severity === "HIGH"     ? "bg-amber-500/10 border-amber-500/40 text-amber-300" :
            r.severity === "MEDIUM"   ? "bg-blue-500/10 border-blue-500/40 text-blue-300" :
                                        "bg-stone-500/10 border-stone-500/40 text-stone-300"
          }`}>{r.severity}</span>
          <div className="font-semibold text-white text-sm">{r.title}</div>
        </div>
        <div className="text-xs text-stone-400 mt-2"><strong className="text-stone-300">Mitigare:</strong> {r.mitigation}</div>
      </div>
    ))}
  </div>
);

const SectionAI = ({ idea }) => (
  <div className="space-y-3">
    <H>Integrare AI (reutilizare infrastructură existentă)</H>
    <p className="text-sm text-stone-300 mb-3">{idea.ai.philosophy}</p>
    {idea.ai.touchpoints.map((t, i) => (
      <div key={i} className="border border-white/10 rounded-xl p-4 bg-white/[0.02]">
        <div className="font-semibold text-white text-sm">{t.title}</div>
        <div className="text-xs text-stone-400 mt-1">{t.description}</div>
        <div className="text-[11px] text-stone-500 mt-2">
          <strong>Reuse:</strong> {t.reuse} · <strong>Fază:</strong> {t.phase}
        </div>
      </div>
    ))}
  </div>
);

const SectionROI = ({ idea }) => (
  <div className="space-y-5">
    {/* DUAL METRICS — Emergent vs Freelance */}
    <div>
      <H>Estimare Emergent (cost real pentru tine)</H>
      <div className="grid sm:grid-cols-3 gap-3">
        <div className="border border-violet-500/40 rounded-xl p-4 bg-violet-500/5">
          <div className="text-[10px] uppercase text-violet-300">Complexitate</div>
          <div className="text-2xl font-mono mt-1 text-white">{idea.emergentComplexity || "—"}</div>
          <div className="text-[10px] text-stone-500 mt-1">Cât de dificil arhitectural</div>
        </div>
        <div className="border border-violet-500/40 rounded-xl p-4 bg-violet-500/5">
          <div className="text-[10px] uppercase text-violet-300">Effort estimat</div>
          <div className="text-sm font-mono mt-1 text-white leading-tight">{idea.emergentEffort || "—"}</div>
          <div className="text-[10px] text-stone-500 mt-1">Task-uri agent necesare</div>
        </div>
        <div className="border border-violet-500/40 rounded-xl p-4 bg-violet-500/5">
          <div className="text-[10px] uppercase text-violet-300">Credite Emergent estimate</div>
          <div className="text-xl font-mono mt-1 text-violet-200">{idea.emergentCreditsEstimate || "—"}</div>
          <div className="text-[10px] text-stone-500 mt-1">Updated în timp real pe parcursul dev</div>
        </div>
      </div>
      <div className="mt-3 text-[11px] text-stone-500 bg-white/[0.02] border border-white/5 rounded-lg p-3">
        💡 Costul real Emergent = credite consumate per task agent. Verifici în Profile → Billing. Eu îți voi raporta consumul aproximativ după fiecare task major odată ce începem implementarea.
      </div>
    </div>

    {/* THEORETICAL REFERENCE */}
    <div>
      <H>Referință teoretică (dacă ai externaliza freelance)</H>
      <div className="grid sm:grid-cols-3 gap-3">
        <div className="border border-white/10 rounded-xl p-4 bg-white/[0.02]">
          <div className="text-[10px] uppercase text-stone-400">Cost freelance one-time</div>
          <div className="text-2xl font-mono mt-1 text-stone-200">~{idea.estCostEur}€</div>
          <div className="text-[10px] text-stone-500 mt-1">{idea.timelineDays} zile × 200€/zi mid-level</div>
        </div>
        <div className="border border-white/10 rounded-xl p-4 bg-white/[0.02]">
          <div className="text-[10px] uppercase text-stone-400">Opex lunar (după lansare)</div>
          <div className="text-2xl font-mono mt-1 text-stone-200">~{idea.estOpexMonthly}€</div>
          <div className="text-[10px] text-stone-500 mt-1">AI calls + storage + emails</div>
        </div>
        <div className="border border-emerald-500/30 rounded-xl p-4 bg-emerald-500/5">
          <div className="text-[10px] uppercase text-emerald-300">Venit potențial lunar</div>
          <div className="text-xl font-mono mt-1 text-emerald-300">{idea.estRevenueRange}</div>
          <div className="text-[10px] text-stone-500 mt-1">Pesimist → optimist</div>
        </div>
      </div>
      <div className="mt-3 text-[11px] text-stone-500">
        ⚠️ Aceste valori sunt <strong>orientative pentru comparație</strong> — pe Emergent nu plătești 5.000€, plătești credite proporțional cu munca efectivă.
      </div>
    </div>

    {/* BUSINESS IMPACT */}
    {idea.businessImpact && (
      <div>
        <H>Impact business direct</H>
        <div className="text-sm text-stone-200 leading-relaxed bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4">
          {idea.businessImpact}
        </div>
      </div>
    )}

    <div>
      <H>Scenarii de monetizare</H>
      <div className="space-y-2">
        {idea.revenueScenarios.map((s, i) => (
          <div key={i} className="border border-white/10 rounded-xl p-3 bg-white/[0.02]">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="font-semibold text-white text-sm">{s.name}</div>
              <div className="text-emerald-300 font-mono text-sm">{s.estimatedRevenue}</div>
            </div>
            <div className="text-xs text-stone-400 mt-1">{s.description}</div>
          </div>
        ))}
      </div>
    </div>
    <div>
      <H>Break-even & Payback</H>
      <div className="text-sm text-stone-300 leading-relaxed">{idea.breakEven}</div>
    </div>
    <div>
      <H>Recomandare strategică</H>
      <div className="text-sm text-stone-300 leading-relaxed border-l-2 border-[#d4ff3a] pl-3">{idea.recommendation}</div>
    </div>
  </div>
);

// ============================================================================
// HISTORY TAB — chronological decision timeline per idea
// ============================================================================
const SectionHistory = ({ status }) => {
  const log = [...(status?.decision_log || [])].reverse(); // newest first
  if (log.length === 0) {
    return (
      <div className="text-center py-10">
        <History className="w-10 h-10 text-stone-600 mx-auto mb-3" />
        <div className="text-sm text-stone-400">Nicio decizie istorică încă</div>
        <div className="text-xs text-stone-500 mt-1 max-w-md mx-auto">
          Istoricul se completează automat când schimbi statusul propunerii. Fiecare schimbare cere un motiv documentat, păstrat aici permanent pentru audit decizional.
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-4" data-testid="fi-history-list">
      <H>Cronologie decizii ({log.length})</H>
      <div className="relative pl-6">
        {/* timeline vertical line */}
        <div className="absolute left-2 top-2 bottom-2 w-px bg-gradient-to-b from-violet-500/40 via-white/10 to-transparent"></div>

        {log.map((entry, i) => {
          const fromMeta = STATUS_META[entry.from_status] || STATUS_META.pending_validation;
          const toMeta = STATUS_META[entry.to_status] || STATUS_META.pending_validation;
          const FromIcon = fromMeta.icon;
          const ToIcon = toMeta.icon;
          return (
            <div key={i} className="relative pl-6 pb-5" data-testid={`fi-history-entry-${i}`}>
              {/* timeline dot */}
              <div className="absolute -left-[5px] top-1 w-3 h-3 rounded-full bg-violet-500 border-2 border-[#0e0e10] shadow-[0_0_0_2px_rgba(139,92,246,0.3)]"></div>
              <div className="bg-white/[0.02] border border-white/10 rounded-xl p-4">
                <div className="flex items-center gap-2 flex-wrap text-xs">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border ${colorClasses(fromMeta.color)}`}>
                    <FromIcon className="w-3 h-3" /> {fromMeta.label}
                  </span>
                  <ArrowRight className="w-3.5 h-3.5 text-stone-500" />
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border ${colorClasses(toMeta.color)}`}>
                    <ToIcon className="w-3 h-3" /> {toMeta.label}
                  </span>
                  <span className="ml-auto text-[10px] text-stone-500">
                    {new Date(entry.at).toLocaleString("ro-RO", { dateStyle: "medium", timeStyle: "short" })}
                  </span>
                </div>
                <div className="mt-3 text-sm text-stone-200 leading-relaxed whitespace-pre-wrap">
                  {entry.reason}
                </div>
                <div className="mt-2 text-[10px] text-stone-500">
                  Decizia luată de: <span className="text-stone-400">{entry.by}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="bg-violet-500/5 border border-violet-500/20 rounded-xl p-3 text-xs text-violet-100 flex items-start gap-2">
        <Lock className="w-3.5 h-3.5 shrink-0 mt-0.5 text-violet-300" />
        <div>Istoricul este <strong>imutabil</strong> — odată salvată, o decizie nu poate fi editată sau ștearsă. Util pentru audit strategic și pentru a-ți aminti peste 6 luni "de ce" ai luat o decizie.</div>
      </div>
    </div>
  );
};

// ============================================================================
// DECISION REASON MODAL — required when status changes
// ============================================================================
const DecisionReasonModal = ({ fromStatus, toStatus, ideaTitle, saving, error, onCancel, onConfirm }) => {
  const [reason, setReason] = useState("");
  const fromMeta = STATUS_META[fromStatus];
  const toMeta = STATUS_META[toStatus];
  const FromIcon = fromMeta.icon;
  const ToIcon = toMeta.icon;
  const valid = reason.trim().length >= 3;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm" data-testid="fi-reason-modal">
      <div className="bg-[#0a0a0b] border border-violet-500/40 rounded-2xl max-w-lg w-full overflow-hidden">
        <div className="px-5 py-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/30 flex items-center justify-center">
              <History className="w-5 h-5 text-violet-300" />
            </div>
            <div>
              <h2 className="font-serif text-lg text-white">Justificare decizie</h2>
              <p className="text-[11px] text-stone-500">Va fi păstrată permanent în istoric · imutabilă</p>
            </div>
          </div>
        </div>

        <div className="px-5 py-4">
          <div className="text-xs text-stone-400 mb-2">Propunere:</div>
          <div className="text-sm text-white font-semibold mb-4">{ideaTitle}</div>

          <div className="flex items-center gap-2 flex-wrap mb-4">
            <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full border ${colorClasses(fromMeta.color)}`}>
              <FromIcon className="w-3 h-3" /> {fromMeta.label}
            </span>
            <ArrowRight className="w-4 h-4 text-stone-500" />
            <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full border ${colorClasses(toMeta.color)}`}>
              <ToIcon className="w-3 h-3" /> {toMeta.label}
            </span>
          </div>

          <label className="text-[10px] uppercase tracking-wider text-violet-300 block mb-2">
            Motiv principal (obligatoriu, min. 3 caractere)
          </label>
          <textarea
            autoFocus
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={4}
            className="w-full bg-[#0e0e10] border border-violet-500/30 focus:border-violet-500/60 rounded-lg px-3 py-2 text-sm outline-none"
            placeholder="ex: validat cu 3 specialiști vechi, ROI estimat 19x conform istoric 2025, începem cu Phase MKT-0 + MKT-1..."
            data-testid="fi-reason-input"
          />
          <div className="text-[10px] text-stone-500 mt-2">
            💡 Tip: scrie ce ai luat în considerare (date, validări, riscuri acceptate). Te va ajuta peste 6 luni să-ți amintești context-ul.
          </div>

          {error && (
            <div className="mt-3 bg-red-500/10 border border-red-500/30 rounded-lg p-2 text-xs text-red-300 flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5" /> {error}
            </div>
          )}
        </div>

        <div className="px-5 py-3 border-t border-white/10 bg-white/[0.02] flex items-center justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={saving}
            className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-stone-300 text-sm hover:bg-white/10 disabled:opacity-50"
            data-testid="fi-reason-cancel"
          >Anulează</button>
          <button
            onClick={() => onConfirm(reason.trim())}
            disabled={!valid || saving}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500 text-white text-sm font-semibold hover:bg-violet-600 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="fi-reason-confirm"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Confirmă & salvează
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// COMPARATOR MODAL — side-by-side comparison of all proposals
// ============================================================================
const ComparatorModal = ({ ideas, statuses, onClose }) => {
  const [sortBy, setSortBy] = useState("roi"); // roi | risk | duration | credits
  const [filter, setFilter] = useState("all"); // all | approved | pending | rejected

  // Compute ROI score (rough heuristic for sorting)
  const computeRoiScore = (idea, st) => {
    const cost = st?.estimated_cost_eur ?? idea.estCostEur ?? 1;
    const revenue = st?.estimated_revenue_eur_monthly ?? idea.estRevenueMonthly ?? 0;
    // Months to recoup = cost / monthly_revenue (lower = better ROI)
    return revenue > 0 ? cost / revenue : 999;
  };

  const filterFn = (idea) => {
    if (filter === "all") return true;
    const st = statuses[idea.id]?.status || "pending_validation";
    if (filter === "approved") return st === "approved" || st === "in_discussion";
    if (filter === "pending")  return st === "pending_validation";
    if (filter === "rejected") return st === "rejected" || st === "on_hold";
    return true;
  };

  const sortedIdeas = [...ideas].filter(filterFn).sort((a, b) => {
    const sA = statuses[a.id];
    const sB = statuses[b.id];
    if (sortBy === "roi")      return computeRoiScore(a, sA) - computeRoiScore(b, sB);
    if (sortBy === "risk")     return (a.risk || 5) - (b.risk || 5);
    if (sortBy === "duration") return (a.timelineDays || 0) - (b.timelineDays || 0);
    if (sortBy === "credits") {
      const cA = parseInt((a.emergentCreditsEstimate || "0").match(/\d+/)?.[0] || 999);
      const cB = parseInt((b.emergentCreditsEstimate || "0").match(/\d+/)?.[0] || 999);
      return cA - cB;
    }
    return 0;
  });

  const totalApprovedCost = ideas
    .filter(i => ["approved", "in_discussion"].includes(statuses[i.id]?.status))
    .reduce((acc, i) => acc + (statuses[i.id]?.estimated_cost_eur ?? i.estCostEur ?? 0), 0);
  const totalApprovedRevenue = ideas
    .filter(i => ["approved", "in_discussion"].includes(statuses[i.id]?.status))
    .reduce((acc, i) => acc + (statuses[i.id]?.estimated_revenue_eur_monthly ?? i.estRevenueMonthly ?? 0), 0);
  const totalCreditsUsed = ideas.reduce((acc, i) => acc + (statuses[i.id]?.emergent_credits_used || 0), 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/80 backdrop-blur-sm" data-testid="fi-comparator-modal">
      <div className="bg-[#0a0a0b] border border-violet-500/30 rounded-2xl max-w-7xl w-full max-h-[95vh] overflow-hidden flex flex-col">
        {/* HEADER */}
        <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/30 flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-violet-300" />
            </div>
            <div>
              <h2 className="font-serif text-xl text-white">Comparator Propuneri</h2>
              <p className="text-[11px] text-stone-500">Side-by-side decision tool · {sortedIdeas.length} din {ideas.length} propuneri</p>
            </div>
          </div>
          <button onClick={onClose} className="w-9 h-9 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center" data-testid="fi-comparator-close">
            <XIcon className="w-4 h-4 text-stone-400" />
          </button>
        </div>

        {/* TOTALS BANNER */}
        <div className="px-5 py-3 bg-violet-500/5 border-b border-violet-500/20 grid sm:grid-cols-3 gap-3 text-xs">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-violet-300">Total cost dev (aprobate / în discuție)</div>
            <div className="text-lg font-mono text-white mt-0.5">~{totalApprovedCost.toLocaleString("ro-RO")}€</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-violet-300">Total venit potențial / lună</div>
            <div className="text-lg font-mono text-emerald-300 mt-0.5">~{totalApprovedRevenue.toLocaleString("ro-RO")}€</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-violet-300">Credite Emergent consumate (total)</div>
            <div className="text-lg font-mono text-white mt-0.5">{totalCreditsUsed}</div>
          </div>
        </div>

        {/* CONTROLS */}
        <div className="px-5 py-3 border-b border-white/10 flex items-center gap-2 flex-wrap text-xs">
          <span className="text-stone-500">Sortează:</span>
          {[
            { id: "roi",      label: "ROI (luni recuperare)" },
            { id: "risk",     label: "Risc" },
            { id: "duration", label: "Durată" },
            { id: "credits",  label: "Credite Emergent" },
          ].map(s => (
            <button
              key={s.id}
              onClick={() => setSortBy(s.id)}
              className={`px-2.5 py-1 rounded-lg border transition-colors ${
                sortBy === s.id ? "bg-violet-500/20 border-violet-500/40 text-violet-200" : "bg-white/5 border-white/10 text-stone-400 hover:text-white"
              }`}
              data-testid={`fi-sort-${s.id}`}
            >{s.label}</button>
          ))}
          <span className="text-stone-500 ml-3">Filtru:</span>
          {[
            { id: "all",      label: "Toate" },
            { id: "approved", label: "Aprobate / discuție" },
            { id: "pending",  label: "În evaluare" },
            { id: "rejected", label: "Respinse / pauză" },
          ].map(f => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`px-2.5 py-1 rounded-lg border transition-colors ${
                filter === f.id ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-200" : "bg-white/5 border-white/10 text-stone-400 hover:text-white"
              }`}
              data-testid={`fi-filter-${f.id}`}
            >{f.label}</button>
          ))}
        </div>

        {/* TABLE */}
        <div className="flex-1 overflow-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-[#0a0a0b] z-10">
              <tr className="border-b border-white/10 text-[10px] uppercase tracking-wider text-stone-500">
                <th className="text-left px-3 py-3 font-medium">Propunere</th>
                <th className="text-left px-3 py-3 font-medium">Status</th>
                <th className="text-right px-3 py-3 font-medium">Risc</th>
                <th className="text-right px-3 py-3 font-medium">Faze</th>
                <th className="text-right px-3 py-3 font-medium">Durată<br/>(ref.)</th>
                <th className="text-right px-3 py-3 font-medium">Cost dev<br/>(€ ref.)</th>
                <th className="text-right px-3 py-3 font-medium">Credite<br/>Emergent</th>
                <th className="text-right px-3 py-3 font-medium">Opex<br/>€/lună</th>
                <th className="text-right px-3 py-3 font-medium">Venit<br/>€/lună</th>
                <th className="text-right px-3 py-3 font-medium">ROI<br/>(luni)</th>
                <th className="text-right px-3 py-3 font-medium">Credite<br/>consumate</th>
              </tr>
            </thead>
            <tbody>
              {sortedIdeas.map(idea => {
                const st = statuses[idea.id];
                const stKey = st?.status || "pending_validation";
                const sMeta = STATUS_META[stKey];
                const cost = st?.estimated_cost_eur ?? idea.estCostEur;
                const rev  = st?.estimated_revenue_eur_monthly ?? idea.estRevenueMonthly;
                const roi  = rev > 0 ? (cost / rev).toFixed(1) : "—";
                return (
                  <tr key={idea.id} className="border-b border-white/5 hover:bg-white/[0.02]" data-testid={`fi-comp-row-${idea.id}`}>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-2">
                        <idea.icon className="w-4 h-4 text-stone-400 shrink-0" />
                        <div className="min-w-0">
                          <div className="font-mono text-[10px] text-stone-500">{idea.code}</div>
                          <div className="text-sm text-white truncate max-w-[200px]" title={idea.title}>{idea.title}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <span className={`inline-block text-[10px] uppercase px-2 py-0.5 rounded-full border ${colorClasses(sMeta.color)}`}>
                        {sMeta.label}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <span className={`font-mono ${idea.risk <= 3 ? "text-emerald-300" : idea.risk <= 5 ? "text-amber-300" : idea.risk <= 7 ? "text-orange-300" : "text-red-300"}`}>
                        {idea.risk}/10
                      </span>
                    </td>
                    <td className="px-3 py-3 text-right text-stone-300 font-mono">{idea.phases.length}</td>
                    <td className="px-3 py-3 text-right text-stone-300 font-mono">{idea.timelineDays}z</td>
                    <td className="px-3 py-3 text-right text-stone-300 font-mono">{cost?.toLocaleString("ro-RO")}€</td>
                    <td className="px-3 py-3 text-right text-violet-300 font-mono text-[11px]">{idea.emergentCreditsEstimate || "—"}</td>
                    <td className="px-3 py-3 text-right text-stone-300 font-mono">{idea.estOpexMonthly}€</td>
                    <td className="px-3 py-3 text-right text-emerald-300 font-mono">{rev > 0 ? `~${rev.toLocaleString("ro-RO")}€` : "—"}</td>
                    <td className="px-3 py-3 text-right">
                      <span className={`font-mono ${roi === "—" ? "text-stone-500" : Number(roi) <= 3 ? "text-emerald-300" : Number(roi) <= 6 ? "text-amber-300" : "text-red-300"}`}>
                        {roi !== "—" ? `${roi} luni` : "—"}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-right text-stone-300 font-mono">
                      {st?.emergent_credits_used ?? "—"}
                    </td>
                  </tr>
                );
              })}
              {sortedIdeas.length === 0 && (
                <tr><td colSpan={11} className="text-center text-stone-500 py-10">Niciun rezultat pentru filtrul curent</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* LEGEND FOOTER */}
        <div className="px-5 py-3 border-t border-white/10 bg-white/[0.02] text-[10px] text-stone-500 flex flex-wrap gap-x-4 gap-y-1">
          <span><strong className="text-emerald-300">ROI verde</strong>: ≤3 luni payback</span>
          <span><strong className="text-amber-300">ROI galben</strong>: 4-6 luni</span>
          <span><strong className="text-red-300">ROI roșu</strong>: &gt;6 luni</span>
          <span className="ml-auto">💡 ROI = Cost dev / Venit lunar. Mai mic = mai bine.</span>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// DIGEST MODAL — weekly email config + send-now + history
// ============================================================================
const DigestModal = ({ onClose }) => {
  const [cfg, setCfg] = useState(null);
  const [history, setHistory] = useState([]);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [recipientsInput, setRecipientsInput] = useState("");
  const [staleDaysInput, setStaleDaysInput] = useState(30);

  const load = async () => {
    setLoading(true);
    try {
      const [c, h, p] = await Promise.all([
        ax.get("/api/admin/future-ideas-digest/config"),
        ax.get("/api/admin/future-ideas-digest/history?limit=10"),
        ax.get("/api/admin/future-ideas-digest/preview"),
      ]);
      setCfg(c.data);
      setHistory(h.data.items || []);
      setPreview(p.data);
      setRecipientsInput((c.data.recipients || []).join(", "));
      setStaleDaysInput(c.data.stale_threshold_days || 30);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const saveConfig = async (patch) => {
    setSaving(true);
    setFeedback(null);
    try {
      const { data } = await ax.put("/api/admin/future-ideas-digest/config", patch);
      setCfg(data);
      setFeedback({ type: "ok", text: "Setări salvate" });
      setTimeout(() => setFeedback(null), 2200);
    } catch (e) {
      setFeedback({ type: "err", text: e?.response?.data?.detail || "Eroare la salvare" });
    } finally { setSaving(false); }
  };

  const toggleEnabled = () => saveConfig({ enabled: !cfg.enabled });

  const saveRecipients = () => {
    const list = recipientsInput.split(",").map(s => s.trim()).filter(Boolean);
    saveConfig({ recipients: list, stale_threshold_days: Number(staleDaysInput) });
  };

  const sendNow = async () => {
    setSending(true);
    setFeedback(null);
    try {
      const { data } = await ax.post("/api/admin/future-ideas-digest/send-now", {});
      if (data.skipped) {
        setFeedback({ type: "err", text: `Trimitere sărită: ${data.skipped}` });
      } else if (data.ok) {
        setFeedback({ type: "ok", text: `Trimis: ${data.subject}` });
        load();
      } else {
        setFeedback({ type: "err", text: `Eroare trimitere: ${data.error || "necunoscută"}` });
      }
    } catch (e) {
      setFeedback({ type: "err", text: e?.response?.data?.detail || "Eroare trimitere" });
    } finally { setSending(false); }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
        <div className="bg-[#0a0a0b] border border-blue-500/30 rounded-2xl px-8 py-6 flex items-center gap-3 text-stone-400">
          <Loader2 className="w-5 h-5 animate-spin text-blue-300" /> Se încarcă configurarea...
        </div>
      </div>
    );
  }

  const nStale = preview?.data?.stale_items?.length || 0;
  const nRecent = preview?.data?.recent_decisions?.length || 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/80 backdrop-blur-sm" data-testid="fi-digest-modal">
      <div className="bg-[#0a0a0b] border border-blue-500/30 rounded-2xl max-w-3xl w-full max-h-[95vh] overflow-hidden flex flex-col">
        <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center">
              <Mail className="w-5 h-5 text-blue-300" />
            </div>
            <div>
              <h2 className="font-serif text-xl text-white">Digest Email Săptămânal</h2>
              <p className="text-[11px] text-stone-500">Trimis automat Lunea 09:15 · Europe/Bucharest</p>
            </div>
          </div>
          <button onClick={onClose} className="w-9 h-9 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center" data-testid="fi-digest-close">
            <XIcon className="w-4 h-4 text-stone-400" />
          </button>
        </div>

        <div className="flex-1 overflow-auto px-5 py-4 space-y-5">
          {/* TOGGLE */}
          <div className="flex items-center justify-between bg-[#0e0e10] border border-white/10 rounded-xl p-4">
            <div>
              <div className="text-sm text-white font-semibold">Digest activat</div>
              <div className="text-[11px] text-stone-500 mt-0.5">
                Când e ON, email-ul se trimite automat luni dimineața la 09:15
              </div>
            </div>
            <button
              onClick={toggleEnabled}
              disabled={saving}
              className={`relative w-12 h-7 rounded-full transition-colors ${cfg.enabled ? "bg-emerald-500" : "bg-stone-700"}`}
              data-testid="fi-digest-toggle"
            >
              <span className={`absolute top-0.5 left-0.5 w-6 h-6 rounded-full bg-white transition-transform ${cfg.enabled ? "translate-x-5" : ""}`}></span>
            </button>
          </div>

          {/* CONFIG */}
          <div className="bg-[#0e0e10] border border-white/10 rounded-xl p-4 space-y-3">
            <div className="text-xs uppercase tracking-wider text-stone-400">Configurare</div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-stone-400">Destinatari (separate prin virgulă)</label>
              <input
                type="text"
                value={recipientsInput}
                onChange={(e) => setRecipientsInput(e.target.value)}
                className="mt-2 w-full bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm"
                placeholder="admin@propmanage.io, partner@..."
                data-testid="fi-digest-recipients"
              />
            </div>
            <div className="flex items-end gap-3 flex-wrap">
              <div className="flex-1 min-w-[150px]">
                <label className="text-[10px] uppercase tracking-wider text-stone-400">Prag "uitate" (zile)</label>
                <input
                  type="number"
                  min={7}
                  max={365}
                  value={staleDaysInput}
                  onChange={(e) => setStaleDaysInput(e.target.value)}
                  className="mt-2 w-full bg-[#0a0a0b] border border-white/10 rounded-lg px-3 py-2 text-sm font-mono"
                  data-testid="fi-digest-threshold"
                />
              </div>
              <button
                onClick={saveRecipients}
                disabled={saving}
                className="px-4 py-2 rounded-xl bg-white/10 border border-white/20 text-stone-200 text-sm hover:bg-white/15 disabled:opacity-50"
                data-testid="fi-digest-save-config"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Salvează"}
              </button>
            </div>
            <div className="text-[10px] text-stone-500">
              💡 Propunerile rămase în "În evaluare" sau "În discuție" mai mult de {staleDaysInput} zile fără modificare apar în digest.
            </div>
          </div>

          {/* PREVIEW STATS */}
          <div className="bg-[#0e0e10] border border-blue-500/20 rounded-xl p-4">
            <div className="text-xs uppercase tracking-wider text-blue-300 mb-3">Preview content (pe baza datelor curente)</div>
            <div className="grid sm:grid-cols-2 gap-3">
              <div className="bg-amber-500/5 border border-amber-500/30 rounded-lg p-3">
                <div className="text-[10px] uppercase text-amber-300">Propuneri uitate</div>
                <div className="text-2xl font-mono text-white mt-1">{nStale}</div>
                <div className="text-[10px] text-stone-500 mt-1">{`> ${cfg.stale_threshold_days} zile fără decizie`}</div>
              </div>
              <div className="bg-violet-500/5 border border-violet-500/30 rounded-lg p-3">
                <div className="text-[10px] uppercase text-violet-300">Decizii ultimele 7 zile</div>
                <div className="text-2xl font-mono text-white mt-1">{nRecent}</div>
                <div className="text-[10px] text-stone-500 mt-1">cross-propuneri</div>
              </div>
            </div>
          </div>

          {/* SEND NOW */}
          <button
            onClick={sendNow}
            disabled={sending || cfg.recipients.length === 0}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-blue-500 hover:bg-blue-600 text-white text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="fi-digest-send-now"
          >
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Trimite acum (test) {cfg.recipients.length > 0 ? `→ ${cfg.recipients.length} destinatari` : "(necesită destinatari)"}
          </button>

          {feedback && (
            <div className={`text-xs rounded-lg p-3 border flex items-center gap-2 ${
              feedback.type === "ok" ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" : "bg-red-500/10 border-red-500/30 text-red-300"
            }`}>
              {feedback.type === "ok" ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
              {feedback.text}
            </div>
          )}

          {/* HISTORY */}
          <div>
            <div className="text-xs uppercase tracking-wider text-stone-400 mb-2 flex items-center gap-2">
              <History className="w-3.5 h-3.5" /> Istoric trimiteri ({history.length})
            </div>
            {history.length === 0 ? (
              <div className="text-xs text-stone-500 bg-white/[0.02] rounded-lg p-3 italic">Niciun digest trimis încă.</div>
            ) : (
              <div className="space-y-1 max-h-48 overflow-auto">
                {history.map((h, i) => (
                  <div key={i} className="text-[11px] bg-white/[0.02] border border-white/5 rounded-lg p-2 flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${h.ok ? "bg-emerald-400" : "bg-red-400"}`}></span>
                    <span className="text-stone-400 font-mono">{new Date(h.sent_at).toLocaleString("ro-RO")}</span>
                    <span className="text-stone-500">·</span>
                    <span className="text-stone-300 truncate flex-1">{h.subject}</span>
                    {h.forced && <span className="text-[9px] text-blue-300 uppercase">manual</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="px-5 py-3 border-t border-white/10 bg-white/[0.02] text-[10px] text-stone-500">
          💡 Schedule automat: <strong className="text-stone-300">Luni 09:15 Europe/Bucharest</strong>. Dezactivează din toggle de mai sus pentru a opri trimiterile automate.
          {cfg.last_sent_at && (
            <span className="ml-2">· Ultima trimitere: {new Date(cfg.last_sent_at).toLocaleString("ro-RO")}</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default FutureIdeasVault;
