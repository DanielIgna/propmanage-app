// Public token-based report approval page (no login required).
// Route: /report-respond/:token
import React, { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import axios from "axios";
import { CheckCircle2, FileEdit, AlertTriangle, Loader2, FileText, ArrowRight } from "lucide-react";

const API_URL = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const CategoryPill = ({ value, color = "#60a5fa" }) => (
  <span
    className="inline-block px-2.5 py-1 rounded-full text-[10px] uppercase tracking-wider font-bold"
    style={{ background: `${color}25`, color }}
  >
    {value}
  </span>
);

const PRIORITY_COLORS = { low: "#94a3b8", normal: "#60a5fa", high: "#f59e0b", urgent: "#ef4444" };

export default function ReportApprovalPage() {
  const { token } = useParams();
  const [searchParams] = useSearchParams();
  const presetDecision = searchParams.get("decision"); // optional: comes from email button
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [decision, setDecision] = useState(presetDecision || null);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const { data } = await axios.get(`${API_URL}/digital-twin/reports/approve/info`, { params: { token } });
        if (!mounted) return;
        setInfo(data);
        if (data.approval_status && data.approval_status !== "pending") {
          setDone({ decision: data.decision, comment: data.decision_comment, decided_at: data.decided_at, already: true });
        }
      } catch (e) {
        if (mounted) setErr(e?.response?.data?.detail || e.message);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [token]);

  const submit = async () => {
    if (!decision) return;
    setSubmitting(true);
    setErr(null);
    try {
      const { data } = await axios.post(`${API_URL}/digital-twin/reports/approve/decide`, {
        token,
        decision,
        comment: comment.trim() || null,
      });
      setDone({ decision: data.decision, comment, decided_at: data.decided_at });
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-stone-950 text-stone-300 flex items-center justify-center">
        <div className="flex items-center gap-3 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" /> Se verifică linkul…
        </div>
      </div>
    );
  }

  if (err && !info) {
    return (
      <div className="min-h-screen bg-stone-950 text-stone-300 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-stone-900 border border-red-500/20 rounded-2xl p-6 text-center" data-testid="report-approval-error">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <h1 className="font-serif text-2xl text-white mb-2">Link invalid</h1>
          <p className="text-sm text-stone-400">{err}</p>
          <Link to="/" className="inline-block mt-5 text-xs text-emerald-400 hover:underline">
            ← Înapoi la PropManage
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-950 text-stone-200 py-10 px-4">
      <div className="max-w-2xl mx-auto" data-testid="report-approval-page">
        {/* Brand header */}
        <div className="flex items-center justify-between mb-8">
          <Link to="/" className="text-sm text-stone-500 hover:text-white">
            PropManage · Digital Twin
          </Link>
          <span className="text-[10px] uppercase tracking-[0.16em] text-emerald-400/70 font-semibold">Răspuns rapid</span>
        </div>

        {/* Pin context card */}
        <div className="bg-stone-900 border border-white/10 rounded-2xl p-6 mb-6" data-testid="report-context">
          <div className="text-[10px] uppercase tracking-[0.16em] text-stone-500 font-semibold mb-1">Proiect</div>
          <h1 className="font-serif text-2xl text-white mb-4">{info.project_name}</h1>

          <div className="text-[10px] uppercase tracking-[0.16em] text-stone-500 font-semibold mb-1">Pin</div>
          <h2 className="text-xl text-white font-medium mb-3">{info.pin_title}</h2>

          <div className="flex flex-wrap gap-2 mb-4">
            <CategoryPill value={info.pin_category} color="#10b981" />
            <CategoryPill value={info.pin_priority} color={PRIORITY_COLORS[info.pin_priority] || "#60a5fa"} />
            <CategoryPill value={info.pin_status} />
          </div>

          <div className="text-sm text-stone-400 mb-2">
            Expediator: <strong className="text-stone-200">{info.sender_name}</strong>
          </div>
          <div className="text-sm text-stone-400 mb-3">
            Destinatar: <strong className="text-stone-200">{info.recipient_name || info.recipient_email}</strong>
          </div>

          {info.custom_message_preview && (
            <div className="mt-4 bg-stone-950 border-l-2 border-[#d4ff3a] rounded-lg px-4 py-3 text-sm text-stone-300 italic">
              "{info.custom_message_preview}"
            </div>
          )}

          <div className="mt-4 flex flex-wrap gap-2 text-[11px] text-stone-500">
            <span>💬 {info.comment_count || 0} comentarii</span>
            {info.has_screenshot && <span>📷 captură 3D</span>}
            {info.has_plan_extract && <span>📐 extract plan 2D</span>}
          </div>
        </div>

        {/* Already-decided state */}
        {done && done.already && (
          <div className="bg-stone-900 border border-emerald-500/20 rounded-2xl p-6 text-center" data-testid="report-already-decided">
            <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-3" />
            <h3 className="font-serif text-xl text-white mb-2">Ai răspuns deja la acest raport</h3>
            <div className="text-sm text-stone-400">
              Decizie: <strong className="text-emerald-300">{done.decision === "confirmed" ? "Confirmat ✅" : "Necesită modificări 📝"}</strong>
            </div>
            {done.comment && (
              <div className="mt-3 bg-stone-950 rounded-lg px-4 py-3 text-sm text-stone-300 italic">"{done.comment}"</div>
            )}
            <Link to="/" className="inline-flex items-center gap-1 text-xs text-stone-500 hover:text-white mt-5">
              Înapoi la platformă <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        )}

        {/* Fresh submission state */}
        {done && !done.already && (
          <div className="bg-stone-900 border border-emerald-500/20 rounded-2xl p-6 text-center" data-testid="report-decision-success">
            <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
            <h3 className="font-serif text-2xl text-white mb-2">Răspuns înregistrat ✓</h3>
            <div className="text-sm text-stone-400 mb-4">
              Expediatorul a fost notificat automat — decizia ta este: {" "}
              <strong className={done.decision === "confirmed" ? "text-emerald-400" : "text-amber-400"}>
                {done.decision === "confirmed" ? "Confirmat ✅" : "Necesită modificări 📝"}
              </strong>
            </div>
            {done.comment && (
              <div className="bg-stone-950 rounded-lg px-4 py-3 text-sm text-stone-300 italic text-left">"{done.comment}"</div>
            )}
            <p className="text-[11px] text-stone-500 mt-5">
              Mulțumim! Nu este nevoie să faci nimic în plus. Poți închide această pagină.
            </p>
          </div>
        )}

        {/* Decision buttons */}
        {!done && (
          <div className="bg-stone-900 border border-white/10 rounded-2xl p-6" data-testid="report-decision-form">
            <div className="text-[10px] uppercase tracking-[0.16em] text-[#d4ff3a]/90 font-semibold mb-2">Răspunsul tău</div>
            <h3 className="font-serif text-2xl text-white mb-5">Cum răspunzi la acest raport?</h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
              <button
                onClick={() => setDecision("confirmed")}
                className={`p-5 rounded-2xl border transition-all text-left ${
                  decision === "confirmed"
                    ? "bg-emerald-500/15 border-emerald-500/50 ring-2 ring-emerald-500/40"
                    : "bg-stone-950 border-white/10 hover:border-emerald-500/30"
                }`}
                data-testid="decision-confirmed"
              >
                <CheckCircle2 className="w-7 h-7 text-emerald-400 mb-2" />
                <div className="font-semibold text-white text-base mb-0.5">Confirmat</div>
                <div className="text-xs text-stone-400">Am înțeles, voi acționa pe acest raport.</div>
              </button>
              <button
                onClick={() => setDecision("needs_changes")}
                className={`p-5 rounded-2xl border transition-all text-left ${
                  decision === "needs_changes"
                    ? "bg-amber-500/15 border-amber-500/50 ring-2 ring-amber-500/40"
                    : "bg-stone-950 border-white/10 hover:border-amber-500/30"
                }`}
                data-testid="decision-needs-changes"
              >
                <FileEdit className="w-7 h-7 text-amber-400 mb-2" />
                <div className="font-semibold text-white text-base mb-0.5">Necesită modificări</div>
                <div className="text-xs text-stone-400">Am întrebări sau cer modificări înainte de a trece mai departe.</div>
              </button>
            </div>

            <div className="mb-4">
              <label className="text-[10px] uppercase text-stone-500 font-semibold">Comentariu (opțional)</label>
              <textarea
                rows={3}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder={decision === "needs_changes" ? "Ex: Vreau să verificăm și etajul 2 înainte de remediere." : "Ex: Voi începe lucrarea săptămâna viitoare."}
                maxLength={2000}
                className="w-full mt-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-stone-600"
                data-testid="decision-comment"
              />
              <div className="text-[10px] text-stone-600 mt-0.5 text-right">{comment.length}/2000</div>
            </div>

            {err && (
              <div className="mb-3 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">
                {err}
              </div>
            )}

            <button
              onClick={submit}
              disabled={!decision || submitting}
              className="w-full px-4 py-3 rounded-xl bg-[#d4ff3a] hover:bg-[#c5f02e] disabled:opacity-40 disabled:cursor-not-allowed text-stone-900 font-semibold flex items-center justify-center gap-2"
              data-testid="decision-submit"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
              {submitting ? "Se înregistrează…" : "Trimite răspunsul"}
            </button>

            <p className="text-[11px] text-stone-500 mt-4 text-center">
              Răspunsul este final — nu poate fi schimbat după trimitere. Expediatorul va primi notificare instant.
            </p>
          </div>
        )}

        <p className="text-[10px] text-stone-600 text-center mt-8">
          PropManage Digital Twin · Link securizat cu semnătură HMAC · Expiră în 30 zile
        </p>
      </div>
    </div>
  );
}
