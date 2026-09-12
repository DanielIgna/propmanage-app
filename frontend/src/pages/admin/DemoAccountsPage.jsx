// Demo Accounts Manager — super admin only, master code 0108
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  ShieldCheck, KeyRound, RefreshCw, Eye, EyeOff, Copy, X,
  Loader2, AlertTriangle, CheckCircle2, ChevronLeft, Users, Lock,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const SCOPE_STYLES = {
  testing: { bg: "bg-cyan-100 dark:bg-cyan-500/20", color: "text-cyan-700 dark:text-cyan-300" },
  frontend: { bg: "bg-pink-100 dark:bg-pink-500/20", color: "text-pink-700 dark:text-pink-300" },
  backend: { bg: "bg-blue-100 dark:bg-blue-500/20", color: "text-blue-700 dark:text-blue-300" },
  security: { bg: "bg-rose-100 dark:bg-rose-500/20", color: "text-rose-700 dark:text-rose-300" },
  marketing: { bg: "bg-fuchsia-100 dark:bg-fuchsia-500/20", color: "text-fuchsia-700 dark:text-fuchsia-300" },
};

const PasswordCell = ({ password }) => {
  const [shown, setShown] = useState(false);
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(password);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="flex items-center gap-1.5">
      <code className="text-xs font-mono bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded select-all">
        {shown ? password : "•".repeat(password.length)}
      </code>
      <button onClick={() => setShown(s => !s)} className="text-slate-400 hover:text-violet-500 p-1" title={shown ? "Ascunde" : "Arată"} data-testid={`toggle-${password.slice(0, 3)}`}>
        {shown ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
      </button>
      <button onClick={copy} className="text-slate-400 hover:text-emerald-500 p-1" title="Copiază" data-testid={`copy-${password.slice(0, 3)}`}>
        {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
      </button>
    </div>
  );
};

// Code prompt modal
const CodeModal = ({ title, onConfirm, onClose, busy, error, requireNewPassword = false }) => {
  const [code, setCode] = useState("");
  const [newPw, setNewPw] = useState("");

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="code-modal">
      <div className="w-full max-w-sm bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700">
        <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-gradient-to-r from-rose-500 to-pink-600 text-white">
          <h3 className="font-bold flex items-center gap-2 text-sm"><Lock className="w-4 h-4" /> {title}</h3>
          <button onClick={onClose} className="text-white/80 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-5 space-y-3">
          <div>
            <label className="text-xs uppercase text-slate-500 font-medium mb-1 block">Cod master (4 cifre)</label>
            <input type="password" value={code} onChange={e => setCode(e.target.value)}
              autoFocus inputMode="numeric" maxLength={4} pattern="[0-9]*"
              placeholder="••••"
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-center text-xl font-mono tracking-[0.5em]"
              data-testid="master-code-input" />
          </div>
          {requireNewPassword && (
            <div>
              <label className="text-xs uppercase text-slate-500 font-medium mb-1 block">Parolă nouă (min 8 caractere, litere + cifre)</label>
              <input type="text" value={newPw} onChange={e => setNewPw(e.target.value)}
                placeholder="ex: NewPassword2026!"
                className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm font-mono"
                data-testid="new-password-input" />
            </div>
          )}
          {error && <div className="text-rose-500 text-xs"><AlertTriangle className="w-3.5 h-3.5 inline mr-1" />{error}</div>}
          <button onClick={() => onConfirm(code, newPw)} disabled={busy || code.length !== 4 || (requireNewPassword && newPw.length < 8)}
            className="w-full py-2.5 rounded-lg bg-gradient-to-r from-rose-500 to-pink-600 text-white font-medium disabled:opacity-50 flex items-center justify-center gap-2"
            data-testid="confirm-code-btn">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            Confirmă
          </button>
        </div>
      </div>
    </div>
  );
};

const DemoAccountsPage = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modal, setModal] = useState(null); // { kind: 'reset'|'set', email, busy, error }
  const [flash, setFlash] = useState(null);

  const load = async () => {
    setLoading(true); setError("");
    try {
      const r = await ax.get("/api/admin/demo-accounts");
      setItems(r.data.items || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const handleConfirm = async (code, newPw) => {
    setModal(m => ({ ...m, busy: true, error: "" }));
    try {
      const body = modal.kind === "reset"
        ? { email: modal.email, master_code: code }
        : { email: modal.email, master_code: code, new_password: newPw };
      const url = modal.kind === "reset"
        ? "/api/admin/demo-accounts/reset-password"
        : "/api/admin/demo-accounts/set-password";
      const r = await ax.post(url, body);
      setModal(null);
      setFlash({
        kind: "success",
        message: modal.kind === "reset"
          ? `Parola pentru ${modal.email} a fost resetată la valoarea implicită: ${r.data.new_password}`
          : `Parolă personalizată salvată pentru ${modal.email}.`,
      });
      setTimeout(() => setFlash(null), 8000);
      await load();
    } catch (e) {
      setModal(m => ({ ...m, busy: false, error: e.response?.data?.detail || e.message }));
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 lg:p-8" data-testid="demo-accounts-page">
      <div className="mb-6 flex items-center gap-3 flex-wrap">
        <Link to="/admin" className="text-slate-500 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 text-sm"><ChevronLeft className="w-4 h-4" /> Admin</Link>
        <span className="text-slate-300">·</span>
        <ShieldCheck className="w-5 h-5 text-rose-500" />
        <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">Demo Accounts Manager</h1>
        <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-rose-100 dark:bg-rose-500/15 text-rose-700 dark:text-rose-400">Super-admin only · cod 0108</span>
      </div>

      <div className="max-w-4xl">
        <div className="mb-5 p-4 rounded-xl bg-gradient-to-r from-fuchsia-50 to-violet-50 dark:from-fuchsia-500/10 dark:to-violet-500/10 border border-fuchsia-200 dark:border-fuchsia-500/30">
          <h2 className="font-bold text-slate-900 dark:text-white mb-1 flex items-center gap-2"><Users className="w-4 h-4 text-fuchsia-500" /> 5 conturi demo</h2>
          <p className="text-xs text-slate-600 dark:text-slate-300">
            Conturile sunt destinate prezentărilor către colaboratori externi care explorează platforma pe zona lor de expertiză.
            Tu (super-admin) ești singurul care poate <strong>vedea parolele</strong>, <strong>reseta la implicit</strong> sau <strong>seta o parolă personalizată</strong> — toate aceste operații cer codul de 4 cifre.
          </p>
        </div>

        {flash && (
          <div className={`mb-5 p-3 rounded-lg text-sm flex items-start gap-2 ${
            flash.kind === "success" ? "bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
            : "bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300"
          }`} data-testid="flash-message">
            <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{flash.message}</span>
            <button onClick={() => setFlash(null)} className="ml-auto text-slate-400 hover:text-slate-700"><X className="w-4 h-4" /></button>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12"><Loader2 className="w-7 h-7 animate-spin mx-auto text-slate-400" /></div>
        ) : error ? (
          <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-500/10 text-rose-700 text-sm"><AlertTriangle className="w-4 h-4 inline mr-1" />{error}</div>
        ) : (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
            {items.map((item) => {
              const s = SCOPE_STYLES[item.scope] || { bg: "bg-slate-100", color: "text-slate-700" };
              return (
                <div key={item.email} className="p-4 border-b border-slate-100 dark:border-slate-800 last:border-0 flex flex-wrap items-center gap-3" data-testid={`demo-row-${item.scope}`}>
                  <div className="flex-1 min-w-[200px]">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <code className="text-sm font-mono text-slate-900 dark:text-white font-bold">{item.email}</code>
                      <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${s.bg} ${s.color}`}>{item.scope}</span>
                      {!item.exists && <span className="text-[10px] text-rose-500">⚠ Lipsă în DB</span>}
                      {!item.is_active && item.exists && <span className="text-[10px] text-amber-500">Dezactivat</span>}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {item.name} · {item.role}
                      {item.last_login_at && <> · Ultimul login: {new Date(item.last_login_at).toLocaleString("ro-RO")}</>}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-0.5">Parolă implicită</div>
                    <PasswordCell password={item.default_password} />
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => setModal({ kind: "reset", email: item.email, busy: false, error: "" })}
                      className="px-2.5 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-medium flex items-center gap-1"
                      data-testid={`reset-${item.scope}`}>
                      <RefreshCw className="w-3 h-3" /> Reset implicit
                    </button>
                    <button onClick={() => setModal({ kind: "set", email: item.email, busy: false, error: "" })}
                      className="px-2.5 py-1.5 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-xs font-medium flex items-center gap-1"
                      data-testid={`set-${item.scope}`}>
                      <KeyRound className="w-3 h-3" /> Schimbă parola
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-6 p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400">
          <strong className="text-slate-900 dark:text-white">Cum funcționează:</strong>
          <ul className="mt-2 space-y-1 list-disc pl-5">
            <li><strong>Reset implicit</strong> — revine la parola hardcoded în seed (utilă după ce un colaborator demo a schimbat-o).</li>
            <li><strong>Schimbă parola</strong> — setează o parolă custom (minim 8 caractere, litere + cifre).</li>
            <li>Toate operațiile sunt auditate în log-urile backend cu email-ul super-adminului care a făcut acțiunea.</li>
            <li>Codul master este <strong>0108</strong> (definit în <code>/app/backend/routes/demo_accounts.py</code>).</li>
          </ul>
        </div>
      </div>

      {modal && (
        <CodeModal
          title={modal.kind === "reset" ? `Reset parolă pentru ${modal.email}` : `Schimbă parola pentru ${modal.email}`}
          requireNewPassword={modal.kind === "set"}
          busy={modal.busy}
          error={modal.error}
          onConfirm={handleConfirm}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  );
};

export default DemoAccountsPage;
