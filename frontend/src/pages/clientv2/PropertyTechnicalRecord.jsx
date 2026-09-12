/**
 * Property Technical Record (v1) — dosar tehnic viu al unei proprietăți.
 *
 * Reguli de implementare respectate:
 *   • Nu duplică documentele/assets/timeline — reutilizează endpoint-urile existente
 *   • Domain A / B / C rămân distincte semantic în UI (secțiuni separate)
 *   • Orice diagnostic nou pornește UNVERIFIED (badge vizibil)
 *   • Fără scor numeric în Transaction Readiness — doar statusuri
 *   • FR și RO sunt jurisdicții distincte, tratate ca metadate
 *   • HartaBlocuri = doar sursă externă (source_type=external_reference)
 *   • Mobile-first + desktop responsive
 *   • Fără emojis; iconițe din lucide-react
 */
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  ClipboardList, Building, FileText, Layers, Clock,
  ShieldAlert, CheckCircle2, AlertTriangle, CircleDashed,
  Plus, Trash2, Pencil, ExternalLink, ChevronDown, ChevronUp, Info, Loader2,
  ShieldCheck, ShieldX, Download, Users, Link as LinkIcon, Paperclip, Search,
} from "lucide-react";
import { API } from "../DashShared";
import { formatApiError } from "../../auth";

// ─────────────────────────────────────────────────────────────────────────────
// STATUS TOKENS (COMPLETE / PARTIAL / MISSING / NOT_VERIFIED)
// ─────────────────────────────────────────────────────────────────────────────
const STATUS_META = {
  COMPLETE: { label: "Complet", icon: CheckCircle2, cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  PARTIAL: { label: "Parțial", icon: AlertTriangle, cls: "bg-amber-50 text-amber-700 border-amber-200" },
  MISSING: { label: "Lipsă", icon: CircleDashed, cls: "bg-slate-100 text-slate-500 border-slate-200" },
  NOT_VERIFIED: { label: "Neverificat", icon: ShieldAlert, cls: "bg-sky-50 text-sky-700 border-sky-200" },
};

const StatusBadge = ({ status, testid }) => {
  const meta = STATUS_META[status] || STATUS_META.MISSING;
  const Icon = meta.icon;
  return (
    <span data-testid={testid}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${meta.cls}`}>
      <Icon className="w-3 h-3" /> {meta.label}
    </span>
  );
};

const VERIF_META = {
  unverified: { label: "Neverificat", cls: "bg-slate-100 text-slate-500" },
  declared: { label: "Declarat", cls: "bg-sky-50 text-sky-700" },
  documented: { label: "Documentat", cls: "bg-indigo-50 text-indigo-700" },
  verified: { label: "Verificat", cls: "bg-emerald-50 text-emerald-700" },
};

const VerifBadge = ({ status, testid }) => {
  const m = VERIF_META[status] || VERIF_META.unverified;
  return (
    <span data-testid={testid}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${m.cls}`}>
      {m.label}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SECTION SHELL
// ─────────────────────────────────────────────────────────────────────────────
const SECTION_DEFS = [
  { id: "core", label: "Proprietatea", icon: ClipboardList },
  { id: "building", label: "Contextul clădirii", icon: Building },
  { id: "diagnostics", label: "Diagnostice tehnice", icon: ShieldAlert },
  { id: "systems", label: "Sisteme & Active", icon: Layers },
  { id: "documents", label: "Documente & Evidență", icon: FileText },
  { id: "history", label: "Istoric", icon: Clock },
  { id: "readiness", label: "Pregătire tranzacție", icon: CheckCircle2 },
];

// ─────────────────────────────────────────────────────────────────────────────
// PROPERTY CORE (A)
// ─────────────────────────────────────────────────────────────────────────────
const PropertyCoreSection = ({ core }) => {
  if (!core) return null;
  const identity = core.identity || {};
  const stats = core.stats || {};
  const twin = core.digital_twin || {};
  const items = [
    ["Nume", identity.name],
    ["Adresă", identity.address],
    ["Tip", identity.type],
    ["Camere", identity.rooms],
    ["Suprafață", identity.surface ? `${identity.surface} mp` : null],
  ];
  return (
    <div data-testid="ptr-core-section" className="space-y-4">
      <div className="rounded-2xl border border-slate-100 bg-white p-4">
        <div className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-400">Identitate</div>
        <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1.5">
          {items.map(([k, v]) => (
            <div key={k} className="text-[11px]">
              <dt className="text-slate-400">{k}</dt>
              <dd className="font-bold text-slate-800">{v || "—"}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div className="rounded-2xl border border-slate-100 bg-white p-4">
        <div className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-400">Rezumat tehnic</div>
        <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2">
          <SummaryTile label="Documente" value={stats.documents ?? 0} sub={`${stats.documents_verified ?? 0} verificate`} />
          <SummaryTile label="Active" value={stats.assets_active ?? 0} sub="echipamente" />
          <SummaryTile label="Cereri" value={stats.requests ?? 0} sub="lucrări totale" />
          <SummaryTile label="Garanții" value={stats.warranties_active ?? 0} sub="active" />
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <SummaryTile label="Digital Twin" value={twin.status || "—"} sub={twin.unlocked ? "deblocat" : "referință"} />
          <SummaryTile label="Evenimente" value={stats.events ?? 0} sub={`${stats.maintenance_logs ?? 0} logs mentenanță`} />
        </div>
      </div>
    </div>
  );
};

const SummaryTile = ({ label, value, sub }) => (
  <div className="rounded-xl bg-slate-50 p-2.5">
    <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">{label}</div>
    <div className="mt-0.5 text-sm font-black text-slate-900 truncate">{value ?? "—"}</div>
    {sub && <div className="text-[9px] text-slate-400">{sub}</div>}
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// BUILDING CONTEXT (B)
// ─────────────────────────────────────────────────────────────────────────────
const BuildingContextSection = ({ propId, initial, vocab, viewer, onSaved }) => {
  const [building, setBuilding] = useState(initial);
  const [editing, setEditing] = useState(!initial);
  const [form, setForm] = useState(buildingToForm(initial));
  const [busy, setBusy] = useState(false);
  const [neighbours, setNeighbours] = useState(null);
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    setBuilding(initial);
    setForm(buildingToForm(initial));
    setEditing(!initial);
  }, [initial]);

  useEffect(() => {
    axios.get(`${API}/properties/${propId}/building-neighbours`)
      .then(r => setNeighbours(r.data))
      .catch(() => setNeighbours({ neighbours: [], total: 0 }));
  }, [propId, building?.id]);

  const save = async () => {
    setBusy(true);
    try {
      const payload = cleanPayload(form);
      const res = await axios.post(`${API}/properties/${propId}/building-context`, payload);
      setBuilding(res.data.building);
      setEditing(false);
      onSaved?.(res.data.building);
    } catch (e) {
      alert(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const verify = async () => {
    if (!building?.id) return;
    const notes = window.prompt("Note pentru verificarea contextului clădirii (opțional):", "") || null;
    setBusy(true);
    try {
      const res = await axios.post(`${API}/admin/buildings/${building.id}/verify`, { notes });
      setBuilding(res.data.building);
      onSaved?.(res.data.building);
    } catch (e) { alert(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const attachExisting = async (b) => {
    if (!window.confirm(`Conectezi această proprietate la „${b.name}" (${b.units_registered} unități înregistrate)?`)) return;
    setBusy(true);
    try {
      const res = await axios.post(`${API}/properties/${propId}/attach-building`, { building_id: b.id });
      setBuilding(res.data.building);
      setSearchOpen(false);
      onSaved?.(res.data.building);
    } catch (e) { alert(formatApiError(e)); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="ptr-building-section" className="space-y-3">
      <div className="rounded-2xl border border-slate-100 bg-white p-4">
        <div className="flex items-center gap-2">
          <div className="flex-1 min-w-0">
            <div className="text-sm font-black text-slate-900">Contextul clădirii</div>
            <div className="text-[10px] text-slate-400">Informație despre clădire, nu despre apartament. Sursă și încredere separate de proprietate.</div>
          </div>
          {building && !editing && (
            <button data-testid="ptr-building-edit" onClick={() => setEditing(true)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border-2 border-slate-200 text-[10px] font-bold text-slate-600">
              <Pencil className="w-3 h-3" /> Editează
            </button>
          )}
        </div>

        {!editing && building && (
          <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5">
            <FieldRow label="Nume clădire" value={building.name} />
            <FieldRow label="Adresă" value={building.address} />
            <FieldRow label="An construcție" value={building.construction_year} />
            <FieldRow label="Tipologie" value={building.building_type_label} />
            <FieldRow label="Nr. unități" value={building.number_of_units} />
            <FieldRow label="Etaje" value={building.floors} />
            <FieldRow label="Sursă" value={building.source_type_label} />
            <FieldRow label="Sursă nume" value={building.source_name} />
            {building.source_reference && (
              <div className="col-span-2 text-[11px]">
                <div className="text-slate-400">Referință sursă</div>
                <a data-testid="ptr-building-source-link" href={building.source_reference} target="_blank" rel="noreferrer"
                  className="font-bold text-indigo-700 inline-flex items-center gap-1 break-all">
                  {building.source_reference} <ExternalLink className="w-3 h-3 shrink-0" />
                </a>
              </div>
            )}
            <div className="col-span-2 mt-1 flex items-center gap-2 flex-wrap">
              <span className="text-[10px] text-slate-400">Verificare:</span>
              <VerifBadge status={building.verification_status} testid="ptr-building-verif" />
              {viewer?.is_verifier && building.verification_status !== "verified" && (
                <button onClick={verify} disabled={busy} data-testid="ptr-building-verify-btn"
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-black bg-emerald-600 text-white disabled:opacity-50">
                  <ShieldCheck className="w-3 h-3" /> Verifică contextul
                </button>
              )}
              {building.verification_status === "verified" && neighbours && neighbours.total > 0 && (
                <span className="text-[10px] font-bold text-emerald-700" data-testid="ptr-building-shared">
                  · Context comun {neighbours.total + 1} unități
                </span>
              )}
            </div>
          </div>
        )}

        {editing && (
          <div className="mt-3 space-y-2" data-testid="ptr-building-form">
            <TextInput label="Nume clădire" value={form.name} onChange={v => setForm({ ...form, name: v })} testid="ptr-b-name" />
            <TextInput label="Adresă" value={form.address} onChange={v => setForm({ ...form, address: v })} testid="ptr-b-address" />
            <div className="grid grid-cols-2 gap-2">
              <NumberInput label="An construcție" value={form.construction_year} onChange={v => setForm({ ...form, construction_year: v })} testid="ptr-b-year" />
              <SelectInput label="Tipologie" value={form.building_type} onChange={v => setForm({ ...form, building_type: v })}
                options={vocab?.building_types || []} testid="ptr-b-type" />
              <NumberInput label="Nr. unități" value={form.number_of_units} onChange={v => setForm({ ...form, number_of_units: v })} testid="ptr-b-units" />
              <NumberInput label="Etaje" value={form.floors} onChange={v => setForm({ ...form, floors: v })} testid="ptr-b-floors" />
              <SelectInput label="Tip sursă" value={form.source_type} onChange={v => setForm({ ...form, source_type: v })}
                options={vocab?.source_types || []} testid="ptr-b-src-type" />
              <TextInput label="Nume sursă" value={form.source_name} onChange={v => setForm({ ...form, source_name: v })}
                placeholder="ex. HartaBlocuri" testid="ptr-b-src-name" />
            </div>
            <TextInput label="Referință sursă (URL/ID)" value={form.source_reference}
              onChange={v => setForm({ ...form, source_reference: v })} testid="ptr-b-src-ref" />
            <div className="flex items-center gap-2 pt-2">
              <button onClick={save} disabled={busy} data-testid="ptr-building-save"
                className="px-4 py-2 rounded-full text-xs font-black text-black disabled:opacity-50" style={{ background: "#d4ff3a" }}>
                {busy ? <Loader2 className="w-3 h-3 animate-spin inline" /> : "Salvează"}
              </button>
              {building && (
                <button onClick={() => { setEditing(false); setForm(buildingToForm(building)); }}
                  className="px-3 py-2 rounded-full text-xs font-bold text-slate-600 border-2 border-slate-200">
                  Renunță
                </button>
              )}
              <span className="ml-auto text-[9px] text-slate-400">Salvarea nu marchează automat contextul ca „verificat”.</span>
            </div>
          </div>
        )}

        {!building && !editing && (
          <div className="mt-3 text-[11px] text-slate-500">
            Nicio informație despre clădire înregistrată încă. Adaugă context pentru a corela apartamentul cu clădirea.
          </div>
        )}
      </div>

      {/* Building Neighbours — a doua axă: 1 building → N properties */}
      {building && neighbours && (
        <div className="rounded-2xl border border-slate-100 bg-white p-4" data-testid="ptr-neighbours-card">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-slate-500 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-black text-slate-900">Vecinătatea clădirii</div>
              <div className="text-[10px] text-slate-400">
                {neighbours.total === 0
                  ? "Nicio altă unitate din bloc înregistrată pe PropManage."
                  : `${neighbours.total} ${neighbours.total === 1 ? "unitate conectată" : "unități conectate"}`}
              </div>
            </div>
            {building.verification_status === "verified" && (
              <span className="px-2 py-0.5 rounded-full text-[9px] font-black bg-emerald-50 text-emerald-700"
                data-testid="ptr-neighbours-shared-badge">
                Context comun verificat
              </span>
            )}
          </div>
          {neighbours.neighbours.length > 0 && (
            <ul className="mt-3 space-y-1.5" data-testid="ptr-neighbours-list">
              {neighbours.neighbours.slice(0, 6).map(n => (
                <li key={n.id} className="flex items-center gap-2 text-[11px]" data-testid={`ptr-neighbour-${n.id}`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-400 shrink-0" />
                  <span className="font-bold text-slate-700 flex-1">{n.name || "Unitate"}</span>
                  <span className="text-slate-500">{n.type || "—"}{n.rooms ? ` · ${n.rooms} cam` : ""}{n.surface ? ` · ${n.surface} mp` : ""}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Attach existing building (nu pentru cazul în care e deja atașat) */}
      {!building && (
        <AttachBuildingSearchBox open={searchOpen} setOpen={setSearchOpen} onAttach={attachExisting} />
      )}

      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-3">
        <div className="flex items-start gap-2 text-[11px] text-slate-500">
          <Info className="w-4 h-4 shrink-0 mt-0.5 text-slate-400" />
          <p>
            Datele externe (ex. HartaBlocuri) rămân drept referință. Nu sunt importate automat și nu devin
            automat verificate. O clădire validată poate fi conectată ulterior mai multor proprietăți.
          </p>
        </div>
      </div>
    </div>
  );
};

const AttachBuildingSearchBox = ({ open, setOpen, onAttach }) => {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [busy, setBusy] = useState(false);
  const search = async () => {
    if (q.trim().length < 2) return;
    setBusy(true);
    try {
      const r = await axios.get(`${API}/buildings/search?q=${encodeURIComponent(q)}`);
      setResults(r.data.buildings || []);
    } catch { setResults([]); }
    finally { setBusy(false); }
  };
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-4" data-testid="ptr-attach-building">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-2 text-left"
        data-testid="ptr-attach-toggle">
        <LinkIcon className="w-4 h-4 text-slate-500" />
        <span className="text-sm font-black text-slate-900 flex-1">Conectează la o clădire existentă</span>
        {open ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>
      {open && (
        <div className="mt-3 space-y-2">
          <div className="flex items-center gap-2">
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Caută după nume sau adresă"
              onKeyDown={e => e.key === "Enter" && search()}
              data-testid="ptr-attach-search-input"
              className="flex-1 px-3 py-2 rounded-lg border border-slate-200 text-[12px] outline-none focus:border-[#34C759]" />
            <button onClick={search} disabled={busy || q.trim().length < 2} data-testid="ptr-attach-search-btn"
              className="px-3 py-2 rounded-full text-xs font-black text-black disabled:opacity-50" style={{ background: "#d4ff3a" }}>
              <Search className="w-3.5 h-3.5" />
            </button>
          </div>
          {results.length > 0 ? (
            <ul className="space-y-1.5" data-testid="ptr-attach-results">
              {results.map(b => (
                <li key={b.id} className="rounded-lg border border-slate-100 p-2.5" data-testid={`ptr-attach-result-${b.id}`}>
                  <div className="text-[11px] font-black text-slate-900">{b.name}</div>
                  <div className="text-[10px] text-slate-500">{b.address}</div>
                  <div className="mt-1 flex items-center gap-2">
                    <VerifBadge status={b.verification_status} />
                    <span className="text-[9px] text-slate-500">{b.units_registered} unități conectate</span>
                    <button onClick={() => onAttach(b)} data-testid={`ptr-attach-do-${b.id}`}
                      className="ml-auto px-2.5 py-1 rounded-full text-[10px] font-black text-black" style={{ background: "#d4ff3a" }}>
                      Conectează
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            q.trim().length >= 2 && !busy && <div className="text-[11px] text-slate-500">Nicio clădire găsită.</div>
          )}
        </div>
      )}
    </div>
  );
};

const buildingToForm = (b) => ({
  name: b?.name || "",
  address: b?.address || "",
  construction_year: b?.construction_year || "",
  building_type: b?.building_type || "",
  number_of_units: b?.number_of_units || "",
  floors: b?.floors || "",
  source_type: b?.source_type || "",
  source_name: b?.source_name || "",
  source_reference: b?.source_reference || "",
});

const cleanPayload = (o) => {
  const out = {};
  Object.entries(o).forEach(([k, v]) => {
    if (v === "" || v === null || v === undefined) return;
    if (["construction_year", "number_of_units", "floors"].includes(k)) {
      const n = parseInt(v, 10);
      if (!Number.isNaN(n)) out[k] = n;
    } else out[k] = v;
  });
  return out;
};

// ─────────────────────────────────────────────────────────────────────────────
// REGULATORY DIAGNOSTICS (C)
// ─────────────────────────────────────────────────────────────────────────────
const DiagnosticsSection = ({ propId, vocab, initial, viewer, onChanged }) => {
  const [items, setItems] = useState(initial?.items || []);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyDiagForm(vocab));
  const [busy, setBusy] = useState(false);
  const [docs, setDocs] = useState([]);
  const [verifyModal, setVerifyModal] = useState(null); // {id, mode: 'verify'|'reject'}
  const [verifyNotes, setVerifyNotes] = useState("");

  useEffect(() => { setItems(initial?.items || []); }, [initial]);
  useEffect(() => { setForm(emptyDiagForm(vocab)); }, [vocab]);
  useEffect(() => {
    // Preîncarcă documentele existente pentru picker (o singură dată per proprietate)
    axios.get(`${API}/properties/${propId}/documents-picker`)
      .then(r => setDocs(r.data.documents || []))
      .catch(() => setDocs([]));
  }, [propId]);

  const load = async () => {
    try {
      const r = await axios.get(`${API}/properties/${propId}/diagnostics`);
      setItems(r.data.diagnostics || []);
      onChanged?.();
    } catch { /* silent */ }
  };

  const save = async () => {
    if (!form.diagnostic_type || !form.jurisdiction) {
      alert("Tipul și jurisdicția sunt obligatorii.");
      return;
    }
    setBusy(true);
    try {
      await axios.post(`${API}/properties/${propId}/diagnostics`, cleanPayload(form));
      setShowForm(false);
      setForm(emptyDiagForm(vocab));
      await load();
    } catch (e) {
      alert(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Elimini acest diagnostic?")) return;
    try {
      await axios.delete(`${API}/diagnostics/${id}`);
      await load();
    } catch (e) { alert(formatApiError(e)); }
  };

  const runVerify = async () => {
    if (!verifyModal) return;
    setBusy(true);
    try {
      if (verifyModal.mode === "verify") {
        await axios.post(`${API}/admin/diagnostics/${verifyModal.id}/verify`, { notes: verifyNotes || null });
      } else {
        if (!verifyNotes || verifyNotes.trim().length < 3) {
          alert("Motivul respingerii este obligatoriu (min. 3 caractere).");
          setBusy(false); return;
        }
        await axios.post(`${API}/admin/diagnostics/${verifyModal.id}/reject`, { reason: verifyNotes });
      }
      setVerifyModal(null); setVerifyNotes("");
      await load();
    } catch (e) {
      alert(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="ptr-diagnostics-section" className="space-y-3">
      <div className="rounded-2xl border border-slate-100 bg-white p-4">
        <div className="flex items-center gap-2">
          <div className="flex-1 min-w-0">
            <div className="text-sm font-black text-slate-900">Diagnostice tehnice / reglementare</div>
            <div className="text-[10px] text-slate-400">
              Fiecare diagnostic are jurisdicție proprie (FR, RO, EU, altele). Nu sunt afirmații legale.
            </div>
          </div>
          <button onClick={() => setShowForm(!showForm)} data-testid="ptr-diag-add-btn"
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-[11px] font-black text-black"
            style={{ background: "#d4ff3a" }}>
            <Plus className="w-3.5 h-3.5" /> Adaugă
          </button>
        </div>

        {showForm && (
          <div className="mt-3 rounded-xl bg-slate-50 p-3 space-y-2" data-testid="ptr-diag-form">
            <div className="grid grid-cols-2 gap-2">
              <SelectInput label="Tip diagnostic *" value={form.diagnostic_type}
                onChange={v => setForm({ ...form, diagnostic_type: v })}
                options={vocab?.diagnostic_types || []} testid="ptr-d-type" />
              <SelectInput label="Jurisdicție *" value={form.jurisdiction}
                onChange={v => setForm({ ...form, jurisdiction: v })}
                options={vocab?.jurisdictions || []} testid="ptr-d-jur" />
              <TextInput label="Profesionist" value={form.issuing_professional}
                onChange={v => setForm({ ...form, issuing_professional: v })} testid="ptr-d-prof" />
              <TextInput label="Organizație" value={form.issuing_organization}
                onChange={v => setForm({ ...form, issuing_organization: v })} testid="ptr-d-org" />
              <DateInput label="Data emiterii" value={form.issue_date}
                onChange={v => setForm({ ...form, issue_date: v })} testid="ptr-d-issue" />
              <DateInput label="Valabil până la" value={form.valid_until}
                onChange={v => setForm({ ...form, valid_until: v })} testid="ptr-d-valid" />
              <SelectInput label="Tip sursă" value={form.source_type}
                onChange={v => setForm({ ...form, source_type: v })}
                options={vocab?.source_types || []} testid="ptr-d-src" />
              <TextInput label="Referință sursă" value={form.source_reference}
                onChange={v => setForm({ ...form, source_reference: v })} testid="ptr-d-src-ref" />
            </div>
            {docs.length > 0 && (
              <label className="block" data-testid="ptr-d-doc-picker-wrap">
                <div className="text-[10px] font-bold text-slate-500 mb-0.5 inline-flex items-center gap-1">
                  <Paperclip className="w-3 h-3" /> Atașează document din Cartea Casei
                </div>
                <select value={form.document_ref || ""}
                  onChange={e => setForm({ ...form, document_ref: e.target.value })}
                  data-testid="ptr-d-doc-picker"
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[12px] bg-white outline-none focus:border-[#34C759]">
                  <option value="">— fără document —</option>
                  {docs.map(d => (
                    <option key={d.id} value={d.id}>
                      {d.title || d.filename} · {d.category}{d.verification_status === "verified" ? " ✓" : ""}
                    </option>
                  ))}
                </select>
                <div className="mt-1 text-[9px] text-slate-400">
                  Documentul atașat este obligatoriu pentru ca un admin să poată verifica diagnosticul.
                </div>
              </label>
            )}
            <TextAreaInput label="Concluzii" value={form.findings}
              onChange={v => setForm({ ...form, findings: v })} testid="ptr-d-findings" />
            <TextAreaInput label="Recomandări" value={form.recommendations}
              onChange={v => setForm({ ...form, recommendations: v })} testid="ptr-d-recs" />
            <div className="flex items-center gap-2 pt-1">
              <button onClick={save} disabled={busy} data-testid="ptr-diag-save"
                className="px-4 py-2 rounded-full text-xs font-black text-black disabled:opacity-50" style={{ background: "#d4ff3a" }}>
                {busy ? <Loader2 className="w-3 h-3 animate-spin inline" /> : "Salvează diagnostic"}
              </button>
              <button onClick={() => setShowForm(false)}
                className="px-3 py-2 rounded-full text-xs font-bold text-slate-600 border-2 border-slate-200">
                Renunță
              </button>
              <span className="ml-auto text-[9px] text-slate-400">Va fi salvat ca „Neverificat”.</span>
            </div>
          </div>
        )}

        {items.length === 0 && !showForm && (
          <div className="mt-3 text-[11px] text-slate-500">
            Niciun diagnostic înregistrat. Poți adăuga un DPE, un raport electric sau orice altă evaluare tehnică.
            Fiecare diagnostic rămâne independent de jurisdicție.
          </div>
        )}

        {items.length > 0 && (
          <ul className="mt-3 space-y-2" data-testid="ptr-diag-list">
            {items.map(d => (
              <li key={d.id} data-testid={`ptr-diag-${d.id}`}
                className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[11px] font-black text-slate-900">{d.diagnostic_type_label}</span>
                  <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-white border border-slate-200 text-slate-500"
                    data-testid={`ptr-diag-jur-${d.id}`}>
                    {d.jurisdiction_label}
                  </span>
                  <VerifBadge status={d.verification_status} testid={`ptr-diag-verif-${d.id}`} />
                  <button onClick={() => remove(d.id)} data-testid={`ptr-diag-remove-${d.id}`}
                    className="ml-auto text-slate-400 hover:text-rose-600">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] text-slate-500">
                  {d.issuing_professional && <div><span className="text-slate-400">Profesionist:</span> {d.issuing_professional}</div>}
                  {d.issuing_organization && <div><span className="text-slate-400">Organizație:</span> {d.issuing_organization}</div>}
                  {d.issue_date && <div><span className="text-slate-400">Emis:</span> {d.issue_date}</div>}
                  {d.valid_until && <div><span className="text-slate-400">Valabil până:</span> {d.valid_until}</div>}
                  {d.source_type_label && <div><span className="text-slate-400">Sursă:</span> {d.source_type_label}</div>}
                </div>
                {d.findings && (
                  <div className="mt-1.5 text-[11px] text-slate-700"><span className="text-slate-400">Concluzii:</span> {d.findings}</div>
                )}
                {d.recommendations && (
                  <div className="mt-1 text-[11px] text-slate-700"><span className="text-slate-400">Recomandări:</span> {d.recommendations}</div>
                )}
                {d.source_reference && (
                  <a href={d.source_reference} target="_blank" rel="noreferrer"
                    className="mt-1 inline-flex items-center gap-1 text-[10px] font-bold text-indigo-700 break-all">
                    {d.source_reference} <ExternalLink className="w-3 h-3 shrink-0" />
                  </a>
                )}
                {d.document_snapshot && (
                  <div className="mt-1 inline-flex items-center gap-1 text-[10px] font-bold text-slate-600"
                    data-testid={`ptr-diag-doc-${d.id}`}>
                    <Paperclip className="w-3 h-3" />
                    Document: {d.document_snapshot.title || d.document_snapshot.filename}
                    {" · "}{d.document_snapshot.category}
                  </div>
                )}
                {d.verification_status === "verified" && d.verified_by_name && (
                  <div className="mt-1 text-[10px] text-emerald-700" data-testid={`ptr-diag-verified-by-${d.id}`}>
                    Verificat de {d.verified_by_name} · {formatDate(d.verified_at)}
                    {d.verification_notes && ` — ${d.verification_notes}`}
                  </div>
                )}
                {d.rejection_reason && (
                  <div className="mt-1 text-[10px] text-rose-700" data-testid={`ptr-diag-rejected-${d.id}`}>
                    Respins: {d.rejection_reason}
                  </div>
                )}
                {viewer?.is_verifier && (
                  <div className="mt-2 flex items-center gap-2" data-testid={`ptr-diag-admin-actions-${d.id}`}>
                    {d.verification_status !== "verified" && (
                      <button onClick={() => { setVerifyModal({ id: d.id, mode: "verify" }); setVerifyNotes(""); }}
                        data-testid={`ptr-diag-verify-btn-${d.id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-black bg-emerald-600 text-white">
                        <ShieldCheck className="w-3 h-3" /> Verifică
                      </button>
                    )}
                    {d.verification_status === "verified" && (
                      <button onClick={() => { setVerifyModal({ id: d.id, mode: "reject" }); setVerifyNotes(""); }}
                        data-testid={`ptr-diag-reject-btn-${d.id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-black bg-rose-600 text-white">
                        <ShieldX className="w-3 h-3" /> Respinge
                      </button>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {verifyModal && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
          data-testid="ptr-verify-modal" onClick={() => setVerifyModal(null)}>
          <div className="bg-white rounded-2xl max-w-md w-full p-5" onClick={e => e.stopPropagation()}>
            <div className="text-sm font-black text-slate-900">
              {verifyModal.mode === "verify" ? "Verifică diagnostic" : "Respinge verificarea"}
            </div>
            <div className="mt-1 text-[11px] text-slate-500">
              {verifyModal.mode === "verify"
                ? "Marchezi acest diagnostic ca verificat. Rămâne o urmă în istoric cu identitatea ta."
                : "Diagnosticul se întoarce la „Neverificat”. Este obligatoriu un motiv scurt."}
            </div>
            <textarea rows={3} value={verifyNotes} onChange={e => setVerifyNotes(e.target.value)}
              placeholder={verifyModal.mode === "verify" ? "Note (opțional)" : "Motiv (obligatoriu)"}
              data-testid="ptr-verify-notes"
              className="mt-3 w-full px-3 py-2 rounded-lg border border-slate-200 text-[12px] outline-none focus:border-[#34C759]" />
            <div className="mt-3 flex items-center gap-2">
              <button onClick={runVerify} disabled={busy} data-testid="ptr-verify-confirm"
                className={`px-4 py-2 rounded-full text-xs font-black text-white disabled:opacity-50 ${verifyModal.mode === "verify" ? "bg-emerald-600" : "bg-rose-600"}`}>
                {busy ? <Loader2 className="w-3 h-3 animate-spin inline" /> : (verifyModal.mode === "verify" ? "Confirmă verificarea" : "Respinge")}
              </button>
              <button onClick={() => setVerifyModal(null)}
                className="px-3 py-2 rounded-full text-xs font-bold text-slate-600 border-2 border-slate-200">
                Renunță
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-3">
        <div className="flex items-start gap-2 text-[11px] text-slate-500">
          <Info className="w-4 h-4 shrink-0 mt-0.5 text-slate-400" />
          <p>
            Aceste categorii sunt un container general de diagnostice. Nu implică obligativitate legală
            într-o jurisdicție anume. Un diagnostic devine „Verificat” doar în urma unei validări explicite.
          </p>
        </div>
      </div>
    </div>
  );
};

const emptyDiagForm = () => ({
  diagnostic_type: "", jurisdiction: "", issuing_professional: "", issuing_organization: "",
  issue_date: "", valid_until: "", findings: "", recommendations: "",
  source_type: "", source_reference: "",
});

// ─────────────────────────────────────────────────────────────────────────────
// SYSTEMS / DOCUMENTS / HISTORY — REUTILIZARE (rezumate + linkuri către modul principal)
// ─────────────────────────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────
const SystemsSection = ({ propId, coreStats }) => {
  const [data, setData] = useState(null);
  useEffect(() => {
    axios.get(`${API}/properties/${propId}/assets`).then(r => setData(r.data)).catch(() => setData({ slots: [] }));
  }, [propId]);
  if (!data) return <div className="text-[11px] text-slate-400">Se încarcă...</div>;
  const slots = data.slots || [];
  return (
    <div data-testid="ptr-systems-section" className="rounded-2xl border border-slate-100 bg-white p-4">
      <div className="text-sm font-black text-slate-900">Sisteme tehnice</div>
      <div className="text-[10px] text-slate-400">Echipamente majore înregistrate ({coreStats?.assets_active ?? 0} active).</div>
      {slots.length === 0 ? (
        <div className="mt-3 text-[11px] text-slate-500">Niciun sistem înregistrat încă.</div>
      ) : (
        <ul className="mt-3 space-y-1.5" data-testid="ptr-systems-list">
          {slots.map(s => (
            <li key={s.asset_type} className="flex items-center gap-2 text-[11px]" data-testid={`ptr-system-${s.asset_type}`}>
              <span className="w-1.5 h-1.5 rounded-full bg-[#166534] shrink-0" />
              <span className="font-bold text-slate-700 flex-1">{s.label}</span>
              {s.asset ? (
                <span className="text-slate-500">
                  {s.asset.installed_year || "an necunoscut"} · <VerifBadge status={s.asset.confidence === "verified" ? "verified" : "declared"} />
                </span>
              ) : <span className="text-slate-300">nedeclarat</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

const DocumentsSection = ({ coreStats }) => {
  const by = coreStats?.documents_by_category || {};
  const entries = Object.entries(by);
  return (
    <div data-testid="ptr-documents-section" className="rounded-2xl border border-slate-100 bg-white p-4">
      <div className="text-sm font-black text-slate-900">Documente & Evidență</div>
      <div className="text-[10px] text-slate-400">
        {coreStats?.documents ?? 0} documente ({coreStats?.documents_verified ?? 0} verificate). Documentele complete se gestionează în secțiunea „Cartea Casei”.
      </div>
      {entries.length === 0 ? (
        <div className="mt-3 text-[11px] text-slate-500">Nicio evidență încă.</div>
      ) : (
        <ul className="mt-3 space-y-1" data-testid="ptr-documents-list">
          {entries.map(([cat, count]) => (
            <li key={cat} className="flex items-center gap-2 text-[11px]" data-testid={`ptr-doc-cat-${cat}`}>
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400 shrink-0" />
              <span className="font-bold text-slate-700 flex-1">{cat.replace(/_/g, " ")}</span>
              <span className="text-slate-500">{count}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

const HistorySection = ({ propId, coreStats }) => {
  const [events, setEvents] = useState(null);
  useEffect(() => {
    axios.get(`${API}/properties/${propId}/timeline`).then(r => setEvents(r.data.events || [])).catch(() => setEvents([]));
  }, [propId]);
  return (
    <div data-testid="ptr-history-section" className="rounded-2xl border border-slate-100 bg-white p-4">
      <div className="text-sm font-black text-slate-900">Istoric intervenții & evenimente</div>
      <div className="text-[10px] text-slate-400">
        {coreStats?.requests ?? 0} cereri · {coreStats?.events ?? 0} evenimente.
      </div>
      {events === null ? (
        <div className="mt-3 text-[11px] text-slate-400">Se încarcă...</div>
      ) : events.length === 0 ? (
        <div className="mt-3 text-[11px] text-slate-500">Nicio activitate înregistrată.</div>
      ) : (
        <ul className="mt-3 space-y-1.5 max-h-64 overflow-y-auto" data-testid="ptr-history-list">
          {events.slice(0, 15).map((e, i) => (
            <li key={i} className="flex items-start gap-2 text-[11px]" data-testid={`ptr-history-item-${i}`}>
              <span className="mt-1 w-1.5 h-1.5 rounded-full bg-slate-400 shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="font-bold text-slate-700 truncate">{e.title || e.type}</div>
                {e.description && <div className="text-[10px] text-slate-400 truncate">{e.description}</div>}
              </div>
              <div className="text-[9px] text-slate-400 shrink-0">{formatDate(e.timestamp)}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

const formatDate = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleDateString("ro-RO", { day: "2-digit", month: "short", year: "2-digit" }); }
  catch { return iso; }
};

// ─────────────────────────────────────────────────────────────────────────────
// TRANSACTION READINESS
// ─────────────────────────────────────────────────────────────────────────────
const ReadinessSection = ({ readiness, propId }) => {
  if (!readiness) return null;
  const downloadPdf = () => {
    const url = `${API}/properties/${propId}/transaction-readiness.pdf`;
    window.open(url, "_blank");
  };
  return (
    <div data-testid="ptr-readiness-section" className="space-y-3">
      <div className="rounded-2xl border border-slate-100 bg-white p-4">
        <div className="flex items-center gap-2">
          <div className="flex-1 min-w-0">
            <div className="text-sm font-black text-slate-900">Pregătire tranzacție</div>
            <div className="text-[10px] text-slate-400">Cât de bine este documentată această proprietate.</div>
          </div>
          <button onClick={downloadPdf} data-testid="ptr-readiness-pdf-btn"
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border-2 border-slate-200 text-[10px] font-bold text-slate-700 hover:bg-slate-50">
            <Download className="w-3 h-3" /> PDF
          </button>
          <StatusBadge status={readiness.overall_status} testid="ptr-readiness-overall" />
        </div>
        <ul className="mt-3 space-y-1.5" data-testid="ptr-readiness-criteria">
          {(readiness.criteria || []).map(c => (
            <li key={c.id} className="flex items-center gap-2 py-1" data-testid={`ptr-crit-${c.id}`}>
              <div className="flex-1 min-w-0">
                <div className="text-[11px] font-bold text-slate-700">{c.label}</div>
                <div className="text-[9px] text-slate-400">{c.detail}</div>
              </div>
              <StatusBadge status={c.status} testid={`ptr-crit-status-${c.id}`} />
            </li>
          ))}
        </ul>
      </div>
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-3">
        <div className="flex items-start gap-2 text-[11px] text-slate-500">
          <Info className="w-4 h-4 shrink-0 mt-0.5 text-slate-400" />
          <p>{readiness.disclaimer}</p>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// FORM PRIMITIVES
// ─────────────────────────────────────────────────────────────────────────────
const TextInput = ({ label, value, onChange, testid, placeholder }) => (
  <label className="block">
    <div className="text-[10px] font-bold text-slate-500 mb-0.5">{label}</div>
    <input value={value ?? ""} onChange={e => onChange(e.target.value)} data-testid={testid} placeholder={placeholder}
      className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[12px] outline-none focus:border-[#34C759]" />
  </label>
);
const NumberInput = ({ label, value, onChange, testid }) => (
  <label className="block">
    <div className="text-[10px] font-bold text-slate-500 mb-0.5">{label}</div>
    <input type="number" value={value ?? ""} onChange={e => onChange(e.target.value)} data-testid={testid}
      className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[12px] outline-none focus:border-[#34C759]" />
  </label>
);
const DateInput = ({ label, value, onChange, testid }) => (
  <label className="block">
    <div className="text-[10px] font-bold text-slate-500 mb-0.5">{label}</div>
    <input type="date" value={value ?? ""} onChange={e => onChange(e.target.value)} data-testid={testid}
      className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[12px] outline-none focus:border-[#34C759]" />
  </label>
);
const SelectInput = ({ label, value, onChange, options, testid }) => (
  <label className="block">
    <div className="text-[10px] font-bold text-slate-500 mb-0.5">{label}</div>
    <select value={value ?? ""} onChange={e => onChange(e.target.value)} data-testid={testid}
      className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[12px] bg-white outline-none focus:border-[#34C759]">
      <option value="">—</option>
      {options.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
    </select>
  </label>
);
const TextAreaInput = ({ label, value, onChange, testid }) => (
  <label className="block">
    <div className="text-[10px] font-bold text-slate-500 mb-0.5">{label}</div>
    <textarea rows={2} value={value ?? ""} onChange={e => onChange(e.target.value)} data-testid={testid}
      className="w-full px-3 py-2 rounded-lg border border-slate-200 text-[12px] outline-none focus:border-[#34C759]" />
  </label>
);
const FieldRow = ({ label, value }) => (
  <div className="text-[11px]">
    <div className="text-slate-400">{label}</div>
    <div className="font-bold text-slate-800">{value ?? "—"}</div>
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export const PropertyTechnicalRecord = ({ propId }) => {
  const [record, setRecord] = useState(null);
  const [vocab, setVocab] = useState(null);
  const [active, setActive] = useState("core");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // Pe mobil folosim expand/collapse pentru fiecare secțiune (mai puțin overhead de navigare).
  const [openMobile, setOpenMobile] = useState({ core: true });

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const [rec, voc] = await Promise.all([
        axios.get(`${API}/properties/${propId}/technical-record`),
        vocab ? Promise.resolve({ data: vocab }) : axios.get(`${API}/technical-record/vocabulary`),
      ]);
      setRecord(rec.data);
      if (!vocab) setVocab(voc.data);
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [propId]);

  const header = record?.header;
  const coreStats = record?.property_core?.stats;

  const toggle = (id) => setOpenMobile(o => ({ ...o, [id]: !o[id] }));

  const renderSection = (id) => {
    switch (id) {
      case "core":
        return <PropertyCoreSection core={record?.property_core} />;
      case "building":
        return <BuildingContextSection propId={propId} vocab={vocab} initial={record?.building_context} viewer={record?.viewer} onSaved={load} />;
      case "diagnostics":
        return <DiagnosticsSection propId={propId} vocab={vocab} initial={record?.regulatory_diagnostics} viewer={record?.viewer} onChanged={load} />;
      case "systems":
        return <SystemsSection propId={propId} coreStats={coreStats} />;
      case "documents":
        return <DocumentsSection coreStats={coreStats} />;
      case "history":
        return <HistorySection propId={propId} coreStats={coreStats} />;
      case "readiness":
        return <ReadinessSection readiness={record?.transaction_readiness} propId={propId} />;
      default:
        return null;
    }
  };

  if (loading && !record) {
    return (
      <div className="mt-4 rounded-2xl border border-slate-100 bg-white p-6 text-center text-[11px] text-slate-400"
        data-testid="ptr-loading">
        <Loader2 className="w-4 h-4 animate-spin inline mr-1" /> Se încarcă dosarul tehnic...
      </div>
    );
  }
  if (error) {
    return (
      <div className="mt-4 rounded-2xl border border-rose-100 bg-rose-50 p-4 text-[11px] text-rose-700"
        data-testid="ptr-error">
        Eroare: {error}
      </div>
    );
  }

  return (
    <div data-testid="property-technical-record" className="mt-4">
      {/* Header */}
      <div className="rounded-3xl border border-slate-100 bg-white shadow-sm p-4">
        <div className="flex items-start gap-3">
          <span className="w-10 h-10 rounded-xl bg-slate-900 flex items-center justify-center shrink-0">
            <ClipboardList className="text-[#ccff00] w-5 h-5" />
          </span>
          <div className="flex-1 min-w-0">
            <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">Dosar Tehnic</div>
            <div className="mt-0.5 text-lg font-black text-slate-900 leading-tight" data-testid="ptr-header-name">{header?.property_name}</div>
            {header?.property_address && (
              <div className="text-[11px] text-slate-500" data-testid="ptr-header-address">{header.property_address}</div>
            )}
          </div>
          <StatusBadge status={header?.overall_status} testid="ptr-header-status" />
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2">
          <SummaryTile label="Documente" value={header?.documents_count ?? 0} sub={`${header?.documents_verified ?? 0} verificate`} />
          <SummaryTile label="Ultima actualizare" value={formatDate(header?.last_updated)} sub="documente" />
          <SummaryTile label="Diagnostice" value={record?.regulatory_diagnostics?.total ?? 0} sub={buildJurLabel(record?.regulatory_diagnostics?.by_jurisdiction)} />
        </div>
      </div>

      {/* Desktop tabs / Mobile accordion */}
      <div className="mt-4 lg:grid lg:grid-cols-12 lg:gap-4">
        {/* Desktop nav */}
        <nav className="hidden lg:block lg:col-span-3 lg:sticky lg:top-4 space-y-1 h-fit" data-testid="ptr-nav">
          {SECTION_DEFS.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setActive(id)} data-testid={`ptr-nav-${id}`}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-[12px] font-bold text-left transition-colors ${active === id ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-100"}`}>
              <Icon className="w-4 h-4 shrink-0" /> {label}
            </button>
          ))}
        </nav>

        {/* Desktop: doar secțiunea activă */}
        <div className="hidden lg:block lg:col-span-9 min-w-0">{renderSection(active)}</div>

        {/* Mobile: acordeon */}
        <div className="lg:hidden mt-2 space-y-2">
          {SECTION_DEFS.map(({ id, label, icon: Icon }) => (
            <div key={id} className="rounded-2xl border border-slate-100 bg-white overflow-hidden">
              <button onClick={() => toggle(id)} data-testid={`ptr-mobile-toggle-${id}`}
                className="w-full flex items-center gap-2 px-4 py-3 text-left">
                <Icon className="w-4 h-4 text-slate-500" />
                <span className="text-[12px] font-black text-slate-900 flex-1">{label}</span>
                {openMobile[id] ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
              </button>
              {openMobile[id] && <div className="px-3 pb-3" data-testid={`ptr-mobile-content-${id}`}>{renderSection(id)}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const buildJurLabel = (byJur) => {
  if (!byJur) return "—";
  const keys = Object.keys(byJur);
  if (!keys.length) return "—";
  return keys.map(k => `${k}:${byJur[k]}`).join(" · ");
};

export default PropertyTechnicalRecord;
