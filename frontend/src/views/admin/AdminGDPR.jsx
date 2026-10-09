// AdminGDPR — Phase 49 Part A. Documentary pack for DPO review.
// Shows ROPA, DPIA, Sub-processors, Cookie Inventory, Breach Plan + PDF exports.
import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  ShieldCheck, FileText, Cookie, AlertTriangle, Bot, Download,
  ChevronDown, ExternalLink, CheckCircle2, Globe, Building2,
  Inbox, ClipboardList, Archive, Send
} from "lucide-react";
import { API } from "../DashShared";
import { AdminCard } from "./AdminLayoutMetronic";

const TABS = [
  { id: "ropa", label: "ROPA (Art. 30)", icon: FileText, hint: "Registru activități prelucrare" },
  { id: "dpia", label: "DPIA AI Layer", icon: Bot, hint: "Risk assessment AI" },
  { id: "subs", label: "Sub-procesatori", icon: Globe, hint: "Stripe, Anthropic, etc." },
  { id: "cookies", label: "Cookies & Storage", icon: Cookie, hint: "Inventar complet" },
  { id: "breach", label: "Breach Plan 72h", icon: AlertTriangle, hint: "Checklist incident" },
  { id: "dsar", label: "DSAR Queue", icon: Inbox, hint: "Cereri utilizatori" },
  { id: "drills", label: "Drills & Audit", icon: ClipboardList, hint: "Breach drills + audit log" },
];

const PUBLIC_PDF_BASE = `${API}/gdpr/pdf`;

const TabHeader = ({ tabs, active, onChange, dark }) => (
  <div className={`flex flex-wrap gap-1 p-1 rounded-xl border ${dark ? "bg-slate-900 border-slate-800" : "bg-slate-50 border-slate-200"}`} data-testid="admin-gdpr-tabs">
    {tabs.map(t => {
      const Icon = t.icon;
      const isActive = active === t.id;
      return (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            isActive
              ? (dark ? "bg-slate-800 text-white shadow-sm" : "bg-white text-slate-900 shadow-sm")
              : (dark ? "text-slate-400 hover:text-slate-200" : "text-slate-500 hover:text-slate-700")
          }`}
          data-testid={`gdpr-tab-${t.id}`}
        >
          <Icon className="w-4 h-4" />
          <span>{t.label}</span>
        </button>
      );
    })}
  </div>
);

const DownloadBtn = ({ href, label, dark }) => (
  <a
    href={href}
    target="_blank"
    rel="noreferrer"
    className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
      dark ? "bg-blue-500/10 text-blue-400 hover:bg-blue-500/20" : "bg-blue-50 text-blue-700 hover:bg-blue-100"
    }`}
    data-testid={`gdpr-download-${label.toLowerCase().replace(/\s+/g, "-")}`}
  >
    <Download className="w-3.5 h-3.5" /> {label}
  </a>
);

const RopaActivity = ({ act, dark }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className={`rounded-xl border ${dark ? "bg-slate-900 border-slate-800" : "bg-white border-slate-200"}`} data-testid={`ropa-activity-${act.id}`}>
      <button onClick={() => setOpen(o => !o)} className="w-full flex items-center gap-3 px-4 py-3 text-left">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-mono ${dark ? "bg-slate-800 text-slate-300" : "bg-slate-100 text-slate-600"}`}>
          {act.id.slice(0, 2).toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <div className={`font-medium text-sm truncate ${dark ? "text-slate-100" : "text-slate-900"}`}>{act.name}</div>
          <div className={`text-xs truncate ${dark ? "text-slate-500" : "text-slate-500"}`}>{act.purpose}</div>
        </div>
        <ChevronDown className={`w-4 h-4 transition-transform ${open ? "rotate-180" : ""} ${dark ? "text-slate-500" : "text-slate-400"}`} />
      </button>
      {open && (
        <div className={`border-t px-4 py-4 grid sm:grid-cols-2 gap-x-6 gap-y-3 text-xs ${dark ? "border-slate-800" : "border-slate-100"}`}>
          <Field label="Temei legal" value={act.legal_basis} dark={dark} />
          <Field label="Retenție" value={act.retention} dark={dark} />
          <Field label="Vizați" value={act.data_subjects?.join(", ")} dark={dark} />
          <Field label="Destinatari" value={act.recipients?.join(", ")} dark={dark} />
          <FieldFull label="Categorii date" value={act.data_categories?.join(" · ")} dark={dark} />
          <FieldFull label="Măsuri securitate" value={act.security?.join(" · ")} dark={dark} />
          {act.transfers?.length > 0 && (
            <FieldFull
              label="Transferuri internaționale"
              value={act.transfers.map(t => `${t.to} → ${t.mechanism}`).join(" | ")}
              dark={dark}
              warn
            />
          )}
        </div>
      )}
    </div>
  );
};

const Field = ({ label, value, dark, warn }) => (
  <div>
    <div className={`text-[10px] font-bold uppercase tracking-wider mb-0.5 ${dark ? "text-slate-500" : "text-slate-400"}`}>{label}</div>
    <div className={`${warn ? "text-amber-500" : (dark ? "text-slate-200" : "text-slate-700")}`}>{value || "—"}</div>
  </div>
);

const FieldFull = ({ label, value, dark, warn }) => (
  <div className="sm:col-span-2">
    <div className={`text-[10px] font-bold uppercase tracking-wider mb-0.5 ${dark ? "text-slate-500" : "text-slate-400"}`}>{label}</div>
    <div className={`${warn ? "text-amber-500" : (dark ? "text-slate-200" : "text-slate-700")}`}>{value || "—"}</div>
  </div>
);

// =============== TAB CONTENT ===============

const RopaTab = ({ dark }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    axios.get(`${API}/gdpr/documents/ropa`)
      .then(r => setItems(r.data.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);
  return (
    <div className="space-y-3">
      <div className={`flex items-center justify-between rounded-xl border px-4 py-3 ${dark ? "bg-blue-500/5 border-blue-500/20" : "bg-blue-50 border-blue-100"}`}>
        <div className="flex items-center gap-3">
          <FileText className={`w-5 h-5 ${dark ? "text-blue-400" : "text-blue-600"}`} />
          <div>
            <div className={`text-sm font-medium ${dark ? "text-blue-300" : "text-blue-900"}`}>
              {items.length} activități de prelucrare documentate
            </div>
            <div className={`text-xs ${dark ? "text-blue-400/80" : "text-blue-700"}`}>
              Conform Art. 30 GDPR — fundament obligatoriu pentru DPO
            </div>
          </div>
        </div>
        <DownloadBtn href={`${PUBLIC_PDF_BASE}/ropa`} label="PDF ROPA" dark={dark} />
      </div>
      {loading && <div className={`text-sm ${dark ? "text-slate-400" : "text-slate-500"}`}>Se încarcă...</div>}
      {!loading && items.map(a => <RopaActivity key={a.id} act={a} dark={dark} />)}
    </div>
  );
};

const DpiaTab = ({ dark }) => {
  const [doc, setDoc] = useState(null);
  useEffect(() => {
    axios.get(`${API}/gdpr/documents/dpia`).then(r => setDoc(r.data)).catch(() => setDoc(null));
  }, []);
  if (!doc) return <div className={`text-sm ${dark ? "text-slate-400" : "text-slate-500"}`}>Se încarcă...</div>;
  return (
    <div className="space-y-4">
      <div className={`rounded-xl border px-5 py-4 ${dark ? "bg-amber-500/5 border-amber-500/20" : "bg-amber-50 border-amber-200"}`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className={`text-sm font-semibold ${dark ? "text-amber-300" : "text-amber-900"}`}>{doc.title}</div>
            <div className={`text-xs mt-0.5 ${dark ? "text-amber-400/80" : "text-amber-700"}`}>
              Versiune {doc.version} · Revizuire: {doc.review_frequency}
            </div>
          </div>
          <DownloadBtn href={`${PUBLIC_PDF_BASE}/dpia`} label="PDF DPIA" dark={dark} />
        </div>
      </div>

      <AdminCard testid="dpia-scope">
        <div className={`text-[10px] font-bold uppercase tracking-wider mb-1 ${dark ? "text-slate-500" : "text-slate-400"}`}>Scop</div>
        <div className={`text-sm ${dark ? "text-slate-200" : "text-slate-700"}`}>{doc.scope}</div>
      </AdminCard>

      <div className="grid lg:grid-cols-2 gap-4">
        <AdminCard title="🔺 Factori de risc ridicat" testid="dpia-risks">
          <ul className="space-y-2">
            {doc.high_risk_factors.map((f, i) => (
              <li key={i} className={`flex gap-2 text-sm ${dark ? "text-slate-300" : "text-slate-700"}`}>
                <span className="text-red-500 shrink-0">●</span> <span>{f}</span>
              </li>
            ))}
          </ul>
        </AdminCard>

        <AdminCard title="🛡️ Măsuri de atenuare" testid="dpia-mitigations">
          <ul className="space-y-2">
            {doc.mitigations.map((m, i) => (
              <li key={i} className={`flex gap-2 text-sm ${dark ? "text-slate-300" : "text-slate-700"}`}>
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" /> <span>{m}</span>
              </li>
            ))}
          </ul>
        </AdminCard>
      </div>

      <AdminCard title="✅ Risc rezidual" testid="dpia-residual">
        <div className={`text-sm ${dark ? "text-emerald-300" : "text-emerald-800"}`}>{doc.residual_risk}</div>
      </AdminCard>
    </div>
  );
};

const SubProcessorsTab = ({ dark }) => {
  const [items, setItems] = useState([]);
  useEffect(() => {
    axios.get(`${API}/gdpr/documents/sub-processors`).then(r => setItems(r.data.items || [])).catch(() => setItems([]));
  }, []);
  const statusStyles = {
    active: dark ? "bg-emerald-500/15 text-emerald-300" : "bg-emerald-50 text-emerald-700",
    ready_to_activate: dark ? "bg-amber-500/15 text-amber-300" : "bg-amber-50 text-amber-700",
    inactive: dark ? "bg-slate-700 text-slate-300" : "bg-slate-100 text-slate-500",
  };
  return (
    <div className="overflow-x-auto rounded-xl border" style={{ borderColor: dark ? "#1e293b" : "#e2e8f0" }}>
      <table className="w-full text-sm" data-testid="gdpr-subs-table">
        <thead>
          <tr className={dark ? "bg-slate-900 text-slate-400" : "bg-slate-50 text-slate-500"}>
            {["Procesator", "Scop", "Țară", "Mecanism transfer", "DPA", "Status"].map(h => (
              <th key={h} className="text-left text-[11px] font-bold uppercase tracking-wider px-4 py-3">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map(s => (
            <tr key={s.id} className={`border-t ${dark ? "border-slate-800" : "border-slate-100"}`} data-testid={`gdpr-sub-${s.id}`}>
              <td className={`px-4 py-3 font-medium ${dark ? "text-slate-100" : "text-slate-900"}`}>{s.name}</td>
              <td className={`px-4 py-3 ${dark ? "text-slate-300" : "text-slate-600"}`}>{s.purpose}</td>
              <td className={`px-4 py-3 text-xs ${dark ? "text-slate-400" : "text-slate-500"}`}>{s.country}</td>
              <td className={`px-4 py-3 text-xs ${dark ? "text-slate-400" : "text-slate-500"}`}>{s.transfer_mechanism}</td>
              <td className="px-4 py-3">
                {s.dpa_url ? (
                  <a href={s.dpa_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-blue-500 hover:underline">
                    Vezi DPA <ExternalLink className="w-3 h-3" />
                  </a>
                ) : "—"}
              </td>
              <td className="px-4 py-3">
                <span className={`inline-block text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded-full ${statusStyles[s.status] || statusStyles.inactive}`}>
                  {s.status.replace(/_/g, " ")}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const CookiesTab = ({ dark }) => {
  const [items, setItems] = useState([]);
  useEffect(() => {
    axios.get(`${API}/gdpr/documents/cookies`).then(r => setItems(r.data.items || [])).catch(() => setItems([]));
  }, []);
  const typeColor = {
    necesar: dark ? "bg-emerald-500/15 text-emerald-300" : "bg-emerald-50 text-emerald-700",
    funcțional: dark ? "bg-blue-500/15 text-blue-300" : "bg-blue-50 text-blue-700",
    preferință: dark ? "bg-purple-500/15 text-purple-300" : "bg-purple-50 text-purple-700",
  };
  return (
    <div>
      <div className={`mb-4 rounded-xl border px-4 py-3 text-xs ${dark ? "bg-slate-900 border-slate-800 text-slate-400" : "bg-slate-50 border-slate-200 text-slate-600"}`}>
        ℹ️ Toate cookies-urile sunt <strong>first-party</strong>. Nu folosim tracking publicitar (Google Analytics, Meta Pixel) fără consimțământ explicit.
      </div>
      <div className="overflow-x-auto rounded-xl border" style={{ borderColor: dark ? "#1e293b" : "#e2e8f0" }}>
        <table className="w-full text-sm" data-testid="gdpr-cookies-table">
          <thead>
            <tr className={dark ? "bg-slate-900 text-slate-400" : "bg-slate-50 text-slate-500"}>
              {["Nume", "Scop", "Tip", "Durată", "First-party"].map(h => (
                <th key={h} className="text-left text-[11px] font-bold uppercase tracking-wider px-4 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map(c => (
              <tr key={c.name} className={`border-t ${dark ? "border-slate-800" : "border-slate-100"}`} data-testid={`gdpr-cookie-${c.name}`}>
                <td className={`px-4 py-3 font-mono text-xs ${dark ? "text-slate-200" : "text-slate-800"}`}>{c.name}</td>
                <td className={`px-4 py-3 ${dark ? "text-slate-300" : "text-slate-600"}`}>{c.purpose}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded-full ${typeColor[c.type] || ""}`}>{c.type}</span>
                </td>
                <td className={`px-4 py-3 text-xs ${dark ? "text-slate-400" : "text-slate-500"}`}>{c.duration}</td>
                <td className="px-4 py-3">
                  {c.first_party ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : <span className="text-slate-400">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const BreachTab = ({ dark }) => {
  const [steps, setSteps] = useState([]);
  useEffect(() => {
    axios.get(`${API}/gdpr/documents/breach-plan`).then(r => setSteps(r.data.steps || [])).catch(() => setSteps([]));
  }, []);
  return (
    <div className="space-y-4">
      <div className={`rounded-xl border px-5 py-4 ${dark ? "bg-red-500/5 border-red-500/20" : "bg-red-50 border-red-200"}`}>
        <div className="flex items-start gap-3">
          <AlertTriangle className={`w-5 h-5 mt-0.5 ${dark ? "text-red-400" : "text-red-600"}`} />
          <div>
            <div className={`text-sm font-semibold ${dark ? "text-red-300" : "text-red-900"}`}>
              Notificare ANSPDCP în maxim 72h (Art. 33 GDPR)
            </div>
            <div className={`text-xs mt-1 ${dark ? "text-red-400/80" : "text-red-700"}`}>
              Procedura oficială. Toate drill-urile sunt log-ate la <code className="text-[11px]">/api/admin/gdpr/breach-drill</code>.
            </div>
          </div>
        </div>
      </div>
      <div className="relative pl-4">
        <div className={`absolute left-[7px] top-2 bottom-2 w-px ${dark ? "bg-slate-700" : "bg-slate-200"}`} />
        {steps.map(s => (
          <div key={s.step} className="relative pl-6 pb-6" data-testid={`breach-step-${s.step}`}>
            <div className={`absolute left-0 top-1 w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${dark ? "bg-red-500/20 text-red-300 ring-2 ring-slate-950" : "bg-red-100 text-red-700 ring-2 ring-white"}`}>
              {s.step}
            </div>
            <div className={`text-sm font-semibold ${dark ? "text-slate-100" : "text-slate-900"}`}>{s.name}</div>
            <ul className="mt-2 space-y-1">
              {s.actions.map((a, i) => (
                <li key={i} className={`text-xs flex gap-2 ${dark ? "text-slate-400" : "text-slate-600"}`}>
                  <span className="text-slate-500">→</span> <span>{a}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};

// =============== DSAR QUEUE (Part D) ===============

const DSAR_STATUSES = [
  { id: "all", label: "Toate" },
  { id: "new", label: "Noi" },
  { id: "in_review", label: "În analiză" },
  { id: "completed", label: "Finalizate" },
  { id: "rejected", label: "Respinse" },
];

const DsarTab = ({ dark }) => {
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState({});
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [editStatus, setEditStatus] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    axios.get(`${API}/admin/gdpr/dsar`, { params: { status: statusFilter } })
      .then(r => { setItems(r.data.items || []); setCounts(r.data.counts || {}); })
      .catch(() => { setItems([]); setCounts({}); })
      .finally(() => setLoading(false));
  };
  useEffect(load, [statusFilter]);

  const openEdit = (it) => { setSelected(it); setEditStatus(it.status); setEditNotes(it.admin_notes || ""); };
  const save = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await axios.patch(`${API}/admin/gdpr/dsar/${selected._id}`, { status: editStatus, admin_notes: editNotes });
      setSelected(null);
      load();
    } catch (e) {
      alert("Eroare la salvare: " + (e?.response?.data?.detail || e.message));
    } finally {
      setSaving(false);
    }
  };

  const statusPill = (s) => {
    const styles = {
      new: dark ? "bg-blue-500/15 text-blue-300" : "bg-blue-50 text-blue-700",
      in_review: dark ? "bg-amber-500/15 text-amber-300" : "bg-amber-50 text-amber-700",
      completed: dark ? "bg-emerald-500/15 text-emerald-300" : "bg-emerald-50 text-emerald-700",
      rejected: dark ? "bg-red-500/15 text-red-300" : "bg-red-50 text-red-700",
    };
    return <span className={`inline-block text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded-full ${styles[s] || ""}`}>{s.replace(/_/g, " ")}</span>;
  };

  const slaPill = (it) => {
    if (!it.sla_due_at) return null;
    const due = new Date(it.sla_due_at);
    const days = Math.round((due.getTime() - Date.now()) / 86400000);
    const overdue = days < 0;
    const cls = overdue ? "text-red-400" : days < 7 ? "text-amber-400" : (dark ? "text-slate-400" : "text-slate-500");
    return <span className={`text-[10px] ${cls}`}>{overdue ? `Întârziat ${-days}z` : `SLA ${days}z`}</span>;
  };

  return (
    <div className="space-y-3">
      <div className={`flex flex-wrap items-center gap-2 rounded-xl border px-3 py-2 ${dark ? "bg-slate-900 border-slate-800" : "bg-white border-slate-200"}`}>
        {DSAR_STATUSES.map(s => (
          <button
            key={s.id}
            onClick={() => setStatusFilter(s.id)}
            className={`px-3 py-1 text-xs rounded-full font-medium ${
              statusFilter === s.id
                ? (dark ? "bg-blue-500/20 text-blue-300" : "bg-blue-50 text-blue-700")
                : (dark ? "text-slate-400 hover:bg-slate-800" : "text-slate-500 hover:bg-slate-50")
            }`}
            data-testid={`dsar-filter-${s.id}`}
          >
            {s.label} {counts[s.id] !== undefined && s.id !== "all" && <span className="opacity-60">({counts[s.id]})</span>}
          </button>
        ))}
        <span className={`ml-auto text-xs ${dark ? "text-slate-500" : "text-slate-400"}`}>
          Total: {counts.total ?? 0}
        </span>
      </div>

      <div className="overflow-x-auto rounded-xl border" style={{ borderColor: dark ? "#1e293b" : "#e2e8f0" }}>
        <table className="w-full text-sm" data-testid="dsar-table">
          <thead>
            <tr className={dark ? "bg-slate-900 text-slate-400" : "bg-slate-50 text-slate-500"}>
              {["User", "Tip", "Status", "Trimisă", "SLA", "Acțiuni"].map(h => (
                <th key={h} className="text-left text-[11px] font-bold uppercase tracking-wider px-4 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={6} className={`px-4 py-6 text-center text-sm ${dark ? "text-slate-400" : "text-slate-500"}`}>Se încarcă...</td></tr>
            )}
            {!loading && items.length === 0 && (
              <tr><td colSpan={6} className={`px-4 py-6 text-center text-sm ${dark ? "text-slate-500" : "text-slate-400"}`}>Nicio cerere DSAR în acest filtru.</td></tr>
            )}
            {items.map(it => (
              <tr key={it._id} className={`border-t ${dark ? "border-slate-800" : "border-slate-100"}`} data-testid={`dsar-row-${it._id}`}>
                <td className="px-4 py-3">
                  <div className={`font-medium text-sm ${dark ? "text-slate-100" : "text-slate-900"}`}>{it.user_email || "—"}</div>
                  <div className={`text-[11px] ${dark ? "text-slate-500" : "text-slate-500"}`}>{it.user_role || "—"} · {it.user_id?.slice(-8)}</div>
                </td>
                <td className={`px-4 py-3 text-xs ${dark ? "text-slate-300" : "text-slate-600"}`}>{it.type}</td>
                <td className="px-4 py-3">{statusPill(it.status)}</td>
                <td className={`px-4 py-3 text-xs ${dark ? "text-slate-400" : "text-slate-500"}`}>
                  {it.created_at ? new Date(it.created_at).toLocaleDateString("ro-RO") : "—"}
                </td>
                <td className="px-4 py-3">{slaPill(it)}</td>
                <td className="px-4 py-3">
                  <button onClick={() => openEdit(it)} className="text-xs text-blue-500 hover:underline" data-testid={`dsar-edit-${it._id}`}>
                    Gestionează
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setSelected(null)}>
          <div
            className={`max-w-lg w-full rounded-2xl border p-6 ${dark ? "bg-slate-900 border-slate-800" : "bg-white border-slate-200"}`}
            onClick={e => e.stopPropagation()}
            data-testid="dsar-edit-modal"
          >
            <h3 className={`font-semibold text-lg mb-1 ${dark ? "text-slate-100" : "text-slate-900"}`}>Cerere DSAR · {selected.type}</h3>
            <p className={`text-xs mb-4 ${dark ? "text-slate-500" : "text-slate-500"}`}>{selected.user_email} · {selected.user_role}</p>
            {selected.reason && (
              <div className={`text-xs p-3 rounded-lg mb-3 ${dark ? "bg-slate-800 text-slate-300" : "bg-slate-50 text-slate-700"}`}>
                <strong>Motiv:</strong> {selected.reason}
              </div>
            )}
            <label className={`text-xs font-medium mb-1 block ${dark ? "text-slate-300" : "text-slate-700"}`}>Status</label>
            <select value={editStatus} onChange={e => setEditStatus(e.target.value)} className={`w-full mb-3 px-3 py-2 text-sm rounded-lg border ${dark ? "bg-slate-800 border-slate-700 text-slate-100" : "bg-white border-slate-200 text-slate-900"}`} data-testid="dsar-edit-status">
              <option value="new">Nou</option>
              <option value="in_review">În analiză</option>
              <option value="completed">Finalizat</option>
              <option value="rejected">Respins</option>
            </select>
            <label className={`text-xs font-medium mb-1 block ${dark ? "text-slate-300" : "text-slate-700"}`}>Note admin (audit trail)</label>
            <textarea value={editNotes} onChange={e => setEditNotes(e.target.value)} rows={3} className={`w-full mb-4 px-3 py-2 text-sm rounded-lg border ${dark ? "bg-slate-800 border-slate-700 text-slate-100" : "bg-white border-slate-200 text-slate-900"}`} data-testid="dsar-edit-notes" />
            <div className="flex justify-end gap-2">
              <button onClick={() => setSelected(null)} className={`px-3 py-1.5 text-sm rounded-lg ${dark ? "bg-slate-800 text-slate-300" : "bg-slate-100 text-slate-700"}`}>Anulează</button>
              <button onClick={save} disabled={saving} className="px-3 py-1.5 text-sm rounded-lg bg-blue-600 hover:bg-blue-700 text-white" data-testid="dsar-save-btn">
                {saving ? "Se salvează..." : "Salvează"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// =============== DRILLS & AUDIT (Part D) ===============

const DrillsAuditTab = ({ dark }) => {
  const [drills, setDrills] = useState([]);
  const [audit, setAudit] = useState([]);
  const [form, setForm] = useState({ scenario: "", duration_minutes: 0, notes: "", steps_done: [] });
  const [saving, setSaving] = useState(false);
  const STEPS = ["Detectare", "Evaluare", "Notificare ANSPDCP", "Notificare utilizatori", "Remediere"];

  const load = () => {
    axios.get(`${API}/admin/gdpr/breach-drill`).then(r => setDrills(r.data.items || [])).catch(() => setDrills([]));
    axios.get(`${API}/admin/gdpr/audit`).then(r => setAudit(r.data.items || [])).catch(() => setAudit([]));
  };
  useEffect(load, []);

  const toggleStep = (s) => setForm(f => ({ ...f, steps_done: f.steps_done.includes(s) ? f.steps_done.filter(x => x !== s) : [...f.steps_done, s] }));

  const submit = async () => {
    if (!form.scenario.trim()) { alert("Scenariu obligatoriu"); return; }
    setSaving(true);
    try {
      await axios.post(`${API}/admin/gdpr/breach-drill`, form);
      setForm({ scenario: "", duration_minutes: 0, notes: "", steps_done: [] });
      load();
    } catch (e) {
      alert("Eroare: " + (e?.response?.data?.detail || e.message));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <AdminCard title="🚨 Înregistrează un drill (exercițiu)" testid="drill-form-card">
        <div className="space-y-3">
          <input
            value={form.scenario}
            onChange={e => setForm(f => ({ ...f, scenario: e.target.value }))}
            placeholder="Scenariu (ex: scurgere accidentală baze date Stripe)"
            className={`w-full px-3 py-2 text-sm rounded-lg border ${dark ? "bg-slate-800 border-slate-700 text-slate-100" : "bg-white border-slate-200 text-slate-900"}`}
            data-testid="drill-scenario"
          />
          <div className="flex flex-wrap gap-2">
            {STEPS.map(s => {
              const on = form.steps_done.includes(s);
              return (
                <button
                  key={s}
                  onClick={() => toggleStep(s)}
                  className={`px-3 py-1.5 text-xs rounded-full border ${
                    on
                      ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                      : (dark ? "border-slate-700 text-slate-400" : "border-slate-200 text-slate-500")
                  }`}
                  data-testid={`drill-step-${s}`}
                >
                  {on ? "✓ " : ""}{s}
                </button>
              );
            })}
          </div>
          <div className="flex gap-3">
            <input
              type="number"
              min={0}
              value={form.duration_minutes}
              onChange={e => setForm(f => ({ ...f, duration_minutes: parseInt(e.target.value) || 0 }))}
              placeholder="Durată (min)"
              className={`w-40 px-3 py-2 text-sm rounded-lg border ${dark ? "bg-slate-800 border-slate-700 text-slate-100" : "bg-white border-slate-200 text-slate-900"}`}
              data-testid="drill-duration"
            />
            <input
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              placeholder="Note (max 1000)"
              maxLength={1000}
              className={`flex-1 px-3 py-2 text-sm rounded-lg border ${dark ? "bg-slate-800 border-slate-700 text-slate-100" : "bg-white border-slate-200 text-slate-900"}`}
              data-testid="drill-notes"
            />
            <button onClick={submit} disabled={saving} className="px-4 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-700 text-white" data-testid="drill-submit">
              {saving ? "Se salvează..." : "Înregistrează"}
            </button>
          </div>
        </div>
      </AdminCard>

      <AdminCard title={`📚 Istoric drills (${drills.length})`} testid="drill-history-card">
        {drills.length === 0 && <div className={`text-sm ${dark ? "text-slate-500" : "text-slate-400"}`}>Niciun drill înregistrat încă.</div>}
        <div className="space-y-2">
          {drills.map(d => (
            <div key={d._id} className={`p-3 rounded-lg border text-sm ${dark ? "bg-slate-800/50 border-slate-700" : "bg-slate-50 border-slate-200"}`} data-testid={`drill-row-${d._id}`}>
              <div className="flex justify-between gap-2">
                <span className={`font-medium ${dark ? "text-slate-100" : "text-slate-900"}`}>{d.scenario}</span>
                <span className={`text-xs ${dark ? "text-slate-500" : "text-slate-500"}`}>
                  {d.created_at ? new Date(d.created_at).toLocaleString("ro-RO") : "—"}
                </span>
              </div>
              <div className={`text-xs mt-1 ${dark ? "text-slate-400" : "text-slate-600"}`}>
                {d.actor_name} · {d.duration_minutes}min · pași: {(d.steps_done || []).join(", ") || "—"}
              </div>
              {d.notes && <div className={`text-xs mt-1 italic ${dark ? "text-slate-500" : "text-slate-500"}`}>{d.notes}</div>}
            </div>
          ))}
        </div>
      </AdminCard>

      <AdminCard title={`📜 GDPR Audit Log (${audit.length})`} testid="gdpr-audit-card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className={dark ? "text-slate-500" : "text-slate-400"}>
                <th className="text-left text-[10px] uppercase font-bold tracking-wider px-2 py-1.5">Eveniment</th>
                <th className="text-left text-[10px] uppercase font-bold tracking-wider px-2 py-1.5">Actor</th>
                <th className="text-left text-[10px] uppercase font-bold tracking-wider px-2 py-1.5">Data</th>
              </tr>
            </thead>
            <tbody>
              {audit.length === 0 && (
                <tr><td colSpan={3} className={`px-2 py-3 text-center text-xs ${dark ? "text-slate-500" : "text-slate-400"}`}>Niciun eveniment de audit GDPR.</td></tr>
              )}
              {audit.map(a => (
                <tr key={a._id} className={`border-t ${dark ? "border-slate-800" : "border-slate-100"}`} data-testid={`audit-row-${a._id}`}>
                  <td className={`px-2 py-2 text-xs ${dark ? "text-slate-200" : "text-slate-800"}`}>{a.kind}</td>
                  <td className={`px-2 py-2 text-xs ${dark ? "text-slate-400" : "text-slate-600"}`}>{a.actor_name || a.actor?.slice(-8) || "—"}</td>
                  <td className={`px-2 py-2 text-xs ${dark ? "text-slate-500" : "text-slate-500"}`}>{a.created_at ? new Date(a.created_at).toLocaleString("ro-RO") : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AdminCard>
    </div>
  );
};

// =============== ROOT ===============

export const AdminGDPR = () => {
  const [active, setActive] = useState("ropa");
  const [company, setCompany] = useState(null);
  const theme = document.documentElement.getAttribute("data-admin-theme") || "light";
  const dark = theme === "dark";

  useEffect(() => {
    axios.get(`${API}/gdpr/documents/company`).then(r => setCompany(r.data)).catch(() => setCompany(null));
  }, []);

  return (
    <div className="space-y-5" data-testid="admin-gdpr-root">
      {company && (
        <div className={`rounded-2xl border px-5 py-4 flex items-center gap-4 ${dark ? "bg-slate-900 border-slate-800" : "bg-white border-slate-200"}`}>
          <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${dark ? "bg-emerald-500/10" : "bg-emerald-50"}`}>
            <Building2 className={`w-5 h-5 ${dark ? "text-emerald-400" : "text-emerald-600"}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className={`text-sm font-semibold truncate ${dark ? "text-slate-100" : "text-slate-900"}`}>{company.name}</div>
            <div className={`text-xs truncate ${dark ? "text-slate-500" : "text-slate-500"}`}>
              {company.address} · {company.registry}
            </div>
          </div>
          <a
            href={`${API}/gdpr/pdf/bundle`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 text-xs rounded-full font-semibold bg-gradient-to-r from-emerald-500 to-teal-500 text-white hover:from-emerald-600 hover:to-teal-600 transition-colors"
            data-testid="gdpr-bundle-download"
          >
            <Archive className="w-3.5 h-3.5" /> Pachet ZIP pentru DPO
          </a>
          <div className={`text-right text-xs ml-2 ${dark ? "text-slate-400" : "text-slate-500"}`}>
            <div className="font-medium">DPO</div>
            <a href={`mailto:${company.dpo_email}`} className="text-blue-500 hover:underline">{company.dpo_email}</a>
          </div>
        </div>
      )}

      <TabHeader tabs={TABS} active={active} onChange={setActive} dark={dark} />

      <div>
        {active === "ropa" && <RopaTab dark={dark} />}
        {active === "dpia" && <DpiaTab dark={dark} />}
        {active === "subs" && <SubProcessorsTab dark={dark} />}
        {active === "cookies" && <CookiesTab dark={dark} />}
        {active === "breach" && <BreachTab dark={dark} />}
        {active === "dsar" && <DsarTab dark={dark} />}
        {active === "drills" && <DrillsAuditTab dark={dark} />}
      </div>
    </div>
  );
};

export default AdminGDPR;
