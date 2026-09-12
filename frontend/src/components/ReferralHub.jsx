import React, { useEffect, useState } from "react";
import axios from "axios";
import { UserPlus, Heart, Copy, Check, Send, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// GBOS P0.1/P0.2 — Referral & Recommendation Hub (variant: "light" cv2 / "dark" pm)
export const ReferralHub = ({ variant = "dark" }) => {
  const light = variant === "light";
  const [data, setData] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ invited_role: "specialist", name: "", email: "", category: "", message: "" });
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState("");

  const load = () => axios.get(`${API}/referrals/mine`).then(r => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const copy = (key, text) => {
    navigator.clipboard?.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(""), 2000);
  };

  const sendInvite = async () => {
    if (form.name.trim().length < 2) return;
    setBusy(true);
    try {
      const r = await axios.post(`${API}/referrals/invite`, form);
      setResult(r.data);
      setForm({ invited_role: "specialist", name: "", email: "", category: "", message: "" });
      load();
    } catch (e) { alert(e?.response?.data?.detail || "Eroare la trimitere"); }
    setBusy(false);
  };

  const card = light ? "rounded-2xl border border-slate-100 bg-white p-4 shadow-sm" : "rounded-2xl border border-white/10 bg-white/[0.03] p-4";
  const title = light ? "text-sm font-black text-slate-900" : "text-sm font-semibold text-stone-100";
  const sub = light ? "text-[11px] text-slate-400" : "text-[11px] text-stone-500";
  const input = light ? "w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-sm text-slate-800 outline-none" : "w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-stone-200 outline-none";
  const btnGhost = light ? "px-3 py-2 rounded-full bg-slate-100 text-slate-600 text-xs font-bold" : "px-3 py-2 rounded-full bg-white/5 text-stone-300 text-xs font-bold";

  return (
    <div className={card} data-testid="referral-hub">
      <div className="flex items-center gap-2.5 mb-1">
        <Heart className="w-4 h-4 text-[#16a34a]" />
        <div className={title}>Invită & Recomandă</div>
        {data && <span className={`${sub} ml-auto`} data-testid="referral-stats">{data.stats.sent} invitații · {data.stats.registered + data.stats.referred_total} conturi create</span>}
      </div>
      <p className={`${sub} mb-3`}>Rețeaua crește prin recomandări reale — fiecare invitație acceptată întărește comunitatea.</p>

      <div className="flex flex-wrap gap-2">
        <button onClick={() => copy("owner", data?.referral_url || "")} data-testid="referral-copy-owner" className={btnGhost}>
          {copied === "owner" ? <Check className="w-3 h-3 inline mr-1" /> : <Copy className="w-3 h-3 inline mr-1" />} Link pentru proprietari
        </button>
        <button onClick={() => copy("spec", data?.referral_url_specialist || "")} data-testid="referral-copy-specialist" className={btnGhost}>
          {copied === "spec" ? <Check className="w-3 h-3 inline mr-1" /> : <Copy className="w-3 h-3 inline mr-1" />} Link pentru specialiști
        </button>
        <button onClick={() => { setShowForm(!showForm); setResult(null); }} data-testid="referral-open-form"
          className="px-3 py-2 rounded-full bg-[#d4ff3a] text-black text-xs font-bold">
          <UserPlus className="w-3 h-3 inline mr-1" /> Invitație personală
        </button>
      </div>

      {showForm && (
        <div className="mt-3 space-y-2" data-testid="referral-form">
          <div className="flex gap-2">
            {[["specialist", "Specialist cu care am lucrat"], ["client", "Proprietar"]].map(([v, l]) => (
              <button key={v} onClick={() => setForm({ ...form, invited_role: v })} data-testid={`referral-role-${v}`}
                className={`flex-1 py-2 rounded-full text-[11px] font-bold border ${form.invited_role === v ? "bg-[#d4ff3a] text-black border-[#d4ff3a]" : btnGhost + " border-transparent"}`}>{l}</button>
            ))}
          </div>
          <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Numele persoanei" className={input} data-testid="referral-name" />
          <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="Email (opțional — trimitem invitația)" className={input} data-testid="referral-email" />
          {form.invited_role === "specialist" && (
            <>
              <input value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} placeholder="Meseria (ex. electrician)" className={input} data-testid="referral-category" />
              <textarea value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} rows={2}
                placeholder="De ce îl recomanzi? (devine recomandarea ta pe profilul lui)" className={`${input} resize-none`} data-testid="referral-message" />
            </>
          )}
          <button onClick={sendInvite} disabled={busy || form.name.trim().length < 2} data-testid="referral-send"
            className="w-full py-2.5 rounded-full bg-[#d4ff3a] text-black text-xs font-bold disabled:opacity-50">
            {busy ? <Loader2 className="w-4 h-4 animate-spin inline" /> : <><Send className="w-3 h-3 inline mr-1" /> Generează invitația</>}
          </button>
          {result && (
            <div className={`${light ? "bg-[#F0FBF4] border-[#D2F2DC]" : "bg-white/5 border-white/10"} border rounded-xl p-3`} data-testid="referral-result">
              <div className={`${sub} mb-1.5`}>Invitația e gata{result.link && form.email ? " și trimisă pe email" : ""} — trimite-i linkul direct:</div>
              <div className="flex items-center gap-2">
                <code className={`flex-1 text-[10px] break-all ${light ? "text-slate-600" : "text-stone-300"}`} data-testid="referral-link">{result.link}</code>
                <button onClick={() => copy("invite", result.link)} className={btnGhost} data-testid="referral-copy-invite">
                  {copied === "invite" ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                </button>
              </div>
              <a href={`https://wa.me/?text=${encodeURIComponent("Te invit pe PropManage — platforma care ține istoricul complet al casei: " + result.link)}`}
                target="_blank" rel="noreferrer" data-testid="referral-whatsapp"
                className="mt-2 inline-block px-3 py-1.5 rounded-full bg-[#25D366] text-white text-[11px] font-bold">Trimite pe WhatsApp</a>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Claim invitație după register/login (idempotent, best-effort)
export const claimPendingInvite = async () => {
  const code = localStorage.getItem("pm_invite_code");
  if (!code) return;
  try {
    await axios.post(`${API}/referrals/claim`, { code });
  } catch (e) { /* invitație folosită/expirată — ignorăm */ }
  localStorage.removeItem("pm_invite_code");
};
