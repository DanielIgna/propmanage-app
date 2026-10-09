import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import {
  FileText, CheckCircle2, Loader2, AlertTriangle, Printer, Send,
  Scale, X, Edit3
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

export default function ContractPage() {
  const { id } = useParams();
  const [contract, setContract] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [signing, setSigning] = useState(false);
  const [signName, setSignName] = useState("");
  const [showSign, setShowSign] = useState(false);
  const [resolution, setResolution] = useState("");
  const [resolving, setResolving] = useState(false);
  const [me, setMe] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [c, u] = await Promise.all([
        ax.get(`/api/contracts/${id}`),
        ax.get("/api/auth/me").catch(() => ({ data: null })),
      ]);
      setContract(c.data);
      setMe(u.data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Contractul nu a putut fi încărcat");
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [id]);

  const sign = async () => {
    if (signName.trim().length < 2) return;
    setSigning(true);
    try {
      await ax.post(`/api/contracts/${id}/sign`, { signature_name: signName.trim() });
      setShowSign(false);
      setSignName("");
      await load();
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la semnătură");
    } finally { setSigning(false); }
  };

  const resolve = async () => {
    if (resolution.trim().length < 10) return;
    setResolving(true);
    try {
      await ax.post(`/api/contracts/${id}/operator-resolve`, { resolution: resolution.trim() });
      setResolution("");
      await load();
    } catch (e) {
      setError(e?.response?.data?.detail || "Eroare la rezoluție");
    } finally { setResolving(false); }
  };

  if (loading) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-stone-400"><Loader2 className="w-6 h-6 animate-spin mr-2" /> Se încarcă contractul...</div>;
  if (!contract) return <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center text-red-400">{error || "Contract negăsit"}</div>;

  const isClient = me && String(me.id) === String(contract.client_id);
  const isSpecialist = me && String(me.id) === String(contract.specialist_id);
  const isOperator = me && (me.role === "operator" || me.role === "admin");

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white">
      <div className="max-w-4xl mx-auto px-6 pt-28 pb-16">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
          <div>
            <Link to="/" className="text-xs text-stone-400 hover:text-white">← Acasă</Link>
            <h1 className="font-serif text-3xl md:text-4xl mt-2" data-testid="contract-title">
              Contract Servicii
            </h1>
            <div className="flex flex-wrap gap-2 mt-2 text-xs">
              <span className={`px-2 py-0.5 rounded-full border ${contract.status === "active" ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" : contract.status === "mediated" ? "bg-violet-500/15 text-violet-300 border-violet-500/30" : "bg-stone-500/15 text-stone-300 border-stone-500/30"}`} data-testid="contract-status">
                {contract.status.toUpperCase()}
              </span>
              <span className="text-stone-500">ID: {contract.id.slice(0, 12)}...</span>
              <span className="text-stone-500">Template {contract.template_version}</span>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => window.print()} className="pm-btn pm-btn-secondary pm-btn-sm" data-testid="contract-print">
              <Printer className="w-3.5 h-3.5" /> Tipărește / PDF
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-3 mb-4 flex items-start gap-2 text-sm text-red-300">
            <AlertTriangle className="w-4 h-4 mt-0.5" />{error}
            <button onClick={() => setError(null)} className="ml-auto"><X className="w-3.5 h-3.5" /></button>
          </div>
        )}

        {/* Contract body */}
        <div className="bg-white text-stone-900 rounded-2xl p-8 my-5 shadow-2xl" data-testid="contract-body" dangerouslySetInnerHTML={{ __html: contract.body_html }} />

        {/* Signatures */}
        <div className="grid md:grid-cols-2 gap-3">
          <div className={`rounded-2xl p-4 border ${contract.signed_by_client ? "bg-emerald-500/10 border-emerald-500/30" : "bg-white/5 border-white/10"}`} data-testid="sig-client">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs uppercase tracking-wider text-stone-400">Semnătură Client</span>
              {contract.signed_by_client && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
            </div>
            {contract.signed_by_client ? (
              <div>
                <div className="text-sm font-medium">{contract.signed_by_client_name}</div>
                <div className="text-[10px] text-stone-500">{new Date(contract.signed_by_client_at).toLocaleString("ro-RO")}</div>
              </div>
            ) : (
              <div className="text-xs text-stone-500 italic">Nesemnat</div>
            )}
          </div>

          <div className={`rounded-2xl p-4 border ${contract.signed_by_specialist ? "bg-emerald-500/10 border-emerald-500/30" : "bg-white/5 border-white/10"}`} data-testid="sig-specialist">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs uppercase tracking-wider text-stone-400">Semnătură Specialist</span>
              {contract.signed_by_specialist && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
            </div>
            {contract.signed_by_specialist ? (
              <div>
                <div className="text-sm font-medium">{contract.signed_by_specialist_name}</div>
                <div className="text-[10px] text-stone-500">{new Date(contract.signed_by_specialist_at).toLocaleString("ro-RO")}</div>
              </div>
            ) : (
              <div className="text-xs text-stone-500 italic">Nesemnat</div>
            )}
          </div>
        </div>

        {/* Sign button */}
        {((isClient && !contract.signed_by_client) || (isSpecialist && !contract.signed_by_specialist)) && (
          <div className="mt-4">
            <button onClick={() => setShowSign(true)} className="pm-btn pm-btn-primary pm-btn-lg w-full" data-testid="contract-sign-btn">
              <Edit3 className="w-4 h-4" /> Semnează contractul electronic
            </button>
          </div>
        )}

        {/* Operator resolution */}
        {contract.operator_resolution && (
          <div className="mt-5 bg-violet-500/10 border border-violet-500/30 rounded-2xl p-5" data-testid="contract-resolution">
            <div className="flex items-center gap-2 mb-2">
              <Scale className="w-4 h-4 text-violet-400" />
              <h3 className="font-serif text-lg">Rezoluție Operator</h3>
            </div>
            <p className="text-sm text-stone-200 whitespace-pre-wrap">{contract.operator_resolution}</p>
            <div className="text-[10px] text-stone-500 mt-2">{contract.operator_resolved_by} · {new Date(contract.operator_resolved_at).toLocaleString("ro-RO")}</div>
          </div>
        )}

        {isOperator && !contract.operator_resolution && (
          <div className="mt-5 bg-[#0e0e10] border border-white/10 rounded-2xl p-5" data-testid="operator-mediation-form">
            <div className="flex items-center gap-2 mb-3">
              <Scale className="w-4 h-4 text-violet-400" />
              <h3 className="font-serif text-lg">Mediere (doar Operator)</h3>
            </div>
            <textarea value={resolution} onChange={e => setResolution(e.target.value)} rows="4" placeholder="Analizez dovezile depuse și emit rezoluția: ..." className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-sm focus:outline-none" data-testid="op-resolution-input" />
            <div className="flex justify-end mt-3">
              <button onClick={resolve} disabled={resolving || resolution.trim().length < 10} className="pm-btn pm-btn-primary" data-testid="op-resolve-submit">
                {resolving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Emit rezoluție
              </button>
            </div>
          </div>
        )}

        {/* Sign modal */}
        {showSign && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setShowSign(false)}>
            <div className="bg-[#0e0e10] border border-white/10 rounded-3xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
              <h3 className="font-serif text-2xl mb-3">Semnătură electronică</h3>
              <p className="text-xs text-stone-400 mb-3">Introdu numele complet (cum apare în Cartea de Identitate) ca semnătură juridică:</p>
              <input value={signName} onChange={e => setSignName(e.target.value)} placeholder="Nume Prenume" className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#d4ff3a]/50" data-testid="contract-sign-name" />
              <div className="flex gap-2 mt-4">
                <button onClick={() => setShowSign(false)} className="pm-btn pm-btn-secondary flex-1">Anulează</button>
                <button onClick={sign} disabled={signing || signName.trim().length < 2} className="pm-btn pm-btn-primary flex-1" data-testid="contract-sign-confirm">
                  {signing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Confirm semnătura
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
