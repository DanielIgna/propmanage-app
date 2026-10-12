// /admin/scheduler — joburile programate (cron): profil full/lite, adăugare / editare / ștergere,
// pornire/oprire per job, rulare manuală. Admin only. Refresh la 60s.
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  AlertTriangle, ArrowLeft, CheckCircle2, Clock, Loader2, Pencil, Play, Plus, RefreshCw, RotateCcw, Square, Timer, Trash2, X, XCircle,
} from "lucide-react";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/admin/scheduler`;

const CATEGORIES = {
  all: "Toate",
  business: "Business",
  monitoring: "Monitorizare",
  ai: "AI / Intelligence",
  reports: "Rapoarte",
  other: "Altele",
};

const CRON_PRESETS = [
  ["*/15 * * * *", "la 15 min"],
  ["0 * * * *", "orar"],
  ["0 9 * * *", "zilnic 09:00"],
  ["0 9 * * 1-5", "L–V 09:00"],
  ["0 9 * * mon", "luni 09:00"],
  ["30 3 * * sun", "duminică 03:30"],
];

const fmt = (iso) => (iso ? new Date(iso).toLocaleString("ro-RO", { dateStyle: "short", timeStyle: "short" }) : "—");
const errMsg = (e) => e?.response?.data?.detail || e.message;

const Toggle = ({ on, onChange, disabled, testId }) => (
  <button
    type="button"
    onClick={onChange}
    disabled={disabled}
    data-testid={testId}
    aria-pressed={on}
    className={`relative w-10 h-5 shrink-0 rounded-full transition-colors disabled:opacity-40 ${on ? "bg-[#d4ff3a]" : "bg-white/15"}`}
  >
    <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-stone-950 transition-all ${on ? "left-5" : "left-0.5"}`} />
  </button>
);

const LastRun = ({ h }) => {
  if (!h?.last_run) return <span className="text-stone-600">—</span>;
  return (
    <span className="inline-flex items-center gap-1.5" title={h.error || ""}>
      {h.ok ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-red-400" />}
      <span className="text-stone-300">{fmt(h.last_run)}</span>
      {h.duration_ms != null && <span className="text-stone-500">· {h.duration_ms < 1000 ? `${h.duration_ms}ms` : `${(h.duration_ms / 1000).toFixed(1)}s`}</span>}
    </span>
  );
};

const Field = ({ label, hint, children }) => (
  <label className="block space-y-1.5">
    <span className="text-xs text-stone-400">{label}</span>
    {children}
    {hint && <span className="block text-[11px] text-stone-500">{hint}</span>}
  </label>
);

const inputCls = "w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-stone-600 focus:outline-none focus:border-[#d4ff3a]/60";

// mode "add": {task, label, category, cron, enabled}; mode "edit": job row
const JobModal = ({ mode, job, tasks, onClose, onSaved }) => {
  const isAdd = mode === "add";
  const [form, setForm] = useState(() => isAdd
    ? { task: tasks[0]?.id || "", label: "", category: "", cron: "0 9 * * *", enabled: true }
    : { label: job.label, category: job.category, cron: job.cron, enabled: job.enabled });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState(null);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e?.target ? e.target.value : e }));

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setErr(null);
    try {
      const r = isAdd
        ? await axios.post(`${API}/jobs`, { ...form, category: form.category || null })
        : await axios.put(`${API}/jobs/${job.id}`, form);
      onSaved(r.data);
    } catch (e2) {
      setErr(errMsg(e2));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose} data-testid="scheduler-modal">
      <form
        onSubmit={submit}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg rounded-2xl border border-white/10 bg-stone-900 p-5 space-y-4 max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-xl">{isAdd ? "Adaugă job" : "Editează job"}</h2>
          <button type="button" onClick={onClose} className="p-1 rounded-md hover:bg-white/10 text-stone-400"><X className="w-4 h-4" /></button>
        </div>
        {!isAdd && <p className="text-xs text-stone-500 font-mono -mt-2">{job.id}{job.custom ? ` · sarcina ${job.task}` : ""}</p>}

        {isAdd && (
          <Field label="Sarcină" hint="Ce rulează jobul — una dintre sarcinile existente din backend.">
            <select value={form.task} onChange={set("task")} className={inputCls} data-testid="scheduler-form-task">
              {tasks.map((t) => <option key={t.id} value={t.id} className="bg-stone-900">{t.label} ({t.id})</option>)}
            </select>
          </Field>
        )}

        <Field label="Nume">
          <input value={form.label} onChange={set("label")} required={isAdd} placeholder="ex: Digest luni dimineață" className={inputCls} data-testid="scheduler-form-label" />
        </Field>

        <Field label="Categorie">
          <select value={form.category} onChange={set("category")} className={inputCls} data-testid="scheduler-form-category">
            {isAdd && <option value="" className="bg-stone-900">Implicit (după sarcină)</option>}
            {Object.entries(CATEGORIES).filter(([k]) => k !== "all").map(([k, l]) => <option key={k} value={k} className="bg-stone-900">{l}</option>)}
          </select>
        </Field>

        <Field
          label="Program (cron)"
          hint={`minut oră zi lună zi_săptămână · ora României · zile: 0/7=dum, 1=lun… sau mon-sun${!isAdd && !job.custom ? " · gol = programul implicit" : ""}`}
        >
          <input value={form.cron} onChange={set("cron")} required={isAdd} placeholder="0 9 * * *" className={`${inputCls} font-mono`} data-testid="scheduler-form-cron" />
          <div className="flex flex-wrap gap-1.5 pt-1">
            {CRON_PRESETS.map(([c, l]) => (
              <button key={c} type="button" onClick={() => set("cron")(c)} className={`px-2 py-0.5 rounded-full text-[11px] border ${form.cron === c ? "border-[#d4ff3a]/60 text-[#d4ff3a]" : "border-white/10 text-stone-400 hover:bg-white/5"}`}>
                {l}
              </button>
            ))}
          </div>
        </Field>

        <div className="flex items-center justify-between">
          <span className="text-sm text-stone-300">Activ</span>
          <Toggle on={form.enabled} onChange={() => setForm((f) => ({ ...f, enabled: !f.enabled }))} testId="scheduler-form-enabled" />
        </div>

        {err && <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2" data-testid="scheduler-form-error">{err}</div>}

        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-full text-sm border border-white/10 hover:bg-white/5">Anulează</button>
          <button type="submit" disabled={saving} className="px-4 py-2 rounded-full text-sm bg-[#d4ff3a] text-stone-950 font-medium disabled:opacity-50" data-testid="scheduler-form-save">
            {saving ? "Se salvează…" : isAdd ? "Adaugă" : "Salvează"}
          </button>
        </div>
      </form>
    </div>
  );
};

export const SchedulerJobsPage = () => {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(null);
  const [cat, setCat] = useState("all");
  const [modal, setModal] = useState(null); // {mode: "add"} | {mode: "edit", job}

  const load = async () => {
    try {
      const r = await axios.get(`${API}/jobs`);
      setData(r.data);
      setErr(null);
    } catch (e) {
      setErr(errMsg(e));
    }
  };

  const anyRunning = !!data?.jobs?.some((j) => j.is_running);
  useEffect(() => {
    load();
  }, []);
  useEffect(() => {  // 3s while something runs, otherwise 60s
    const t = setInterval(load, anyRunning ? 3000 : 60000);
    return () => clearInterval(t);
  }, [anyRunning]);

  const act = async (key, fn) => {
    setBusy(key);
    try {
      const r = await fn();
      if (r?.data?.jobs) setData(r.data);
    } catch (e) {
      alert("Eroare: " + errMsg(e));
    } finally {
      setBusy(null);
    }
  };

  const setProfile = (profile) => {
    const reset = data?.overrides > 0 && window.confirm(`Resetez și cele ${data.overrides} joburi editate manual?`);
    act("profile", () => axios.post(`${API}/profile`, { profile, reset_overrides: reset }));
  };
  const toggle = (job) => act(job.id, () => axios.post(`${API}/jobs/${job.id}/toggle`, { enabled: !job.enabled }));
  const remove = (job) => {
    const msg = job.custom
      ? `Șterg definitiv jobul „${job.label}”?`
      : `Șterg jobul „${job.label}”? E un job din cod: nu mai rulează și apare la „Șterse”, de unde îl poți restaura.`;
    if (window.confirm(msg)) act(`del:${job.id}`, () => axios.delete(`${API}/jobs/${job.id}`));
  };
  const restore = (job) => act(`res:${job.id}`, () => axios.post(`${API}/jobs/${job.id}/restore`));
  const runNow = (job) => {
    if (!window.confirm(`Rulez acum „${job.label}”? Poate citi multe date din baza de date.`)) return;
    act(`run:${job.id}`, () => axios.post(`${API}/jobs/${job.id}/run`));
  };
  const stopRun = (job) => {
    if (window.confirm(`Opresc „${job.label}”? Ce a apucat să facă rămâne făcut.`)) act(`stop:${job.id}`, () => axios.post(`${API}/jobs/${job.id}/stop`));
  };

  const jobs = useMemo(() => (data?.jobs || []).filter((j) => cat === "all" || j.category === cat), [data, cat]);
  const counts = useMemo(() => {
    const c = { all: data?.jobs?.length || 0 };
    (data?.jobs || []).forEach((j) => { c[j.category] = (c[j.category] || 0) + 1; });
    return c;
  }, [data]);

  if (err && !data) return <div className="min-h-screen bg-stone-950 text-red-300 p-8" data-testid="scheduler-error">Eroare: {err}</div>;
  if (!data) return <div className="min-h-screen bg-stone-950 text-stone-400 flex items-center justify-center" data-testid="scheduler-loading">Se încarcă…</div>;

  const iconBtn = "p-1.5 rounded-md hover:bg-white/10 text-stone-400 hover:text-white disabled:opacity-40";

  return (
    <div className="min-h-screen bg-stone-950 text-white p-4 sm:p-6 lg:p-10" data-testid="admin-scheduler-page">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <Link to="/admin" className="inline-flex items-center gap-2 text-xs text-stone-500 hover:text-white mb-2">
              <ArrowLeft className="w-3 h-3" /> Admin Dashboard
            </Link>
            <h1 className="font-serif text-3xl flex items-center gap-3">
              <Timer className="w-7 h-7 text-[#d4ff3a]" /> Joburi programate
            </h1>
            <p className="text-stone-500 text-sm mt-1" data-testid="scheduler-summary">
              {data.active} active din {data.total} · fiecare job care scanează tabele consumă egress din baza de date
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setModal({ mode: "add" })} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#d4ff3a] text-stone-950 font-medium text-xs" data-testid="scheduler-add">
              <Plus className="w-3.5 h-3.5" /> Adaugă job
            </button>
            <button onClick={load} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-xs" data-testid="scheduler-refresh">
              <RefreshCw className="w-3 h-3" /> Refresh
            </button>
          </div>
        </div>

        {!data.running && (
          <div className="flex items-start gap-3 p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-200 text-sm" data-testid="scheduler-not-running">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>Scheduler-ul nu rulează pe acest server{data.enabled_here ? "" : " (local — pornește doar pe Railway sau cu SCHEDULER_ENABLED=true)"}. Modificările se salvează și se aplică la următoarea pornire.</span>
          </div>
        )}

        <div className="grid sm:grid-cols-2 gap-3">
          {[
            { id: "lite", title: "Lite", desc: "Doar joburile esențiale (e-mailuri, remindere, plăți, backup săptămânal). Recomandat la trafic mic." },
            { id: "full", title: "Full", desc: "Toate joburile pe programul original, inclusiv monitorizare, AI și rapoarte." },
          ].map((p) => (
            <button
              key={p.id}
              onClick={() => data.profile !== p.id && setProfile(p.id)}
              disabled={busy === "profile"}
              data-testid={`scheduler-profile-${p.id}`}
              className={`text-left p-4 rounded-xl border transition-colors ${data.profile === p.id ? "border-[#d4ff3a]/60 bg-[#d4ff3a]/10" : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06]"}`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{p.title}</span>
                {data.profile === p.id && <span className="text-[10px] uppercase tracking-wider text-[#d4ff3a]">activ</span>}
              </div>
              <p className="text-xs text-stone-400 mt-1">{p.desc}</p>
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {Object.entries(CATEGORIES).filter(([k]) => counts[k]).map(([k, label]) => (
            <button
              key={k}
              onClick={() => setCat(k)}
              data-testid={`scheduler-cat-${k}`}
              className={`px-3 py-1 rounded-full text-xs border ${cat === k ? "bg-white text-stone-950 border-white" : "border-white/10 text-stone-300 hover:bg-white/5"}`}
            >
              {label} <span className="opacity-60">{counts[k]}</span>
            </button>
          ))}
          {data.overrides > 0 && (
            <button
              onClick={() => window.confirm("Anulez editările manuale și revin la profil? (joburile adăugate și cele șterse rămân)") && act("profile", () => axios.post(`${API}/profile`, { profile: data.profile, reset_overrides: true }))}
              className="ml-auto inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs border border-white/10 text-stone-300 hover:bg-white/5"
              data-testid="scheduler-reset-overrides"
            >
              <RotateCcw className="w-3 h-3" /> {data.overrides} editate manual · resetează
            </button>
          )}
        </div>

        <div className="rounded-xl border border-white/10 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[720px]">
              <thead className="bg-white/[0.03] text-stone-400 text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left font-medium px-4 py-2.5">Job</th>
                  <th className="text-left font-medium px-4 py-2.5">Program</th>
                  <th className="text-left font-medium px-4 py-2.5">Următoarea</th>
                  <th className="text-left font-medium px-4 py-2.5">Ultima rulare</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {jobs.map((j) => (
                  <tr key={j.id} className={j.enabled ? "" : "opacity-60"} data-testid={`scheduler-job-${j.id}`}>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-white">{j.label}</span>
                        {j.essential && <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300">esențial</span>}
                        {j.custom && <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300">adăugat</span>}
                        {j.edited && <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/15 text-sky-300">editat</span>}
                      </div>
                      <div className="text-xs text-stone-500 font-mono">{j.custom ? `${j.task} · ` : `${j.id} · `}{CATEGORIES[j.category] || j.category}</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-stone-300">
                      <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3 text-stone-500" />{j.schedule}</span>
                      {j.original_schedule && j.original_schedule !== j.schedule && <div className="text-stone-500">implicit: {j.original_schedule}</div>}
                    </td>
                    <td className="px-4 py-3 text-xs text-stone-300">{j.enabled ? fmt(j.next_run) : <span className="text-stone-500">oprit</span>}</td>
                    <td className="px-4 py-3 text-xs">
                      {j.is_running
                        ? <span className="inline-flex items-center gap-1.5 text-[#d4ff3a]"><Loader2 className="w-3.5 h-3.5 animate-spin" /> rulează…</span>
                        : <LastRun h={j.history} />}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        {j.is_running ? (
                          <button onClick={() => stopRun(j)} disabled={!!busy} title="Oprește rularea" className="p-1.5 rounded-md bg-red-500/15 text-red-300 hover:bg-red-500/25 disabled:opacity-40" data-testid={`scheduler-stop-${j.id}`}>
                            <Square className="w-3.5 h-3.5 fill-current" />
                          </button>
                        ) : (
                          <button onClick={() => runNow(j)} disabled={!!busy} title="Rulează acum" className={iconBtn} data-testid={`scheduler-run-${j.id}`}>
                            <Play className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button onClick={() => setModal({ mode: "edit", job: j })} disabled={!!busy} title="Editează" className={iconBtn} data-testid={`scheduler-edit-${j.id}`}>
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => remove(j)} disabled={!!busy} title="Șterge" className={`${iconBtn} hover:text-red-300`} data-testid={`scheduler-delete-${j.id}`}>
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                        <span className="w-2" />
                        <Toggle on={j.enabled} onChange={() => toggle(j)} disabled={!!busy} testId={`scheduler-toggle-${j.id}`} />
                      </div>
                    </td>
                  </tr>
                ))}
                {!jobs.length && (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-stone-500 text-sm">Niciun job în această categorie.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {data.deleted?.length > 0 && (
          <div className="rounded-xl border border-white/10 p-4 space-y-2" data-testid="scheduler-deleted">
            <h2 className="text-sm text-stone-300">Șterse <span className="text-stone-500">{data.deleted.length}</span></h2>
            <div className="divide-y divide-white/5">
              {data.deleted.map((j) => (
                <div key={j.id} className="flex items-center justify-between gap-3 py-2">
                  <div className="min-w-0">
                    <div className="text-sm text-stone-300 truncate">{j.label}</div>
                    <div className="text-xs text-stone-500 font-mono truncate">{j.id}</div>
                  </div>
                  <button onClick={() => restore(j)} disabled={!!busy} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs border border-white/10 text-stone-300 hover:bg-white/5 shrink-0" data-testid={`scheduler-restore-${j.id}`}>
                    <RotateCcw className="w-3 h-3" /> Restaurează
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <p className="text-xs text-stone-600">Istoricul rulărilor e ținut în memorie și se resetează la repornirea serverului.</p>
      </div>

      {modal && (
        <JobModal
          mode={modal.mode}
          job={modal.job}
          tasks={data.tasks || []}
          onClose={() => setModal(null)}
          onSaved={(d) => { setData(d); setModal(null); }}
        />
      )}
    </div>
  );
};

export default SchedulerJobsPage;
