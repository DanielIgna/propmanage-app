// AdminConciergePanel — Phase 47: Manage Concierge settings, view conversations,
// inspect security events, configure GEO/VPN/bot/rate-limit guards.
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  ShieldCheck, Globe, Bot, Activity, MessageSquare, Lock, Unlock,
  TriangleAlert, RefreshCw, ChevronRight, X
} from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

const KIND_LABELS = {
  bot_blocked: { label: "Bot blocat", color: "text-red-600 bg-red-50 dark:bg-red-500/15 dark:text-red-300 border-red-200 dark:border-red-500/30" },
  vpn_blocked: { label: "VPN/proxy", color: "text-orange-600 bg-orange-50 dark:bg-orange-500/15 dark:text-orange-300 border-orange-200 dark:border-orange-500/30" },
  geo_blocked: { label: "Țară blocată", color: "text-purple-600 bg-purple-50 dark:bg-purple-500/15 dark:text-purple-300 border-purple-200 dark:border-purple-500/30" },
  rate_limit_ip: { label: "Rate-limit IP", color: "text-amber-600 bg-amber-50 dark:bg-amber-500/15 dark:text-amber-300 border-amber-200 dark:border-amber-500/30" },
  concierge_quota_exhausted: { label: "Cotă concierge", color: "text-amber-600 bg-amber-50 dark:bg-amber-500/15 dark:text-amber-300 border-amber-200 dark:border-amber-500/30" },
};

const SecurityConfigCard = () => {
  const [cfg, setCfg] = useState(null);
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = () => axios.get(`${API}/admin/security/config`).then(r => { setCfg(r.data); setDraft(r.data); }).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async () => {
    setSaving(true);
    try {
      const r = await axios.put(`${API}/admin/security/config`, draft);
      setCfg(r.data);
      setDraft(r.data);
    } catch (e) {
      window.alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (!cfg || !draft) return <AdminCard title="Setări securitate"><div className="text-slate-400 text-sm">Se încarcă...</div></AdminCard>;

  const dirty = JSON.stringify(cfg) !== JSON.stringify(draft);

  return (
    <AdminCard
      title={<div className="flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-500" /> Setări Behavioral Security Guard</div>}
      action={
        <AdminBtn variant={dirty ? "primary" : "secondary"} onClick={save} disabled={!dirty || saving} data-testid="security-save">
          {saving ? "Salvez..." : dirty ? "Salvează" : "Salvat"}
        </AdminBtn>
      }
    >
      <div className="grid md:grid-cols-2 gap-4 text-sm">
        <ToggleRow
          icon={Bot} label="Blocare boți (User-Agent)"
          desc="Refuză curl, requests, headless browsers, scrapers."
          value={draft.bot_block_enabled}
          onChange={(v) => setDraft({ ...draft, bot_block_enabled: v })}
          testid="toggle-bot"
        />
        <ToggleRow
          icon={Lock} label="Blocare VPN/proxy (datacenter IPs)"
          desc="Heuristic AWS/GCP/Azure/DigitalOcean ranges + UA hints."
          value={draft.vpn_block_enabled}
          onChange={(v) => setDraft({ ...draft, vpn_block_enabled: v })}
          testid="toggle-vpn"
        />
        <ToggleRow
          icon={Globe} label="GEO-block (țări neacceptate)"
          desc="Folosește CF-IPCountry / X-Country header de la edge."
          value={draft.geo_block_enabled}
          onChange={(v) => setDraft({ ...draft, geo_block_enabled: v })}
          testid="toggle-geo"
        />
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3">
          <div className="flex items-center gap-2 mb-2 font-medium">
            <Globe className="w-4 h-4 text-blue-500" /> Țări permise
          </div>
          <input
            type="text"
            value={(draft.geo_allowed_countries || []).join(", ")}
            onChange={e => setDraft({ ...draft, geo_allowed_countries: e.target.value.split(",").map(s => s.trim()).filter(Boolean) })}
            placeholder="RO, MD, HU"
            className="w-full px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
            data-testid="security-countries"
          />
          <div className="text-[11px] text-slate-400 mt-1">Coduri ISO-3166 (2 litere). Separate prin virgulă.</div>
        </div>
        <NumRow label="Rate-limit IP / min" desc="Cereri max pe minut pe IP (endpoint-uri protejate)." value={draft.rate_limit_per_minute} onChange={(v) => setDraft({ ...draft, rate_limit_per_minute: v })} testid="num-ip-rl" />
        <NumRow label="Concierge mesaje / oră" desc="Max mesaje per user autenticat / oră." value={draft.concierge_msgs_per_hour} onChange={(v) => setDraft({ ...draft, concierge_msgs_per_hour: v })} testid="num-h" />
        <NumRow label="Concierge mesaje / zi" desc="Cap zilnic per user (anti-cost-scraping)." value={draft.concierge_msgs_per_day} onChange={(v) => setDraft({ ...draft, concierge_msgs_per_day: v })} testid="num-d" />
      </div>
      {cfg.updated_at && (
        <div className="mt-3 text-[11px] text-slate-400">
          Ultima modificare: {new Date(cfg.updated_at).toLocaleString("ro-RO")}
        </div>
      )}
    </AdminCard>
  );
};

const ToggleRow = ({ icon: Icon, label, desc, value, onChange, testid }) => (
  <button
    type="button"
    onClick={() => onChange(!value)}
    className={`text-left rounded-xl border p-3 transition-colors ${
      value ? "bg-emerald-50 border-emerald-300 dark:bg-emerald-500/10 dark:border-emerald-500/40" : "bg-slate-50 border-slate-200 dark:bg-slate-800/50 dark:border-slate-700"
    }`}
    data-testid={testid}
  >
    <div className="flex items-center gap-2 mb-1">
      <Icon className={`w-4 h-4 ${value ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400"}`} />
      <span className="font-medium">{label}</span>
      <span className={`ml-auto text-[10px] uppercase tracking-wider font-bold ${value ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400"}`}>
        {value ? "ON" : "OFF"}
      </span>
    </div>
    <div className="text-xs text-slate-500 dark:text-slate-400">{desc}</div>
  </button>
);

const NumRow = ({ label, desc, value, onChange, testid }) => (
  <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-3">
    <div className="font-medium mb-1">{label}</div>
    <div className="text-xs text-slate-500 dark:text-slate-400 mb-2">{desc}</div>
    <input
      type="number"
      min="1"
      value={value}
      onChange={e => onChange(Math.max(1, parseInt(e.target.value || "1", 10)))}
      className="w-full px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
      data-testid={testid}
    />
  </div>
);

const SecurityEventsCard = () => {
  const [data, setData] = useState({ items: [], by_kind_24h: {} });
  const [kind, setKind] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/security/events`, { params: { limit: 80, kind: kind || undefined } });
      setData(r.data);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [kind]);

  return (
    <AdminCard
      title={<div className="flex items-center gap-2"><Activity className="w-4 h-4 text-orange-500" /> Evenimente blocate (live)</div>}
      action={<AdminBtn variant="secondary" onClick={load}><RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Reîncarcă</AdminBtn>}
    >
      <div className="flex items-center gap-2 mb-3 flex-wrap text-xs">
        {["", ...Object.keys(KIND_LABELS)].map(k => (
          <button
            key={k || "all"}
            onClick={() => setKind(k)}
            className={`px-2.5 py-1 rounded-full font-medium border transition-colors ${
              kind === k
                ? "bg-blue-50 border-blue-300 text-blue-700 dark:bg-blue-500/20 dark:border-blue-500/50 dark:text-blue-300"
                : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"
            }`}
            data-testid={`sec-filter-${k || "all"}`}
          >
            {k ? KIND_LABELS[k].label : "Toate"} {k && data.by_kind_24h?.[k] ? `· ${data.by_kind_24h[k]}` : ""}
          </button>
        ))}
        <span className="ml-auto text-[11px] text-slate-400">
          Ultimele 24h: bot={data.by_kind_24h?.bot_blocked || 0} · vpn={data.by_kind_24h?.vpn_blocked || 0} · geo={data.by_kind_24h?.geo_blocked || 0} · rl={data.by_kind_24h?.rate_limit_ip || 0}
        </span>
      </div>
      {data.items.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm italic">Niciun eveniment înregistrat</div>
      ) : (
        <div className="overflow-x-auto" data-testid="security-events-list">
          <table className="w-full text-xs">
            <thead className="text-slate-500 uppercase tracking-wider">
              <tr><th className="text-left px-2 py-1.5">Tip</th><th className="text-left px-2 py-1.5">IP</th><th className="text-left px-2 py-1.5">Țară</th><th className="text-left px-2 py-1.5">User</th><th className="text-left px-2 py-1.5">Path</th><th className="text-left px-2 py-1.5">UA</th><th className="text-left px-2 py-1.5">Când</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {data.items.map((ev) => {
                const meta = KIND_LABELS[ev.kind] || { label: ev.kind, color: "text-slate-500" };
                return (
                  <tr key={ev._id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="px-2 py-1.5"><span className={`px-2 py-0.5 rounded-full border text-[10px] font-semibold ${meta.color}`}>{meta.label}</span></td>
                    <td className="px-2 py-1.5 font-mono">{ev.ip}</td>
                    <td className="px-2 py-1.5">{ev.country || "—"}</td>
                    <td className="px-2 py-1.5">{ev.user_email || "—"}</td>
                    <td className="px-2 py-1.5 font-mono truncate max-w-[140px]" title={ev.path}>{ev.path}</td>
                    <td className="px-2 py-1.5 truncate max-w-[180px]" title={ev.user_agent}>{(ev.user_agent || "—").slice(0, 30)}</td>
                    <td className="px-2 py-1.5 text-slate-400">{ev.created_at ? new Date(ev.created_at).toLocaleTimeString("ro-RO") : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </AdminCard>
  );
};

const ConciergeConversationsCard = () => {
  const [filter, setFilter] = useState("");
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [activeMessages, setActiveMessages] = useState([]);

  const load = async () => {
    const [convR, statR] = await Promise.all([
      axios.get(`${API}/admin/concierge/conversations`, { params: { filter: filter || undefined, limit: 60 } }),
      axios.get(`${API}/admin/concierge/stats`),
    ]);
    setItems(convR.data?.items || []);
    setStats(statR.data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter]);

  const openSession = async (sid) => {
    setActiveSession(sid);
    const r = await axios.get(`${API}/admin/concierge/conversations/${sid}`);
    setActiveMessages(r.data?.messages || []);
  };

  return (
    <AdminCard
      title={<div className="flex items-center gap-2"><MessageSquare className="w-4 h-4 text-blue-500" /> Conversații Concierge</div>}
      action={<AdminBtn variant="secondary" onClick={load}><RefreshCw className="w-3.5 h-3.5" /> Reîncarcă</AdminBtn>}
    >
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
          <Stat label="Total mesaje (30z)" value={stats.total_messages} />
          <Stat label="Escaladate" value={`${stats.escalated_count} (${stats.escalation_rate_pct}%)`} accent="amber" />
          <Stat label="Blocate" value={`${stats.blocked_count} (${stats.block_rate_pct}%)`} accent="red" />
          <Stat label="Client msg" value={stats.by_role?.client?.messages || 0} />
          <Stat label="Specialist msg" value={stats.by_role?.specialist?.messages || 0} />
        </div>
      )}
      <div className="flex items-center gap-2 mb-3 text-xs">
        {[
          { id: "", label: "Toate" },
          { id: "escalated", label: "Escaladate" },
          { id: "blocked", label: "Blocate" },
        ].map(f => (
          <button
            key={f.id || "all"}
            onClick={() => setFilter(f.id)}
            className={`px-2.5 py-1 rounded-full font-medium border ${
              filter === f.id
                ? "bg-blue-50 border-blue-300 text-blue-700 dark:bg-blue-500/20 dark:border-blue-500/50 dark:text-blue-300"
                : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"
            }`}
            data-testid={`conv-filter-${f.id || "all"}`}
          >{f.label}</button>
        ))}
      </div>
      {items.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm italic">Nicio conversație</div>
      ) : (
        <div className="space-y-1.5 max-h-[400px] overflow-y-auto" data-testid="conversations-list">
          {items.map(c => (
            <button
              key={c.session_id}
              onClick={() => openSession(c.session_id)}
              className="w-full text-left p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 flex items-center gap-2 text-xs"
              data-testid={`conv-${c.session_id}`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium truncate text-slate-700 dark:text-slate-200">{c.first_message}</span>
                  {c.blocked && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300">BLOCAT</span>}
                  {c.escalated && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300">ESCALAT</span>}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">{c.user_role} · {c.message_count} mesaje · {c.last_message_at ? new Date(c.last_message_at).toLocaleString("ro-RO") : ""}</div>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            </button>
          ))}
        </div>
      )}

      {activeSession && (
        <div className="fixed inset-0 z-[70] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setActiveSession(null)}>
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-2xl w-full max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()} data-testid="conv-detail-modal">
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 dark:border-slate-700">
              <div className="font-semibold">Conversație · {activeSession.slice(-10)}</div>
              <button onClick={() => setActiveSession(null)} className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800"><X className="w-4 h-4" /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {activeMessages.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[80%] px-3 py-2 rounded-2xl text-sm whitespace-pre-wrap ${
                    m.role === "user" ? "bg-blue-500 text-white" :
                    m.blocked ? "bg-red-50 dark:bg-red-500/15 text-red-700 dark:text-red-300 border border-red-200" :
                    m.escalated ? "bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-200" :
                    "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200"
                  }`}>
                    {m.content}
                    {m.block_reason && <div className="text-[10px] mt-1 opacity-75">Motiv: {m.block_reason}</div>}
                    {m.escalation_trigger && <div className="text-[10px] mt-1 opacity-75">Trigger: {m.escalation_trigger}</div>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </AdminCard>
  );
};

const Stat = ({ label, value, accent }) => {
  const colors = {
    amber: "text-amber-600 dark:text-amber-400",
    red: "text-red-600 dark:text-red-400",
  };
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-2.5">
      <div className={`text-2xl font-semibold ${accent ? colors[accent] : "text-slate-900 dark:text-slate-100"}`}>{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-slate-400 mt-0.5">{label}</div>
    </div>
  );
};

const ConciergeSettingsCard = () => {
  const [s, setS] = useState(null);
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    axios.get(`${API}/admin/concierge/settings`).then(r => { setS(r.data); setDraft(r.data); }).catch(() => {});
  }, []);

  if (!s || !draft) return null;
  const dirty = JSON.stringify(s) !== JSON.stringify(draft);
  const save = async () => {
    setSaving(true);
    try {
      const r = await axios.put(`${API}/admin/concierge/settings`, draft);
      setS(r.data); setDraft(r.data);
    } catch (e) {
      window.alert(`Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally { setSaving(false); }
  };

  const toggleRole = (role) => {
    const enabled = draft.enabled_roles.includes(role);
    setDraft({ ...draft, enabled_roles: enabled ? draft.enabled_roles.filter(r => r !== role) : [...draft.enabled_roles, role] });
  };

  return (
    <AdminCard
      title={<div className="flex items-center gap-2"><Bot className="w-4 h-4 text-purple-500" /> Setări Concierge</div>}
      action={<AdminBtn variant={dirty ? "primary" : "secondary"} onClick={save} disabled={!dirty || saving} data-testid="concierge-settings-save">{saving ? "..." : dirty ? "Salvează" : "Salvat"}</AdminBtn>}
    >
      <div className="space-y-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-500 mb-2">Roluri activate</div>
          <div className="flex gap-2 flex-wrap">
            {["client", "specialist", "operator"].map(r => (
              <button
                key={r}
                onClick={() => toggleRole(r)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                  draft.enabled_roles.includes(r)
                    ? "bg-emerald-50 border-emerald-300 text-emerald-700 dark:bg-emerald-500/15 dark:border-emerald-500/40 dark:text-emerald-300"
                    : "bg-slate-50 border-slate-200 text-slate-500 dark:bg-slate-800 dark:border-slate-700"
                }`}
                data-testid={`role-toggle-${r}`}
              >
                {draft.enabled_roles.includes(r) ? "✓" : "○"} {r}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-500 mb-2">Email suport (pentru escaladare)</div>
          <input
            type="email"
            value={draft.support_email}
            onChange={e => setDraft({ ...draft, support_email: e.target.value })}
            className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
            data-testid="concierge-support-email"
          />
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-2">
            <TriangleAlert className="w-3 h-3 text-amber-500" /> Trigger-e escalare (1 per linie)
          </div>
          <textarea
            rows={5}
            value={(draft.escalation_triggers || []).join("\n")}
            onChange={e => setDraft({ ...draft, escalation_triggers: e.target.value.split("\n").map(s => s.trim()).filter(Boolean) })}
            className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm font-mono"
            data-testid="concierge-triggers"
          />
        </div>
      </div>
    </AdminCard>
  );
};

export const AdminConciergePanel = () => {
  return (
    <div className="space-y-4" data-testid="admin-concierge-panel">
      <SecurityConfigCard />
      <SecurityEventsCard />
      <ConciergeConversationsCard />
      <ConciergeSettingsCard />
    </div>
  );
};

export default AdminConciergePanel;
