// House Health — Recommendations section (F4.2 + F4.4 publish-to-marketplace).
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Plus, Trash2 } from "lucide-react";
import { API } from "../DashShared";
import { PRIORITY_META, CATEGORY_LABELS, fmtDate } from "./constants";

const EMPTY_FORM = {
  evaluation_id: "", title: "", description: "",
  priority: "recommended", category: "other",
  estimated_cost_eur: "", deadline: "",
};

export const RecommendationsSection = ({ twinId }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [evaluations, setEvaluations] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");

  const load = async () => {
    if (!twinId) return;
    setLoading(true);
    try {
      const r = await axios.get(`${API}/house-health/recommendations`, { params: { twin_project_id: twinId } });
      setItems(r.data?.items || []);
    } finally { setLoading(false); }
  };

  useEffect(() => {
    axios.get(`${API}/auth/me`).then((r) => setUser(r.data)).catch(() => {});
    load();
    axios.get(`${API}/house-health/evaluations`, { params: { twin_project_id: twinId, status: "approved" } })
      .then((r) => setEvaluations(r.data?.items || []))
      .catch(() => {});
  }, [twinId]); // eslint-disable-line react-hooks/exhaustive-deps

  const canAdd = user?.role === "specialist" || user?.role === "admin";

  const submit = async () => {
    setError("");
    if (!form.evaluation_id) { setError("Selectează evaluarea aprobată."); return; }
    if (!form.title.trim()) { setError("Titlul e obligatoriu."); return; }
    try {
      await axios.post(`${API}/house-health/recommendations`, {
        ...form,
        estimated_cost_eur: form.estimated_cost_eur ? parseFloat(form.estimated_cost_eur) : null,
      });
      setShowForm(false);
      setForm(EMPTY_FORM);
      await load();
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare salvare");
    }
  };

  const updateStatus = async (id, status) => {
    await axios.patch(`${API}/house-health/recommendations/${id}`, { status });
    await load();
  };

  const remove = async (id) => {
    if (!window.confirm("Ștergi această recomandare?")) return;
    await axios.delete(`${API}/house-health/recommendations/${id}`);
    await load();
  };

  const publish = async (rec) => {
    if (!window.confirm(`Publici această recomandare ca cerere în marketplace?\n\nSpecialiștii din zona ta vor putea face oferte. Comisionul platformei: ${rec.marketplace_commission_pct || "10"}% din fee-ul lead-ului.`)) return;
    try {
      const r = await axios.post(`${API}/house-health/recommendations/${rec.id}/publish-to-marketplace`, {
        budget_estimate: rec.estimated_cost_eur,
      });
      // eslint-disable-next-line no-alert
      alert(`Publicat în marketplace! Request ID: ${r.data.request_id}. Comision: ${r.data.commission_pct}%.`);
      await load();
    } catch (e) {
      // eslint-disable-next-line no-alert
      alert(e?.response?.data?.detail || "Eroare la publicare.");
    }
  };

  return (
    <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-5" data-testid="hh-recommendations-section">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-bold">Recomandări</h2>
        {canAdd && (
          <button
            onClick={() => setShowForm(!showForm)}
            data-testid="hh-rec-new"
            className="text-xs px-2.5 py-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 text-white font-semibold inline-flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> {showForm ? "Anulează" : "Recomandare nouă"}
          </button>
        )}
      </div>

      {showForm && canAdd && (
        <RecommendationForm
          form={form}
          setForm={setForm}
          evaluations={evaluations}
          error={error}
          onSubmit={submit}
        />
      )}

      <PriorityLegend />

      {loading && <div className="text-xs text-stone-500">Se încarcă...</div>}
      {!loading && items.length === 0 && (
        <div className="text-xs text-stone-500 italic" data-testid="hh-rec-empty">
          Nicio recomandare încă. {canAdd ? "Adaugă prima după o evaluare aprobată." : "Specialistul va adăuga recomandări după evaluări."}
        </div>
      )}

      <ul className="space-y-2" data-testid="hh-rec-list">
        {items.map((r, i) => (
          <RecommendationCard
            key={r.id}
            rec={r}
            index={i}
            user={user}
            canAdd={canAdd}
            onPublish={() => publish(r)}
            onDone={() => updateStatus(r.id, "done")}
            onDelete={() => remove(r.id)}
          />
        ))}
      </ul>
    </div>
  );
};

const PriorityLegend = () => (
  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs mb-3">
    {Object.entries(PRIORITY_META).map(([k, m]) => (
      <div key={k} className={`px-3 py-2 rounded-lg border ${m.cls}`}>
        <div className="font-bold uppercase tracking-wider mb-0.5">{m.icon} {m.label}</div>
        <div className="text-stone-400 text-[11px]">
          {k === "urgent" ? "Lucrări critice — necesar imediat." :
           k === "recommended" ? "Intervenții preventive recomandate." :
           "Atenție în viitor, nu acum."}
        </div>
      </div>
    ))}
  </div>
);

const RecommendationForm = ({ form, setForm, evaluations, error, onSubmit }) => {
  const set = (k, v) => setForm({ ...form, [k]: v });
  return (
    <div className="p-3 rounded-xl border border-emerald-500/30 bg-emerald-500/5 space-y-2 mb-3" data-testid="hh-rec-form">
      <select value={form.evaluation_id} onChange={(e) => set("evaluation_id", e.target.value)}
        className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-rec-eval">
        <option value="">— alege evaluarea aprobată —</option>
        {evaluations.map((ev) => (
          <option key={ev.id} value={ev.id}>{fmtDate(ev.date)} · {ev.kind}</option>
        ))}
      </select>
      <input value={form.title} onChange={(e) => set("title", e.target.value)} placeholder="Titlu recomandare"
        className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-rec-title" />
      <textarea value={form.description} onChange={(e) => set("description", e.target.value)} placeholder="Detalii..." rows={3}
        className="w-full bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-rec-desc" />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <select value={form.priority} onChange={(e) => set("priority", e.target.value)}
          className="bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-rec-priority">
          <option value="urgent">Urgent</option>
          <option value="recommended">Recomandat</option>
          <option value="monitor">Monitorizare</option>
        </select>
        <select value={form.category} onChange={(e) => set("category", e.target.value)}
          className="bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-rec-category">
          {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input type="number" step="1" min="0" placeholder="Cost € (opt)" value={form.estimated_cost_eur}
          onChange={(e) => set("estimated_cost_eur", e.target.value)}
          className="bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-rec-cost" />
        <input type="date" value={form.deadline} onChange={(e) => set("deadline", e.target.value)}
          className="bg-stone-800 border border-stone-700 rounded px-2 py-1.5 text-sm" data-testid="hh-rec-deadline" />
      </div>
      {error && <div className="text-xs text-rose-400">{error}</div>}
      <button onClick={onSubmit} data-testid="hh-rec-save"
        className="px-3 py-1.5 rounded-lg bg-emerald-500 text-stone-950 text-xs font-bold inline-flex items-center gap-1.5">
        <Plus className="w-3.5 h-3.5" /> Salvează
      </button>
    </div>
  );
};

const RecommendationCard = ({ rec, index: i, user, canAdd, onPublish, onDone, onDelete }) => {
  const m = PRIORITY_META[rec.priority] || PRIORITY_META.monitor;
  const borderCls = m.cls.replace("text-", "border-").split(" ").filter(c => c.startsWith("border-")).join(" ");
  const canEdit = (canAdd && rec.specialist_id === user?.id) || user?.role === "admin";
  return (
    <li className={`p-3 rounded-lg border ${borderCls} bg-stone-800/40`} data-testid={`hh-rec-${i}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded font-bold ${m.cls}`}>{m.icon} {m.label}</span>
            <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-stone-700 text-stone-300">{CATEGORY_LABELS[rec.category] || rec.category}</span>
            {rec.status === "done" && <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400">✓ Done</span>}
            {rec.status === "dismissed" && <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-stone-700 text-stone-400">Anulat</span>}
          </div>
          <div className="text-sm font-semibold text-stone-100">{rec.title}</div>
          {rec.description && <div className="text-xs text-stone-400 mt-1 whitespace-pre-wrap">{rec.description}</div>}
          <div className="flex gap-3 flex-wrap text-[11px] text-stone-500 mt-1">
            {rec.estimated_cost_eur != null && <span>💰 ~{rec.estimated_cost_eur}€</span>}
            {rec.deadline && <span>📅 până {fmtDate(rec.deadline)}</span>}
            <span>de {rec.created_by_email || "specialist"}</span>
            {rec.marketplace_request_id && (
              <span className="text-cyan-400 font-semibold" data-testid={`hh-rec-published-${i}`}>
                ✓ Publicat în marketplace
              </span>
            )}
          </div>
          {user?.role === "client" && !rec.marketplace_request_id && rec.priority !== "monitor" && rec.status === "active" && (
            <button
              onClick={onPublish}
              data-testid={`hh-rec-publish-${i}`}
              className="mt-2 text-[11px] px-2 py-1 rounded-md bg-cyan-500/15 text-cyan-300 hover:bg-cyan-500/25 border border-cyan-500/40 inline-flex items-center gap-1 font-semibold"
            >
              📢 Publică în marketplace
            </button>
          )}
        </div>
        {canEdit && (
          <div className="flex flex-col gap-1 shrink-0">
            {rec.status !== "done" && (
              <button onClick={onDone} data-testid={`hh-rec-done-${i}`}
                className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25">
                ✓ Done
              </button>
            )}
            <button onClick={onDelete} data-testid={`hh-rec-delete-${i}`}
              className="text-rose-400 hover:text-rose-300 self-end">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </li>
  );
};
