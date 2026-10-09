// /admin/support-inbox — list & manage contact messages sent via Contactează-ne.
// Visible to admin AND operator (both roles receive notifications).
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import { ArrowLeft, Mail, CheckCircle2, Clock, RefreshCw, AlertCircle, User as UserIcon, Inbox } from "lucide-react";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const STATUS_META = {
  new:         { label: "Nou",       color: "bg-amber-500/15 text-amber-300 border-amber-500/30", icon: AlertCircle },
  in_progress: { label: "În lucru",  color: "bg-blue-500/15 text-blue-300 border-blue-500/30",   icon: Clock },
  resolved:    { label: "Rezolvat",  color: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30", icon: CheckCircle2 },
};

export const AdminSupportInboxPage = () => {
  const [data, setData] = useState({ items: [], counts: { new: 0, in_progress: 0, resolved: 0 } });
  const [filter, setFilter] = useState("");  // "" = all, or new/in_progress/resolved
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  const load = async () => {
    try {
      const url = filter ? `${API}/support/inbox?status=${filter}` : `${API}/support/inbox`;
      const r = await axios.get(url);
      setData(r.data);
      setErr(null);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter]);

  const updateStatus = async (id, status) => {
    try {
      await axios.patch(`${API}/support/inbox/${id}`, { status });
      await load();
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    }
  };

  if (loading) return <div className="min-h-screen bg-stone-950 text-stone-400 flex items-center justify-center" data-testid="inbox-loading">Se încarcă inbox…</div>;
  if (err) return <div className="min-h-screen bg-stone-950 text-red-300 p-8" data-testid="inbox-error">Eroare: {err}</div>;

  return (
    <div className="min-h-screen bg-stone-950 text-white p-6 lg:p-10" data-testid="admin-support-inbox-page">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Link to="/admin" className="inline-flex items-center gap-2 text-xs text-stone-500 hover:text-white mb-2">
              <ArrowLeft className="w-3 h-3" /> Admin Dashboard
            </Link>
            <h1 className="font-serif text-3xl flex items-center gap-3" data-testid="inbox-title">
              <Inbox className="w-7 h-7 text-[#d4ff3a]" />
              Mesaje de la utilizatori
            </h1>
            <p className="text-stone-500 text-sm mt-1">Toate mesajele trimise via &quot;Contactează-ne&quot; · Vizibile pentru Admin + Operator</p>
          </div>
          <button onClick={load} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-xs" data-testid="inbox-refresh">
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>

        {/* Filter tabs */}
        <div className="flex flex-wrap gap-2">
          {[
            { val: "",            label: `Toate (${(data.counts.new || 0) + (data.counts.in_progress || 0) + (data.counts.resolved || 0)})` },
            { val: "new",         label: `Noi (${data.counts.new || 0})`,         pulse: (data.counts.new || 0) > 0 },
            { val: "in_progress", label: `În lucru (${data.counts.in_progress || 0})` },
            { val: "resolved",    label: `Rezolvate (${data.counts.resolved || 0})` },
          ].map(t => (
            <button
              key={t.val}
              onClick={() => setFilter(t.val)}
              className={`px-4 py-1.5 rounded-full text-xs font-medium border ${filter === t.val ? "bg-[#d4ff3a] text-black border-[#d4ff3a]" : "bg-white/5 text-stone-300 border-white/10 hover:bg-white/10"} ${t.pulse ? "ring-2 ring-amber-500/40" : ""}`}
              data-testid={`inbox-filter-${t.val || "all"}`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Messages list */}
        <div className="space-y-3" data-testid="inbox-list">
          {data.items.length === 0 && (
            <div className="rounded-2xl bg-white/[0.03] border border-white/10 p-12 text-center text-stone-500">
              <Mail className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p className="text-sm">Niciun mesaj {filter ? `cu statusul "${STATUS_META[filter]?.label}"` : ""}.</p>
            </div>
          )}
          {data.items.map(m => {
            const meta = STATUS_META[m.status] || STATUS_META.new;
            const StatusIcon = meta.icon;
            return (
              <div key={m.id} className="rounded-2xl bg-white/[0.03] border border-white/10 p-5" data-testid={`inbox-msg-${m.id}`}>
                <div className="flex items-start gap-3 mb-3">
                  <div className="w-9 h-9 rounded-full bg-stone-800 flex items-center justify-center text-stone-400 shrink-0">
                    <UserIcon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-white font-medium text-sm">{m.user_name}</span>
                      <a href={`mailto:${m.user_email}?subject=Re: ${encodeURIComponent(m.subject)}`} className="text-xs text-[#d4ff3a] hover:underline" data-testid={`inbox-reply-${m.id}`}>
                        {m.user_email}
                      </a>
                      <span className="text-[10px] uppercase text-stone-500 border border-white/10 rounded-full px-2 py-0.5">{m.user_role}</span>
                    </div>
                    <div className="text-[10px] text-stone-600 mt-0.5">#{m.id.slice(0, 8)} · {new Date(m.created_at).toLocaleString("ro-RO")}</div>
                  </div>
                  <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] uppercase font-medium border ${meta.color}`}>
                    <StatusIcon className="w-3 h-3" /> {meta.label}
                  </span>
                </div>
                <div className="text-sm text-white font-medium mb-1.5">{m.subject}</div>
                <div className="text-sm text-stone-300 whitespace-pre-wrap leading-relaxed mb-4">{m.message}</div>
                <div className="flex items-center gap-2 flex-wrap">
                  <a
                    href={`mailto:${m.user_email}?subject=Re: ${encodeURIComponent(m.subject)}&body=${encodeURIComponent("Salut " + m.user_name + ",\n\n")}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#d4ff3a] hover:bg-[#c5f000] text-black text-xs font-semibold"
                    data-testid={`inbox-reply-btn-${m.id}`}
                  >
                    <Mail className="w-3 h-3" /> Răspunde pe email
                  </a>
                  {m.status !== "in_progress" && (
                    <button onClick={() => updateStatus(m.id, "in_progress")} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30 text-xs hover:bg-blue-500/25" data-testid={`inbox-progress-${m.id}`}>
                      <Clock className="w-3 h-3" /> În lucru
                    </button>
                  )}
                  {m.status !== "resolved" && (
                    <button onClick={() => updateStatus(m.id, "resolved")} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-xs hover:bg-emerald-500/25" data-testid={`inbox-resolve-${m.id}`}>
                      <CheckCircle2 className="w-3 h-3" /> Marchează rezolvat
                    </button>
                  )}
                  {m.status === "resolved" && (
                    <button onClick={() => updateStatus(m.id, "new")} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 text-stone-400 border border-white/10 text-xs hover:bg-white/10" data-testid={`inbox-reopen-${m.id}`}>
                      Redeschide
                    </button>
                  )}
                  {m.resolved_by && (
                    <span className="text-[10px] text-stone-500 ml-auto">Rezolvat de {m.resolved_by}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default AdminSupportInboxPage;
