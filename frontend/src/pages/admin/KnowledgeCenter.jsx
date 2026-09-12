// Enterprise Knowledge Center — IDE mode (EO-002 R5): stânga categorii · centru documente ·
// dreapta inspector; jos timeline. Lifecycle (R2/R3), Health Score (R4), Review Mode (R7).
import React, { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import {
  BookOpenCheck, Loader2, Search, Network, FileText, ShieldAlert, X, RefreshCcw, ClipboardCheck, Clock, Compass,
} from "lucide-react";
import { RegistryGraph, STATUS_STYLE, TYPE_META } from "../../components/founder/RegistryGraph";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

// Enterprise Query Assistant — operator config (client-side only, zero backend contract touched)
const QUERY_OPERATORS = ["artifact", "status", "category"];
const STATUS_VALUES = ["Active", "Review", "Draft", "Archived"]; // spec: exact 4 statuses shown as suggestions

// Regex helpers: quoted values captured with surrounding quotes; unquoted are non-space runs.
// Position-agnostic (start/middle/end), whitespace-tolerant, case-insensitive.
const TOKEN_REGEX = (op) => new RegExp(`(?:^|\\s)${op}:("[^"]+"|\\S+)(?=\\s|$)`, "i");

const LIFECYCLE_STYLE = {
  Active: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
  Approved: "bg-lime-500/10 border-lime-500/30 text-lime-300",
  Review: "bg-sky-500/10 border-sky-500/30 text-sky-300",
  Draft: "bg-amber-500/10 border-amber-500/30 text-amber-300",
  Superseded: "bg-stone-500/10 border-stone-500/30 text-stone-400",
  Archived: "bg-stone-500/10 border-stone-500/30 text-stone-400",
  Deprecated: "bg-red-500/10 border-red-500/30 text-red-300",
};
const StatusBadge = ({ s }) => (
  <span className={`text-[9px] px-2 py-0.5 rounded-full border shrink-0 uppercase ${LIFECYCLE_STYLE[s] || LIFECYCLE_STYLE.Review}`}>{s}</span>
);

// Registry-specific client-side parser (no backend contract touched).
// Extracts structured metadata from the markdown body of a REGISTRY artifact.
const parseRegistryMeta = (md) => {
  if (!md) return null;
  const readLabel = (label) => {
    const m = md.match(new RegExp(`\\*\\*${label}\\*\\*:\\s*(.+?)$`, "im"));
    return m ? m[1].trim() : null;
  };
  // Count Entries table rows: locate the "## Entries" section then count non-separator table rows.
  let entries = 0;
  const sections = md.split(/^##\s+/im);
  const entriesSection = sections.find(s => /^Entries\b/i.test(s));
  if (entriesSection) {
    const rows = entriesSection.split("\n").filter(l => /^\s*\|.+\|\s*$/.test(l) && !/^\s*\|(\s*[-:]+\s*\|)+\s*$/.test(l));
    // rows[0] is the header row; data rows = rest
    entries = Math.max(0, rows.length - 1);
  }
  return {
    owner: readLabel("Owner"),
    lastReview: readLabel("Last Review"),
    schema: readLabel("Schema"),
    purpose: readLabel("Purpose"),
    entries,
  };
};

// Enterprise Artifact Type badges (UI extension — infrastructure already exposed by backend).
// Contract descriptions loaded from /api/founder/knowledge/artifact-types.
const ARTIFACT_TYPE_STYLE = {
  DOCUMENT: "bg-stone-500/10 border-stone-500/30 text-stone-300",
  REGISTRY: "bg-indigo-500/10 border-indigo-500/30 text-indigo-300",
  GRAPH:    "bg-violet-500/10 border-violet-500/30 text-violet-300",
  LEDGER:   "bg-amber-500/10 border-amber-500/30 text-amber-300",
  INDEX:    "bg-cyan-500/10 border-cyan-500/30 text-cyan-300",
  CATALOG:  "bg-rose-500/10 border-rose-500/30 text-rose-300",
};
const ARTIFACT_TYPE_LABEL = {
  DOCUMENT: "Documents", REGISTRY: "Registries", GRAPH: "Graphs",
  LEDGER: "Ledgers", INDEX: "Indexes", CATALOG: "Catalogs",
};
const ARTIFACT_TYPE_SINGULAR = {
  DOCUMENT: "Document", REGISTRY: "Registry", GRAPH: "Graph",
  LEDGER: "Ledger", INDEX: "Index", CATALOG: "Catalog",
};
const ArtifactBadge = ({ type, contract, className = "" }) => {
  const t = (type || "DOCUMENT").toUpperCase();
  const desc = contract?.[t];
  return (
    <span
      className={`text-[9px] px-2 py-0.5 rounded-full border shrink-0 uppercase font-mono tracking-wide ${ARTIFACT_TYPE_STYLE[t] || ARTIFACT_TYPE_STYLE.DOCUMENT} ${className}`}
      title={desc ? `${t}\n${desc}` : t}
      aria-label={desc ? `Artifact Type ${t}. ${desc}` : `Artifact Type ${t}`}
      data-testid={`kc-artifact-badge-${t}`}
    >{t}</span>
  );
};

const MD = {
  h1: (p) => <h1 className="text-xl font-serif text-white mt-2 mb-3 pb-2 border-b border-white/10" {...p} />,
  h2: (p) => <h2 className="text-base font-serif text-[#d4ff3a] mt-5 mb-2" {...p} />,
  h3: (p) => <h3 className="text-sm font-semibold text-white mt-4 mb-1.5" {...p} />,
  p: (p) => <p className="text-sm text-stone-300 leading-relaxed my-2" {...p} />,
  ul: (p) => <ul className="list-disc ml-5 text-sm text-stone-300 my-2 space-y-1" {...p} />,
  ol: (p) => <ol className="list-decimal ml-5 text-sm text-stone-300 my-2 space-y-1" {...p} />,
  a: (p) => <a className="text-[#d4ff3a] underline" {...p} />,
  code: ({ inline, ...p }) => inline
    ? <code className="bg-white/10 text-[#d4ff3a] px-1.5 py-0.5 rounded text-[12px] font-mono" {...p} />
    : <code className="block bg-black/40 text-emerald-200 p-3 rounded-lg text-[12px] font-mono overflow-x-auto my-2 border border-white/5" {...p} />,
  blockquote: (p) => <blockquote className="border-l-4 border-[#d4ff3a]/40 bg-[#d4ff3a]/5 pl-4 py-2 my-3 text-sm text-stone-200 italic" {...p} />,
  table: (p) => <div className="my-3 overflow-x-auto"><table className="min-w-full text-xs border border-white/10" {...p} /></div>,
  th: (p) => <th className="px-3 py-2 text-left text-stone-200 font-semibold border-b border-white/10 bg-white/[0.04]" {...p} />,
  td: (p) => <td className="px-3 py-2 text-stone-300 border-b border-white/5" {...p} />,
  strong: (p) => <strong className="text-white font-semibold" {...p} />,
  hr: (p) => <hr className="border-white/10 my-5" {...p} />,
};

const HealthBar = ({ label, value, max }) => (
  <div className="flex items-center gap-2 text-[10px]">
    <span className="w-24 text-stone-500">{label}</span>
    <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
      <div className="h-full rounded-full" style={{ width: `${max ? (value / max) * 100 : 0}%`, background: value / max >= 0.8 ? "#34d399" : value / max >= 0.4 ? "#fbbf24" : "#ef4444" }} />
    </div>
    <span className="w-10 text-right text-stone-400">{value}/{max}</span>
  </div>
);

const RelationRow = ({ r, onOpen }) => (
  <button onClick={() => r.other_ref?.startsWith("memory/") || r.other_ref?.startsWith("docs/") ? onOpen(r.other_ref) : null}
    className="w-full text-left text-xs bg-white/[0.02] border border-white/10 rounded-lg px-3 py-2 hover:border-[#d4ff3a]/30"
    data-testid={`kc-rel-${r.id}`}>
    <div className="flex items-center gap-2 flex-wrap">
      <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${STATUS_STYLE[r.verification_status] || STATUS_STYLE.UNKNOWN}`}>{r.verification_status}</span>
      <span style={{ color: TYPE_META[r.other_type]?.color }}>{r.other_name}</span>
      <span className="text-stone-500">· {r.type}</span>
    </div>
    <div className="text-[10px] text-stone-500 mt-1">Evidență: {r.evidence} · Confidence: {r.confidence}</div>
  </button>
);

// R5: Inspectorul din dreapta (meta + health + gate + relații + preview)
const InspectorPane = ({ path, onOpen, contract }) => {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    setData(null); setErr(null);
    if (!path) return;
    ax.get(`/api/founder/knowledge/doc`, { params: { path } })
      .then(r => setData(r.data)).catch(e => setErr(e?.response?.data?.detail || "Eroare"));
  }, [path]);
  if (!path) return (
    <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-6 text-xs text-stone-500 h-fit" data-testid="kc-inspector-empty">
      Selectează un document: Inspectorul arată statusul de lifecycle, Health Score, Quality Gate, relațiile dovedite și conținutul.
    </div>
  );
  const m = data?.meta;
  const h = m?.health;
  return (
    <div className="bg-[#0e0e10] border border-white/10 rounded-2xl overflow-hidden" data-testid="kc-inspector">
      {err && <div className="text-red-300 text-sm p-5">{err}</div>}
      {!data && !err && <div className="flex items-center gap-2 text-stone-400 text-sm p-5"><Loader2 className="w-4 h-4 animate-spin" /> Se încarcă...</div>}
      {data && (
        <>
          <div className="p-5 border-b border-white/10">
            <div className="flex items-start justify-between gap-2">
              <div className="font-serif text-lg text-white leading-snug" data-testid="kc-doc-title">{m.title}</div>
              <div className="flex items-center gap-1.5 shrink-0">
                <ArtifactBadge type={m.artifact_type} contract={contract} />
                <StatusBadge s={m.status} />
              </div>
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-stone-400 mt-2" data-testid="kc-doc-meta">
              <span>v{m.version}</span>
              <span>{m.author}</span>
              {m.approver && <span>Aprobat: {m.approver} · {String(m.approved_at).slice(0, 10)}</span>}
              <span>{m.category}</span>
              <span className="font-mono text-[10px] text-stone-500 break-all">{m.path}</span>
            </div>
            <div className="mt-3 space-y-1" data-testid="kc-doc-health">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-stone-400">Document Health</span>
                <span className="font-serif text-base" style={{ color: h.score >= 80 ? "#34d399" : h.score >= 40 ? "#fbbf24" : "#ef4444" }}>{h.score}%</span>
              </div>
              <HealthBar label="Referit de OS" value={h.referenced} max={35} />
              <HealthBar label="Implementare" value={h.implementation} max={25} />
              <HealthBar label="Evidență" value={h.evidence} max={20} />
              <HealthBar label="Completitudine" value={h.completeness} max={20} />
              <div className="text-[10px] text-stone-500">Confidence: {h.confidence} · Quality Gate: <span className={data.gate.passed ? "text-emerald-300" : "text-amber-300"}>{data.gate.passed ? "PASSED" : `REVIEW (${(data.gate.critical_failed || []).join(", ")})`}</span> · Quality {data.gate.quality_score}%</div>
            </div>
          </div>
          {m.artifact_type === "REGISTRY" && (() => {
            const meta = parseRegistryMeta(data.content);
            if (!meta) return null;
            const schemaFields = meta.schema ? meta.schema.split(/\s*[·|,]\s*/).filter(Boolean) : [];
            return (
              <div className="p-5 border-b border-white/10 bg-indigo-500/[0.03]" data-testid="kc-registry-details">
                <div className="text-[10px] uppercase tracking-widest text-indigo-300/80 mb-2 flex items-center gap-1.5">
                  <Network className="w-3 h-3" /> Registry Details
                </div>
                <div className="grid grid-cols-2 gap-3 text-[11px]">
                  <div>
                    <div className="text-stone-500 text-[10px] uppercase">Entries</div>
                    <div className="text-white font-mono text-lg" data-testid="kc-registry-entries">{meta.entries}</div>
                  </div>
                  <div>
                    <div className="text-stone-500 text-[10px] uppercase">Last Review</div>
                    <div className="text-stone-200 font-mono" data-testid="kc-registry-last-review">{meta.lastReview || "—"}</div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-stone-500 text-[10px] uppercase">Owner</div>
                    <div className="text-stone-200" data-testid="kc-registry-owner">{meta.owner || "—"}</div>
                  </div>
                  {schemaFields.length > 0 && (
                    <div className="col-span-2">
                      <div className="text-stone-500 text-[10px] uppercase mb-1">Schema</div>
                      <div className="flex flex-wrap gap-1" data-testid="kc-registry-schema">
                        {schemaFields.map(f => (
                          <span key={f} className="text-[10px] px-1.5 py-0.5 rounded border border-indigo-500/30 bg-indigo-500/5 text-indigo-200 font-mono">{f}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })()}
          {(data.relationships?.depends_on?.length > 0 || data.relationships?.used_by?.length > 0) && (
            <div className="p-5 border-b border-white/10 space-y-3" data-testid="kc-doc-relationships">
              <div>
                <div className="text-[10px] uppercase tracking-wide text-stone-500 mb-1.5">Depinde de / Guvernat de</div>
                <div className="space-y-1.5">{data.relationships.depends_on.map(r => <RelationRow key={r.id} r={r} onOpen={onOpen} />)}
                  {!data.relationships.depends_on.length && <div className="text-xs text-stone-600">—</div>}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wide text-stone-500 mb-1.5">Folosit de / Influențează</div>
                <div className="space-y-1.5">{data.relationships.used_by.map(r => <RelationRow key={r.id} r={r} onOpen={onOpen} />)}
                  {!data.relationships.used_by.length && <div className="text-xs text-stone-600">—</div>}</div>
              </div>
            </div>
          )}
          {data.relationships?.note && <div className="mx-5 mt-4 text-[11px] text-stone-500 border border-white/10 rounded-lg px-3 py-2">{data.relationships.note}</div>}
          <div className="p-5 max-h-[52vh] overflow-y-auto" data-testid="kc-doc-content">
            <ReactMarkdown components={MD}>{data.content}</ReactMarkdown>
          </div>
        </>
      )}
    </div>
  );
};

// R7: Founder Review Mode
const ReviewPane = ({ onOpen }) => {
  const [r, setR] = useState(null);
  useEffect(() => { ax.get(`/api/founder/knowledge/review`).then(res => setR(res.data)).catch(() => {}); }, []);
  if (!r) return <div className="flex items-center gap-2 text-stone-400 text-sm p-6"><Loader2 className="w-4 h-4 animate-spin" /> Se generează Founder Review...</div>;
  const Section = ({ title, docs, tone = "text-stone-300" }) => (
    <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-4">
      <div className={`text-xs font-semibold mb-2 ${tone}`}>{title} <span className="text-stone-500">({docs.length})</span></div>
      <div className="space-y-1 max-h-56 overflow-y-auto">
        {docs.length === 0 && <div className="text-[11px] text-stone-600">Nimic — curat.</div>}
        {docs.map(d => (
          <button key={d.path} onClick={() => onOpen(d.path)} className="w-full text-left text-[11px] bg-white/[0.02] border border-white/10 rounded-lg px-2.5 py-1.5 hover:border-[#d4ff3a]/30 flex items-center gap-2">
            <span className="truncate flex-1 text-stone-300">{d.title}</span>
            {d.quality != null && <span className="text-stone-500">{d.quality}%</span>}
            <StatusBadge s={d.status} />
          </button>
        ))}
      </div>
    </div>
  );
  return (
    <div className="space-y-4" data-testid="kc-review">
      <div className="bg-[#0e0e10] border border-[#d4ff3a]/20 rounded-2xl p-4">
        <div className="text-xs font-semibold text-[#d4ff3a] mb-2 flex items-center gap-1.5"><ClipboardCheck className="w-3.5 h-3.5" /> Priorități (Founder Review)</div>
        <div className="flex flex-wrap gap-2" data-testid="kc-review-priorities">
          {r.top_priorities.length === 0 && <span className="text-[11px] text-stone-500">Nicio acțiune urgentă.</span>}
          {r.top_priorities.map((p, i) => <span key={i} className="text-[11px] px-2.5 py-1 rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-300">{p.action} · {p.count}</span>)}
        </div>
        {r.broken_relations.length > 0 && (
          <div className="mt-2 text-[11px] text-red-300">Relații rupte (evidența a dispărut → UNKNOWN): {r.broken_relations.map(n => n.name).join(", ")}</div>
        )}
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <Section title="În așteptarea textului verbatim" docs={r.pending_verbatim} tone="text-amber-300" />
        <Section title="Draft-uri (strategii neactivate)" docs={r.drafts} tone="text-amber-300" />
        <Section title="Necesită review (nereferite de OS)" docs={r.needs_review} tone="text-sky-300" />
        <Section title="Duplicate (titluri identice)" docs={r.duplicates} tone="text-red-300" />
        <Section title="Sugestii de activare (quality ≥60%)" docs={r.activation_suggestions} tone="text-emerald-300" />
        <Section title="Sugestii de curățenie" docs={r.cleanup_suggestions} tone="text-stone-300" />
      </div>
    </div>
  );
};

export default function KnowledgeCenter() {
  const location = useLocation();
  const [tree, setTree] = useState(null);
  const [denied, setDenied] = useState(false);
  const [cat, setCat] = useState(null);
  const [tab, setTab] = useState("docs");
  const [openPath, setOpenPath] = useState(null);
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);
  // Artifact Type layer (UI extension of existing infrastructure)
  const [artifactFilter, setArtifactFilter] = useState(null); // null = All | "DOCUMENT" | "REGISTRY" ...
  const [artifactContract, setArtifactContract] = useState(null); // { types, contract, default, note }
  // Enterprise Query Assistant — autocomplete state (frontend only, uses already-loaded data)
  const [sugOpen, setSugOpen] = useState(false);
  const [sugIndex, setSugIndex] = useState(0);
  const [caret, setCaret] = useState(0);
  const inputRef = useRef(null);
  const searchWrapRef = useRef(null);

  const load = useCallback(() => {
    ax.get(`/api/founder/knowledge/tree`)
      .then(r => { setTree(r.data); setDenied(false); })
      .catch(e => { if (e?.response?.status === 403) setDenied(true); });
  }, []);
  useEffect(() => { load(); }, [load]);
  // Load artifact-types contract once (source of truth for tooltip descriptions + type enum)
  useEffect(() => {
    ax.get(`/api/founder/knowledge/artifact-types`)
      .then(r => setArtifactContract(r.data))
      .catch(() => setArtifactContract(null));
  }, []);
  useEffect(() => {
    const doc = new URLSearchParams(location.search).get("doc");
    if (doc) { setOpenPath(doc); setTab("docs"); }
  }, [location.search]);

  const openDoc = (p) => { setOpenPath(p); setTab("docs"); };

  // Search parser — supports `artifact:<TYPE>`, `status:<STATUS>`, `category:<NAME>`
  // Case-insensitive, position-agnostic, tolerates multiple spaces, quoted multi-word values.
  // Backend contract untouched: only free text is sent to /api/founder/knowledge/search.
  const parseTokens = (raw) => {
    const tokens = { artifact: null, status: null, category: null };
    let rest = raw;
    for (const op of QUERY_OPERATORS) {
      const m = rest.match(TOKEN_REGEX(op));
      if (m) {
        // Strip surrounding quotes if present
        tokens[op] = m[1].replace(/^"|"$/g, "");
        rest = rest.replace(m[0], " ").replace(/\s+/g, " ").trim();
      }
    }
    return { tokens, rest };
  };
  // Normalizers so values compare correctly against tree data:
  //  - artifact_type is UPPERCASE in the backend enum
  //  - lifecycle status is Capitalized ("Active", not "ACTIVE") — we normalize case-insensitive
  //  - category is arbitrary string, matched case-insensitive
  const normalizeArtifact = (v) => (v || "").toUpperCase();
  const matchesStatus = (docStatus, tokenValue) => (docStatus || "").toLowerCase() === (tokenValue || "").toLowerCase();
  const matchesCategory = (docCategory, tokenValue) => (docCategory || "").toLowerCase() === (tokenValue || "").toLowerCase();

  const applyClientFilters = (docs, tokens) => {
    return docs.filter(d => {
      if (tokens.artifact && (d.artifact_type || "DOCUMENT") !== normalizeArtifact(tokens.artifact)) return false;
      if (tokens.status && !matchesStatus(d.status, tokens.status)) return false;
      if (tokens.category && !matchesCategory(d.category, tokens.category)) return false;
      return true;
    });
  };

  const anyToken = (tokens) => !!(tokens.artifact || tokens.status || tokens.category);

  const doSearch = async (e) => {
    e?.preventDefault();
    setSugOpen(false);
    const raw = q.trim();
    if (raw.length < 2) return;
    setSearching(true);
    const { tokens, rest } = parseTokens(raw);
    try {
      // If ONLY operator tokens (no free text), list matching docs locally from the loaded tree.
      if (anyToken(tokens) && !rest) {
        const allDocs = (tree?.categories || []).flatMap(c => c.docs);
        const filtered = applyClientFilters(allDocs, tokens);
        setResults({
          query: raw,
          total: filtered.length,
          documents: filtered.map(d => ({ ...d, occurrences: 0, snippet: "" })),
          registry_nodes: [],
          _tokens: tokens,
        });
        return;
      }
      // Otherwise hit the existing backend search endpoint with free text only, then filter client-side by tokens.
      const r = await ax.get(`/api/founder/knowledge/search`, { params: { q: rest || raw } });
      const filteredDocs = anyToken(tokens) ? applyClientFilters(r.data.documents || [], tokens) : (r.data.documents || []);
      setResults({
        ...r.data,
        documents: filteredDocs,
        total: filteredDocs.length,
        _tokens: anyToken(tokens) ? tokens : null,
      });
    }
    catch { /* noop */ } finally { setSearching(false); }
  };

  // ————————————————————————————————————————————————
  // Enterprise Query Assistant — autocomplete engine
  // Uses only already-loaded state: tree.artifact_type_counts, tree.status_counts, tree.categories,
  // artifactContract.contract. Zero extra HTTP requests. Instant.
  // ————————————————————————————————————————————————
  const suggestions = useMemo(() => {
    if (!tree) return [];
    const cp = Math.min(caret, q.length);
    const before = q.slice(0, cp);
    const tokenMatch = before.match(/(\S+)$/);
    const currentToken = tokenMatch ? tokenMatch[1] : "";
    const lower = currentToken.toLowerCase();
    if (!lower) return [];

    const artifactTypesLocal = artifactContract?.types || ["DOCUMENT", "REGISTRY", "GRAPH", "LEDGER", "INDEX", "CATALOG"];
    const artifactCounts = tree.artifact_type_counts || {};
    const statusCounts = tree.status_counts || {};
    const categories = tree.categories || [];
    const items = [];

    if (lower.includes(":")) {
      const [op, valRaw] = lower.split(":");
      const val = valRaw || "";
      if (op === "artifact") {
        artifactTypesLocal.filter(a => a.toLowerCase().startsWith(val)).forEach(a => items.push({
          key: `artifact:${a}`, label: `artifact:${a}`, insert: `artifact:${a}`,
          group: "Artifact Type", meta: `${artifactCounts[a] ?? 0}`, hint: artifactContract?.contract?.[a] || "",
        }));
      } else if (op === "status") {
        STATUS_VALUES.filter(s => s.toLowerCase().startsWith(val)).forEach(s => items.push({
          key: `status:${s}`, label: `status:${s.toUpperCase()}`, insert: `status:${s.toUpperCase()}`,
          group: "Status", meta: `${statusCounts[s] ?? 0}`,
        }));
      } else if (op === "category") {
        categories.filter(c => c.name.toLowerCase().includes(val)).slice(0, 20).forEach(c => items.push({
          key: `category:${c.name}`, label: `category:${c.name}`,
          insert: c.name.includes(" ") ? `category:"${c.name}"` : `category:${c.name}`,
          group: "Category", meta: `${c.count}`,
        }));
      }
      return items;
    }

    // No colon yet — suggest operator prefixes matching the partial word
    QUERY_OPERATORS.forEach(op => {
      if (!op.startsWith(lower)) return;
      if (op === "artifact") {
        artifactTypesLocal.forEach(a => items.push({
          key: `artifact:${a}`, label: `artifact:${a}`, insert: `artifact:${a}`,
          group: "Artifact Type", meta: `${artifactCounts[a] ?? 0}`, hint: artifactContract?.contract?.[a] || "",
        }));
      } else if (op === "status") {
        STATUS_VALUES.forEach(s => items.push({
          key: `status:${s}`, label: `status:${s.toUpperCase()}`, insert: `status:${s.toUpperCase()}`,
          group: "Status", meta: `${statusCounts[s] ?? 0}`,
        }));
      } else if (op === "category") {
        categories.slice(0, 20).forEach(c => items.push({
          key: `category:${c.name}`, label: `category:${c.name}`,
          insert: c.name.includes(" ") ? `category:"${c.name}"` : `category:${c.name}`,
          group: "Category", meta: `${c.count}`,
        }));
      }
    });
    return items;
  }, [q, caret, tree, artifactContract]);

  // Reset highlight when suggestions change (avoid stale indices)
  useEffect(() => { setSugIndex(0); }, [suggestions.length]);

  const acceptSuggestion = useCallback((sug) => {
    if (!sug) return;
    const cp = Math.min(caret, q.length);
    const before = q.slice(0, cp);
    const after = q.slice(cp);
    const tokenMatch = before.match(/(\S+)$/);
    const start = tokenMatch ? cp - tokenMatch[1].length : cp;
    const newQ = q.slice(0, start) + sug.insert + " " + after.replace(/^\s*/, "");
    const newCaret = start + sug.insert.length + 1;
    setQ(newQ);
    setSugOpen(false);
    setSugIndex(0);
    requestAnimationFrame(() => {
      if (inputRef.current) {
        inputRef.current.focus();
        inputRef.current.setSelectionRange(newCaret, newCaret);
        setCaret(newCaret);
      }
    });
  }, [q, caret]);

  // Click outside closes the dropdown
  useEffect(() => {
    if (!sugOpen) return;
    const handler = (e) => {
      if (searchWrapRef.current && !searchWrapRef.current.contains(e.target)) setSugOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [sugOpen]);

  // Fill-in-example helper for the empty-state and help panel
  const setExampleQuery = (example) => {
    setQ(example);
    setSugOpen(false);
    requestAnimationFrame(() => {
      inputRef.current?.focus();
      inputRef.current?.setSelectionRange(example.length, example.length);
      setCaret(example.length);
    });
  };


  if (denied) return (
    <div className="min-h-screen bg-[#0a0a0b] flex flex-col items-center justify-center text-stone-400 gap-3" data-testid="kc-denied">
      <ShieldAlert className="w-8 h-8 text-amber-400" />
      <div className="text-sm">Enterprise Knowledge Center este disponibil exclusiv Fondatorului.</div>
      <Link to="/admin" className="text-[#d4ff3a] text-xs underline">← Înapoi la Admin</Link>
    </div>
  );
  if (!tree) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400"><Loader2 className="w-6 h-6 animate-spin mr-2" /> Se încarcă Knowledge Center...</div>;

  const activeCat = tree.categories.find(c => c.name === cat) || null;
  const sc = tree.status_counts || {};
  const ac = tree.artifact_type_counts || {};
  const artifactTypes = artifactContract?.types || ["DOCUMENT", "REGISTRY", "GRAPH", "LEDGER", "INDEX", "CATALOG"];

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-[1500px] mx-auto px-6 pt-28 pb-16">
        <div className="flex items-start justify-between flex-wrap gap-4 mb-5">
          <div>
            <Link to="/admin" className="text-xs text-stone-400 hover:text-white mb-3 inline-block">← Înapoi la Admin</Link>
            <h1 className="font-serif text-4xl tracking-tight flex items-center gap-3" data-testid="kc-title">
              <BookOpenCheck className="w-8 h-8 text-[#d4ff3a]" /> Enterprise Knowledge Center
              <span className="text-[10px] px-2 py-1 rounded-full bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 text-[#d4ff3a] font-sans tracking-normal">FOUNDER ONLY</span>
            </h1>
            <p className="text-sm text-stone-400 mt-1" data-testid="kc-status-counts">
              {tree.total} documente · <span className="text-emerald-300">{sc.Active || 0} Active</span> · <span className="text-sky-300">{sc.Review || 0} Review</span> · <span className="text-amber-300">{sc.Draft || 0} Draft</span> · {sc.Archived || 0} Archived — doar documentele Active guvernează (R2).
            </p>
            <p className="text-[11px] text-stone-500 mt-1.5 flex flex-wrap gap-x-3 gap-y-1" data-testid="kc-artifact-counts">
              {artifactTypes.map(t => (
                <span key={t} data-testid={`kc-artifact-count-${t}`}>
                  <span className="text-stone-400">{ARTIFACT_TYPE_LABEL[t] || t}:</span> <span className="text-stone-200 font-mono">{ac[t] ?? 0}</span>
                </span>
              ))}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/admin/research-coverage"
              className="pm-btn pm-btn-secondary"
              data-testid="kc-nav-research-coverage"
              title="Deschide Research Coverage Matrix — instrument intern Founder"
            >
              <Compass className="w-3.5 h-3.5" /> Research Coverage
            </Link>
            <button onClick={load} className="pm-btn pm-btn-secondary" data-testid="kc-refresh"><RefreshCcw className="w-3.5 h-3.5" /> Refresh</button>
          </div>
        </div>

        <form onSubmit={doSearch} className="mb-3" data-testid="kc-search-form">
          <div className="flex gap-2" ref={searchWrapRef}>
            <div className="flex-1 relative">
              <Search className="w-4 h-4 absolute left-3 top-3.5 text-stone-500 pointer-events-none" />
              <input
                ref={inputRef}
                value={q}
                onChange={(e) => { setQ(e.target.value); setCaret(e.target.selectionStart || 0); setSugOpen(true); }}
                onFocus={() => setSugOpen(true)}
                onClick={(e) => setCaret(e.target.selectionStart || 0)}
                onKeyUp={(e) => setCaret(e.target.selectionStart || 0)}
                onKeyDown={(e) => {
                  if (e.key === "Escape") { e.preventDefault(); setSugOpen(false); return; }
                  if (sugOpen && suggestions.length) {
                    if (e.key === "ArrowDown") { e.preventDefault(); setSugIndex(i => (i + 1) % suggestions.length); return; }
                    if (e.key === "ArrowUp") { e.preventDefault(); setSugIndex(i => (i - 1 + suggestions.length) % suggestions.length); return; }
                    if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); acceptSuggestion(suggestions[sugIndex]); return; }
                  }
                  // Enter without open dropdown → form submit continues naturally
                }}
                placeholder="Search documents..."
                className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-3 py-2.5 text-sm outline-none focus:border-[#d4ff3a]/50"
                data-testid="kc-search-input"
                autoComplete="off"
                spellCheck={false}
              />
              {sugOpen && suggestions.length > 0 && (
                <div
                  className="absolute z-30 left-0 right-0 mt-1.5 bg-[#0e0e10] border border-white/15 rounded-xl shadow-2xl max-h-[320px] overflow-y-auto"
                  data-testid="kc-search-suggestions"
                  role="listbox"
                >
                  {(() => {
                    const groups = [];
                    const seen = new Set();
                    suggestions.forEach((s, i) => {
                      if (!seen.has(s.group)) { seen.add(s.group); groups.push({ name: s.group, items: [] }); }
                      groups[groups.length - 1].items.push({ ...s, _idx: i });
                    });
                    return groups.map(g => (
                      <div key={g.name}>
                        <div className="px-3 pt-2 pb-1 text-[9px] uppercase tracking-widest text-stone-500" data-testid={`kc-sug-group-${g.name.replace(/\s/g, "-")}`}>{g.name}</div>
                        {g.items.map(s => (
                          <button
                            key={s.key}
                            type="button"
                            onMouseEnter={() => setSugIndex(s._idx)}
                            onMouseDown={(e) => { e.preventDefault(); acceptSuggestion(s); }}
                            className={`w-full text-left px-3 py-1.5 text-xs flex items-center justify-between gap-3 border-l-2 transition ${sugIndex === s._idx ? "bg-[#d4ff3a]/10 border-[#d4ff3a]" : "border-transparent hover:bg-white/[0.03]"}`}
                            data-testid={`kc-sug-${s.key.replace(/[:"\s]/g, "-")}`}
                            role="option"
                            aria-selected={sugIndex === s._idx}
                          >
                            <span className="flex items-center gap-2 min-w-0">
                              <span className={`font-mono ${sugIndex === s._idx ? "text-white" : "text-stone-300"}`}>{s.label}</span>
                              {s.hint && <span className="text-[10px] text-stone-500 truncate hidden md:inline">— {s.hint}</span>}
                            </span>
                            <span className="text-[10px] text-stone-500 font-mono shrink-0">{s.meta}</span>
                          </button>
                        ))}
                      </div>
                    ));
                  })()}
                  <div className="border-t border-white/10 px-3 py-1.5 text-[9px] text-stone-500 flex flex-wrap gap-x-3 gap-y-0.5">
                    <span>↑ ↓ navigate</span><span>Enter accept</span><span>Esc close</span>
                  </div>
                </div>
              )}
            </div>
            <button type="submit" className="pm-btn pm-btn-success" disabled={searching} data-testid="kc-search-btn">
              {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : "Caută"}
            </button>
            {(results || q) && <button type="button" onClick={() => { setResults(null); setQ(""); setSugOpen(false); }} className="pm-btn pm-btn-secondary" data-testid="kc-search-clear"><X className="w-3.5 h-3.5" /></button>}
          </div>
          <div className="text-[10px] text-stone-500 mt-1.5 flex flex-wrap gap-x-2 gap-y-1 items-center" data-testid="kc-search-help">
            <span className="text-stone-600">Examples:</span>
            {["artifact:DOCUMENT audit", "status:ACTIVE", "category:Architecture"].map(ex => (
              <button
                key={ex} type="button"
                onClick={() => setExampleQuery(ex)}
                className="font-mono text-[10px] px-1.5 py-0.5 rounded border border-white/10 bg-white/[0.02] hover:border-[#d4ff3a]/40 hover:text-white transition"
                data-testid={`kc-search-example-${ex.split(" ")[0].replace(/[:\s]/g, "-")}`}
              >{ex}</button>
            ))}
          </div>
        </form>

        {results && (
          <div className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5 mb-5" data-testid="kc-search-results">
            <div className="text-xs text-stone-400 mb-3 flex items-center gap-2 flex-wrap">
              {results._tokens?.artifact && (
                <span className="inline-flex items-center gap-1.5 text-[10px] text-stone-300 border border-[#d4ff3a]/30 bg-[#d4ff3a]/5 rounded-full px-2 py-0.5" data-testid="kc-search-scope-chip">
                  <span className="opacity-70">artifact:</span>
                  <ArtifactBadge type={results._tokens.artifact} contract={artifactContract?.contract} />
                </span>
              )}
              {results._tokens?.status && (
                <span className="inline-flex items-center gap-1.5 text-[10px] text-stone-300 border border-[#d4ff3a]/30 bg-[#d4ff3a]/5 rounded-full px-2 py-0.5" data-testid="kc-search-scope-chip-status">
                  <span className="opacity-70">status:</span>
                  <StatusBadge s={STATUS_VALUES.find(s => s.toLowerCase() === results._tokens.status.toLowerCase()) || results._tokens.status} />
                </span>
              )}
              {results._tokens?.category && (
                <span className="inline-flex items-center gap-1.5 text-[10px] text-stone-300 border border-[#d4ff3a]/30 bg-[#d4ff3a]/5 rounded-full px-2 py-0.5" data-testid="kc-search-scope-chip-category">
                  <span className="opacity-70">category:</span>
                  <span className="font-mono text-[10px] text-white">{results._tokens.category}</span>
                </span>
              )}
              <span data-testid="kc-search-total">
                {(() => {
                  const t = results._tokens || {};
                  let displayQ = results.query || "";
                  // Strip all operator tokens from displayed query
                  QUERY_OPERATORS.forEach(op => {
                    if (t[op]) {
                      displayQ = displayQ.replace(TOKEN_REGEX(op), " ");
                    }
                  });
                  displayQ = displayQ.replace(/\s+/g, " ").trim();
                  return displayQ
                    ? <>{results.total} rezultate pentru „{displayQ}"</>
                    : <>{results.total} rezultate</>;
                })()}
              </span>
            </div>
            {results.total === 0 && results._tokens ? (
              <div className="text-center py-8 px-4 border border-dashed border-white/10 rounded-xl" data-testid="kc-search-empty-scoped">
                <div className="text-stone-300 text-xs">
                  {results._tokens.artifact
                    ? <>No {ARTIFACT_TYPE_SINGULAR[normalizeArtifact(results._tokens.artifact)] || results._tokens.artifact} artifacts found.</>
                    : <>No matching artifacts found.</>}
                </div>
                <div className="text-stone-500 text-[11px] mt-1">Infrastructure ready.</div>
                {/* Nearest suggestions: pick top 3 non-zero artifact types */}
                <div className="mt-3 flex flex-wrap gap-1.5 justify-center" data-testid="kc-search-suggested-queries">
                  {(() => {
                    const ac = tree.artifact_type_counts || {};
                    const nonZero = Object.entries(ac).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]).slice(0, 3);
                    if (!nonZero.length) return <span className="text-stone-600 text-[10px]">No populated artifact types yet.</span>;
                    return nonZero.map(([type, count]) => (
                      <button
                        key={type} type="button"
                        onClick={() => setExampleQuery(`artifact:${type}`)}
                        className="text-[10px] px-2 py-0.5 rounded-full border border-white/15 hover:border-[#d4ff3a]/50 hover:text-white text-stone-400 transition font-mono"
                        data-testid={`kc-suggest-${type}`}
                      >Try artifact:{type} ({count})</button>
                    ));
                  })()}
                </div>
              </div>
            ) : (
              <div className="space-y-1.5 max-h-[36vh] overflow-y-auto">
                {results.documents.map(d => (
                  <button key={d.path} onClick={() => openDoc(d.path)} className="w-full text-left text-xs bg-white/[0.02] border border-white/10 rounded-lg px-3 py-2 hover:border-[#d4ff3a]/30" data-testid={`kc-result-${d.path.replace(/[/.]/g, "-")}`}>
                    <div className="flex items-center gap-2 flex-wrap"><FileText className="w-3 h-3 text-[#d4ff3a] shrink-0" /><span className="text-stone-200 truncate">{d.title}</span><span className="text-stone-600">· {d.category} · {d.occurrences}×</span><ArtifactBadge type={d.artifact_type} contract={artifactContract?.contract} /><StatusBadge s={d.status} /></div>
                    {d.snippet && <div className="text-[10px] text-stone-500 mt-0.5 truncate">{d.snippet}</div>}
                  </button>
                ))}
                {results.registry_nodes.map(n => (
                  <div key={n.id} className="text-xs bg-white/[0.02] border border-white/10 rounded-lg px-3 py-2">
                    <div className="flex items-center gap-2"><Network className="w-3 h-3 shrink-0" style={{ color: TYPE_META[n.type]?.color }} /><span className="text-stone-200">{n.name}</span><span className="text-stone-600">· {TYPE_META[n.type]?.label}</span></div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="flex gap-2 mb-5 flex-wrap">
          <button onClick={() => setTab("docs")} className={`pm-btn pm-btn-sm ${tab === "docs" ? "pm-btn-success" : "pm-btn-secondary"}`} data-testid="kc-tab-docs"><FileText className="w-3.5 h-3.5" /> Documente</button>
          <button onClick={() => setTab("map")} className={`pm-btn pm-btn-sm ${tab === "map" ? "pm-btn-success" : "pm-btn-secondary"}`} data-testid="kc-tab-map"><Network className="w-3.5 h-3.5" /> Dependency Map</button>
          <a href="/admin/function-map" className="pm-btn pm-btn-sm pm-btn-secondary" data-testid="kc-tab-function-map"><Network className="w-3.5 h-3.5" /> Function Map</a>
          <button onClick={() => setTab("review")} className={`pm-btn pm-btn-sm ${tab === "review" ? "pm-btn-success" : "pm-btn-secondary"}`} data-testid="kc-tab-review"><ClipboardCheck className="w-3.5 h-3.5" /> Review</button>
        </div>

        {tab === "map" && <RegistryGraph onOpenDoc={openDoc} />}
        {tab === "review" && <ReviewPane onOpen={openDoc} />}

        {tab === "docs" && (
          <>
            <div className="flex flex-wrap items-center gap-1.5 mb-4" data-testid="kc-artifact-filter">
              <span className="text-[10px] uppercase tracking-widest text-stone-500 mr-1">Artifact:</span>
              <button
                onClick={() => setArtifactFilter(null)}
                className={`text-[10px] px-2.5 py-1 rounded-full border transition ${!artifactFilter ? "border-[#d4ff3a]/50 bg-[#d4ff3a]/10 text-white" : "border-white/10 text-stone-400 hover:border-white/25 hover:text-white"}`}
                data-testid="kc-artifact-filter-ALL"
              >All <span className="text-stone-500 font-mono">{tree.total}</span></button>
              {artifactTypes.map(t => (
                <button
                  key={t}
                  onClick={() => setArtifactFilter(t)}
                  className={`text-[10px] px-2.5 py-1 rounded-full border transition uppercase font-mono tracking-wide ${artifactFilter === t ? `${ARTIFACT_TYPE_STYLE[t]} border-current` : "border-white/10 text-stone-400 hover:border-white/25 hover:text-white"}`}
                  title={artifactContract?.contract?.[t]}
                  data-testid={`kc-artifact-filter-${t}`}
                >{t} <span className="opacity-70">{ac[t] ?? 0}</span></button>
              ))}
            </div>
            <div className="grid lg:grid-cols-[230px_330px_1fr] gap-4 items-start">
              <div className="space-y-1 max-h-[70vh] overflow-y-auto" data-testid="kc-categories">
                <button onClick={() => setCat(null)} className={`w-full text-left text-xs px-3 py-2 rounded-lg border ${!cat ? "border-[#d4ff3a]/40 bg-[#d4ff3a]/5 text-white" : "border-white/10 text-stone-400 hover:text-white"}`} data-testid="kc-cat-all">
                  Toate categoriile <span className="float-right text-stone-500">{tree.total}</span>
                </button>
                {tree.categories.map(c => (
                  <button key={c.name} onClick={() => setCat(c.name)} className={`w-full text-left text-xs px-3 py-2 rounded-lg border ${cat === c.name ? "border-[#d4ff3a]/40 bg-[#d4ff3a]/5 text-white" : "border-white/10 text-stone-400 hover:text-white"}`} data-testid={`kc-cat-${c.name.replace(/\s/g, "-")}`}>
                    {c.name} <span className="float-right text-stone-500">{c.count}</span>
                  </button>
                ))}
              </div>
              <div className="space-y-1.5 max-h-[70vh] overflow-y-auto" data-testid="kc-doc-list">
                {(() => {
                  const scoped = (activeCat ? [activeCat] : tree.categories).flatMap(c => c.docs);
                  const filtered = artifactFilter ? scoped.filter(d => (d.artifact_type || "DOCUMENT") === artifactFilter) : scoped;
                  if (!filtered.length) {
                    const label = artifactFilter ? (ARTIFACT_TYPE_SINGULAR[artifactFilter] || artifactFilter) : "Document";
                    return (
                      <div className="text-center py-10 px-4 border border-dashed border-white/10 rounded-xl" data-testid="kc-artifact-empty">
                        <div className="text-stone-300 text-xs">No {label} artifacts available yet.</div>
                        <div className="text-stone-500 text-[11px] mt-1">Infrastructure ready.</div>
                      </div>
                    );
                  }
                  return filtered.map(d => (
                    <button key={d.path} onClick={() => openDoc(d.path)} className={`w-full text-left bg-white/[0.02] border rounded-xl px-3.5 py-2.5 flex items-center gap-2.5 ${openPath === d.path ? "border-[#d4ff3a]/50" : "border-white/10 hover:border-[#d4ff3a]/30"}`} data-testid={`kc-doc-${d.path.replace(/[/.]/g, "-")}`}>
                      <FileText className="w-3.5 h-3.5 text-[#d4ff3a] shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="text-xs text-stone-200 truncate">{d.title}</div>
                        <div className="text-[10px] text-stone-500">v{d.version} · Health {d.health?.score ?? 0}%</div>
                      </div>
                      <ArtifactBadge type={d.artifact_type} contract={artifactContract?.contract} />
                      <StatusBadge s={d.status} />
                    </button>
                  ));
                })()}
              </div>
              <InspectorPane path={openPath} onOpen={openDoc} contract={artifactContract?.contract} />
            </div>
            <div className="mt-5 bg-[#0e0e10] border border-white/10 rounded-2xl p-4" data-testid="kc-timeline">
              <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-2 flex items-center gap-1.5"><Clock className="w-3 h-3" /> Activitate recentă (Enterprise Memory)</div>
              <div className="flex flex-wrap gap-2">
                {(tree.recent || []).map(d => (
                  <button key={d.path} onClick={() => openDoc(d.path)} className="text-[11px] px-2.5 py-1.5 rounded-lg border border-white/10 bg-white/[0.02] hover:border-[#d4ff3a]/30 text-stone-300 flex items-center gap-2">
                    <span className="truncate max-w-[220px]">{d.title}</span>
                    <span className="text-stone-600">{new Date(d.updated).toLocaleDateString("ro-RO")}</span>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
