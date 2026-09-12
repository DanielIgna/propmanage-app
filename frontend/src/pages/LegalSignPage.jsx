// Legal Sign Center — collaborator portal to view + accept mandatory documents.
// Route: /legal/sign  (visible to ANY logged-in user; only strategic contributors are gated by status)
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import {
  ShieldCheck, FileText, ChevronLeft, ChevronRight, Loader2, CheckCircle2,
  AlertTriangle, AlertCircle, X, Pen, Lock, FileWarning,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const TYPE_ICON = {
  nda: ShieldCheck,
  collaboration: FileText,
  ip_cession: FileWarning,
  security_policy: Lock,
  infra_access: ShieldCheck,
  regulation: FileText,
};

const Markdown = ({ text }) => {
  // Lightweight markdown renderer — handles h1/h2/h3, lists, paragraphs, strong, blockquote.
  const lines = (text || "").split("\n");
  const blocks = [];
  let listBuf = [];
  let paraBuf = [];
  const flushList = () => {
    if (listBuf.length) {
      blocks.push(<ul key={`ul-${blocks.length}`} className="list-disc pl-6 my-3 space-y-1">{listBuf.map((l, i) => <li key={i} dangerouslySetInnerHTML={{ __html: inline(l) }} />)}</ul>);
      listBuf = [];
    }
  };
  const flushPara = () => {
    if (paraBuf.length) {
      blocks.push(<p key={`p-${blocks.length}`} className="my-3 leading-relaxed text-slate-700 dark:text-slate-300" dangerouslySetInnerHTML={{ __html: inline(paraBuf.join(" ")) }} />);
      paraBuf = [];
    }
  };
  const inline = (s) => s
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code class='px-1 rounded bg-slate-100 dark:bg-slate-800 text-xs'>$1</code>");

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { flushList(); flushPara(); continue; }
    if (line.startsWith("# ")) {
      flushList(); flushPara();
      blocks.push(<h2 key={`h1-${blocks.length}`} className="font-serif text-2xl font-bold mt-6 mb-3 text-slate-900 dark:text-white">{line.slice(2)}</h2>);
    } else if (line.startsWith("## ")) {
      flushList(); flushPara();
      blocks.push(<h3 key={`h2-${blocks.length}`} className="font-serif text-lg font-bold mt-5 mb-2 text-slate-900 dark:text-white">{line.slice(3)}</h3>);
    } else if (line.startsWith("### ")) {
      flushList(); flushPara();
      blocks.push(<h4 key={`h3-${blocks.length}`} className="font-semibold mt-4 mb-2 text-slate-900 dark:text-white">{line.slice(4)}</h4>);
    } else if (line.startsWith("- ")) {
      flushPara();
      listBuf.push(line.slice(2));
    } else if (line.startsWith("> ")) {
      flushList(); flushPara();
      blocks.push(<blockquote key={`bq-${blocks.length}`} className="my-3 border-l-4 border-amber-400 bg-amber-50 dark:bg-amber-500/10 px-4 py-2 italic text-amber-900 dark:text-amber-200" dangerouslySetInnerHTML={{ __html: inline(line.slice(2)) }} />);
    } else {
      flushList();
      paraBuf.push(line);
    }
  }
  flushList(); flushPara();
  return <div>{blocks}</div>;
};

const SignModal = ({ doc, onClose, onSigned }) => {
  const [agreed, setAgreed] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    if (!agreed) { setErr("Trebuie să bifezi că ai citit și ești de acord."); return; }
    if (name.trim().length < 2) { setErr("Introdu numele complet."); return; }
    setBusy(true); setErr("");
    try {
      const { data } = await ax.post("/api/legal/me/accept", {
        document_id: doc.document_id,
        agreed: true,
        signature_name: name.trim(),
      });
      onSigned(data);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-[95] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="sign-modal">
      <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Pen className="w-4 h-4 text-emerald-500" /> Semnează: {doc.title}
          </h3>
          <button onClick={onClose} className="text-slate-400"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 space-y-4">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Confirmă că ai citit integral documentul și ești de acord cu termenii lui.
          </p>
          <label className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-200 cursor-pointer">
            <input type="checkbox" checked={agreed} onChange={e => setAgreed(e.target.checked)} className="mt-0.5 w-4 h-4" data-testid="sign-checkbox" />
            <span>Am citit integral și sunt de acord cu „<strong>{doc.title}</strong>” v{doc.version}.</span>
          </label>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Numele complet (semnătură digitală)</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Ex: Daniel Igna"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
              data-testid="sign-name"
            />
          </div>
          {err && <div className="text-xs text-rose-500 flex items-center gap-1.5"><AlertCircle className="w-3.5 h-3.5" /> {err}</div>}
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80">
          <button onClick={onClose} className="px-3 py-1.5 text-sm rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">Anulează</button>
          <button onClick={submit} disabled={busy || !agreed} className="px-4 py-1.5 text-sm font-medium rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-60 flex items-center gap-1.5" data-testid="sign-submit">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Semnează digital
          </button>
        </div>
      </div>
    </div>
  );
};

const LegalSignPage = () => {
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [active, setActive] = useState(null);  // {document_id, title, body, version}
  const [signDoc, setSignDoc] = useState(null);

  const loadStatus = async () => {
    setLoading(true); setError("");
    try {
      const { data } = await ax.get("/api/legal/me/status");
      setStatus(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };
  useEffect(() => { loadStatus(); }, []);

  const openDoc = async (type) => {
    try {
      const { data } = await ax.get(`/api/legal/documents/${type}`);
      setActive(data);
    } catch (e) {
      alert(e.response?.data?.detail || e.message);
    }
  };

  const total = (status?.required || []).length;
  const signed = (status?.signed || []).length;
  const pct = total ? Math.round((signed / total) * 100) : 0;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950" data-testid="legal-sign-page">
      <div className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div className="max-w-6xl mx-auto px-4 lg:px-8 py-4 flex items-center gap-3">
          <Link to="/" className="text-slate-500 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 text-sm">
            <ChevronLeft className="w-4 h-4" /> Acasă
          </Link>
          <span className="text-slate-300">·</span>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-500" />
            <h1 className="text-lg lg:text-xl font-bold text-slate-900 dark:text-white">Cadru juridic · Documente obligatorii</h1>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-4 lg:p-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT — list */}
        <div className="lg:col-span-1 space-y-3">
          {/* Compliance summary */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
            {loading && <Loader2 className="w-5 h-5 animate-spin text-slate-400" />}
            {!loading && status && (
              <>
                <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Conformitate</div>
                <div className="flex items-center justify-between mb-2">
                  <div className="text-2xl font-bold text-slate-900 dark:text-white">{signed} / {total}</div>
                  {status.compliant
                    ? <span className="text-[10px] font-bold uppercase px-2 py-1 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> CONFORM</span>
                    : <span className="text-[10px] font-bold uppercase px-2 py-1 rounded-full bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> ACȚIUNE NECESARĂ</span>
                  }
                </div>
                <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-emerald-500 to-emerald-600" style={{ width: `${pct}%` }} />
                </div>
                {!status.is_strategic_contributor && (
                  <div className="mt-3 text-[11px] text-slate-500 dark:text-slate-400 flex items-start gap-1">
                    <AlertCircle className="w-3 h-3 mt-0.5" />
                    Nu ești marcat drept Strategic Contributor — semnarea este opțională.
                  </div>
                )}
              </>
            )}
            {error && <div className="text-rose-500 text-sm">{error}</div>}
          </div>

          {/* Pending list */}
          {status && status.pending.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
              <div className="text-xs font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" /> De semnat ({status.pending.length})
              </div>
              <div className="space-y-1">
                {status.pending.map(p => {
                  const Icon = TYPE_ICON[p.type] || FileText;
                  return (
                    <button
                      key={p.type}
                      onClick={() => openDoc(p.type)}
                      className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 text-left border border-slate-100 dark:border-slate-800"
                      data-testid={`pending-${p.type}`}
                    >
                      <Icon className="w-4 h-4 text-rose-500" />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-slate-900 dark:text-white truncate">{p.title}</div>
                        <div className="text-[11px] text-slate-500 truncate">{p.summary}</div>
                      </div>
                      <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Signed list */}
          {status && status.signed.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
              <div className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-2 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> Semnate ({status.signed.length})
              </div>
              <div className="space-y-1">
                {status.signed.map(s => {
                  const Icon = TYPE_ICON[s.document_type] || FileText;
                  return (
                    <button
                      key={s.id}
                      onClick={() => openDoc(s.document_type)}
                      className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 text-left border border-slate-100 dark:border-slate-800"
                      data-testid={`signed-${s.document_type}`}
                    >
                      <Icon className="w-4 h-4 text-emerald-500" />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-slate-900 dark:text-white truncate">{s.document_title}</div>
                        <div className="text-[11px] text-slate-500">v{s.document_version} · {s.accepted_at ? new Date(s.accepted_at).toLocaleDateString("ro-RO") : ""}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Outdated */}
          {status && status.expired.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-amber-300 dark:border-amber-500/40">
              <div className="text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 mb-2 flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" /> Versiune depășită ({status.expired.length})
              </div>
              <div className="text-xs text-slate-600 dark:text-slate-300 mb-2">
                Documente actualizate — semnează versiunea nouă.
              </div>
              {status.expired.map(p => (
                <button
                  key={p.type}
                  onClick={() => openDoc(p.type)}
                  className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-500/10 text-left border border-amber-100 dark:border-amber-500/20"
                  data-testid={`outdated-${p.type}`}
                >
                  <FileWarning className="w-4 h-4 text-amber-500" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-900 dark:text-white truncate">{p.title}</div>
                    <div className="text-[11px] text-amber-600">v{p.signed_version} → v{p.current_version}</div>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* RIGHT — viewer */}
        <div className="lg:col-span-2">
          {!active && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-10 border-2 border-dashed border-slate-200 dark:border-slate-700 text-center" data-testid="doc-viewer-empty">
              <FileText className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-600 mb-3" />
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">Selectează un document</h3>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                Click pe un document din lista din stânga pentru a-l citi și semna.
              </p>
            </div>
          )}
          {active && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden" data-testid="doc-viewer">
              <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between flex-wrap gap-2">
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-slate-400">v{active.version} · {active.type}</div>
                  <h2 className="text-lg font-bold text-slate-900 dark:text-white">{active.title}</h2>
                </div>
                <button
                  onClick={() => setSignDoc({
                    document_id: active.id,
                    title: active.title,
                    version: active.version,
                  })}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium flex items-center gap-1.5"
                  data-testid="doc-viewer-sign"
                >
                  <Pen className="w-4 h-4" /> Semnează digital
                </button>
              </div>
              <div className="p-6 max-h-[70vh] overflow-y-auto text-sm">
                <Markdown text={active.body} />
              </div>
            </div>
          )}
        </div>
      </div>

      {signDoc && (
        <SignModal
          doc={signDoc}
          onClose={() => setSignDoc(null)}
          onSigned={() => {
            setSignDoc(null);
            setActive(null);
            loadStatus();
          }}
        />
      )}
    </div>
  );
};

export default LegalSignPage;
export { LegalSignPage };
