// WeeklyBriefingControl — small config widget for the Weekly AI Briefing email.
// Toggle on/off, edit recipients, "Trimite acum" preview, view last sent.
import React, { useState, useEffect } from "react";
import axios from "axios";
import { Mail, Loader2, Send, Power, Plus, X, AlertTriangle, CheckCircle2 } from "lucide-react";
import { AdminCard } from "./AdminLayoutMetronic";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

export const WeeklyBriefingControl = () => {
  const [config, setConfig] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [lastSent, setLastSent] = useState(null);
  const [newEmail, setNewEmail] = useState("");

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, h] = await Promise.all([
        ax.get("/api/admin/ai-weekly-briefing/config"),
        ax.get("/api/admin/ai-weekly-briefing/history", { params: { limit: 3 } }),
      ]);
      setConfig(c.data);
      setHistory(h.data.items || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la încărcare");
    } finally { setLoading(false); }
  };

  useEffect(() => { loadAll(); }, []);

  const updateConfig = async (patch) => {
    setSaving(true);
    setError(null);
    try {
      const { data } = await ax.put("/api/admin/ai-weekly-briefing/config", patch);
      setConfig(data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la salvare");
    } finally { setSaving(false); }
  };

  const addRecipient = async () => {
    const e = newEmail.trim();
    if (!e || !e.includes("@")) return;
    const next = Array.from(new Set([...(config?.recipients || []), e]));
    await updateConfig({ recipients: next });
    setNewEmail("");
  };

  const removeRecipient = async (email) => {
    const next = (config?.recipients || []).filter(r => r !== email);
    await updateConfig({ recipients: next });
  };

  const sendNow = async () => {
    if (!window.confirm("Trimit briefing-ul AI ACUM către destinatarii configurați?")) return;
    setSending(true);
    setError(null);
    setLastSent(null);
    try {
      const { data } = await ax.post("/api/admin/ai-weekly-briefing/send-now", {});
      setLastSent(data);
      loadAll();
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la trimitere");
    } finally { setSending(false); }
  };

  return (
    <AdminCard testid="weekly-briefing-control">
      <div className="flex items-start gap-4 flex-wrap">
        <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/30 flex items-center justify-center shrink-0">
          <Mail className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div className="flex-1 min-w-[280px]">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-base">Weekly AI Briefing</h3>
            {config?.enabled ? (
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300 border border-emerald-300/40" data-testid="briefing-status">
                Activ · luni 09:00
              </span>
            ) : (
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-400 border border-slate-200 dark:border-white/10" data-testid="briefing-status">
                Dezactivat
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Email automat lunea dimineața · Claude Sonnet rezumă activitatea AI a săptămânii (auto-match, findings, autonomy delta).
          </p>

          {loading ? (
            <div className="mt-3 flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin" /> Se încarcă...
            </div>
          ) : (
            <>
              {/* Recipients */}
              <div className="mt-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Destinatari ({config?.recipients?.length || 0})</div>
                <div className="flex flex-wrap gap-1.5 mb-2" data-testid="briefing-recipients-list">
                  {(config?.recipients || []).map(r => (
                    <span key={r} className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-xs">
                      {r}
                      <button onClick={() => removeRecipient(r)} className="text-slate-400 hover:text-red-500" data-testid={`briefing-remove-${r}`}>
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                  {(!config?.recipients || config.recipients.length === 0) && (
                    <span className="text-xs text-slate-400 italic">Niciun destinatar — adaugă unul mai jos</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <input
                    type="email"
                    value={newEmail}
                    onChange={e => setNewEmail(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && addRecipient()}
                    placeholder="adresa@email.ro"
                    disabled={saving}
                    className="flex-1 text-xs bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-400"
                    data-testid="briefing-new-email"
                  />
                  <button
                    onClick={addRecipient}
                    disabled={saving || !newEmail.includes("@")}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs bg-indigo-500 hover:bg-indigo-600 text-white disabled:opacity-50"
                    data-testid="briefing-add-email"
                  >
                    <Plus className="w-3.5 h-3.5" /> Adaugă
                  </button>
                </div>
              </div>

              {/* Last sent */}
              {history.length > 0 && (
                <div className="mt-3 text-[11px] text-slate-500 dark:text-slate-400 font-mono" data-testid="briefing-last-sent">
                  Ultima trimitere: {new Date(history[0].sent_at).toLocaleString("ro-RO")}
                  {history[0].ok
                    ? <span className="text-emerald-600 dark:text-emerald-400 ml-1">✓ OK</span>
                    : <span className="text-red-500 ml-1">✗ {history[0].error || "fail"}</span>}
                  {" · "}
                  {history[0].forced ? "manual" : "cron"}
                </div>
              )}

              {lastSent && (
                <div className={`mt-3 rounded-xl border px-3 py-2.5 ${
                  lastSent.ok
                    ? "border-emerald-200 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-500/10"
                    : "border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-500/10"
                }`} data-testid="briefing-last-result">
                  <div className={`text-sm flex items-center gap-2 ${
                    lastSent.ok ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300"
                  }`}>
                    {lastSent.ok ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                    {lastSent.ok ? `Trimis către ${lastSent.recipients?.length} destinatari` : `Eșec: ${lastSent.error || "necunoscut"}`}
                  </div>
                  {lastSent.summary_text && (
                    <div className="text-xs text-slate-600 dark:text-slate-300 mt-2 italic max-h-32 overflow-y-auto whitespace-pre-wrap">
                      {lastSent.summary_text.slice(0, 400)}{lastSent.summary_text.length > 400 ? "..." : ""}
                    </div>
                  )}
                </div>
              )}

              {error && (
                <div className="mt-3 text-xs text-red-600 dark:text-red-400 flex items-center gap-2">
                  <AlertTriangle className="w-3.5 h-3.5" /> {error}
                </div>
              )}
            </>
          )}
        </div>

        <div className="flex flex-col gap-2 shrink-0">
          <button
            onClick={sendNow}
            disabled={sending || loading || !(config?.recipients?.length)}
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold bg-indigo-500 hover:bg-indigo-600 text-white shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            data-testid="briefing-send-now"
          >
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Trimite acum
          </button>
          <button
            onClick={() => updateConfig({ enabled: !config?.enabled })}
            disabled={saving || loading}
            className={`inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-colors ${
              config?.enabled
                ? "bg-red-50 hover:bg-red-100 text-red-700 dark:bg-red-500/10 dark:hover:bg-red-500/20 dark:text-red-300 border border-red-200 dark:border-red-500/30"
                : "bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:hover:bg-emerald-500/20 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/30"
            }`}
            data-testid="briefing-toggle"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Power className="w-3.5 h-3.5" />}
            {config?.enabled ? "Dezactivează" : "Activează"}
          </button>
        </div>
      </div>
    </AdminCard>
  );
};

export default WeeklyBriefingControl;
