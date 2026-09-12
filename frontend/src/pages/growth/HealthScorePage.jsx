// Lead Magnet #1 — „Scorul Casei Tale" (Growth OS G1, Directiva 088)
// Calculator public: 12 întrebări → scor 0-100 INSTANT + riscuri + CTA audit.
// Emailul e opțional și se cere DUPĂ afișarea valorii (cerința CPO — trust first).
import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Building2, ArrowLeft, ArrowRight, ShieldCheck, AlertTriangle, CheckCircle2, Loader2, Mail } from "lucide-react";
import axios from "axios";
import { useSEO } from "../../hooks/useSEO";

const API = process.env.REACT_APP_BACKEND_URL;
const SITE_URL = "https://propmanage.ro";

const QUESTIONS = [
  { id: "an", q: "Când a fost construită clădirea?", max: 10, risk: "Clădire veche — risc structural și instalații la limita duratei de viață",
    opts: [["După 2010", 10], ["1990 – 2010", 8], ["1977 – 1990", 5], ["Înainte de 1977", 2]] },
  { id: "electric", q: "Când a fost refăcută complet instalația electrică?", max: 12, risk: "Instalație electrică veche — risc de incendiu și suprasarcină",
    opts: [["În ultimii 10 ani", 12], ["Acum 10-25 ani", 6], ["Nu a fost refăcută / e originală", 0], ["Nu știu", 3]] },
  { id: "tablou", q: "Tabloul electric are siguranțe automate și împământare?", max: 8, risk: "Fără siguranțe automate/împământare — protecție electrică insuficientă",
    opts: [["Da, ambele", 8], ["Parțial", 4], ["Nu / nu știu", 0]] },
  { id: "tevi", q: "Din ce sunt țevile de apă?", max: 10, risk: "Țevi vechi de plumb/oțel — risc de spargeri și apă contaminată",
    opts: [["PEX / PPR (plastic, noi)", 10], ["Mixte (parțial înlocuite)", 5], ["Plumb / oțel vechi", 0], ["Nu știu", 3]] },
  { id: "umiditate", q: "Ai avut probleme cu umiditate, mucegai sau infiltrații?", max: 10, risk: "Umiditate activă — risc pentru sănătate și degradare structurală",
    opts: [["Niciodată", 10], ["Rar / pete vechi, rezolvate", 5], ["Da, probleme active", 0]] },
  { id: "incalzire", q: "Sistemul de încălzire?", max: 10, risk: "Centrală veche sau fără revizie — risc de avarie și randament slab",
    opts: [["Centrală sub 5 ani, revizie anuală", 10], ["Centrală 5-12 ani", 6], ["Termoficare / punct termic bloc", 6], ["Centrală peste 12 ani sau fără revizie", 1]] },
  { id: "ferestre", q: "Ferestrele locuinței?", max: 8, risk: "Tâmplărie veche — pierderi mari de căldură și condens",
    opts: [["Termopan recent (sub 15 ani)", 8], ["Termopan vechi (peste 15 ani)", 4], ["Lemn vechi / simple", 0]] },
  { id: "izolatie", q: "Clădirea este izolată termic?", max: 7, risk: "Fără izolație — facturi mari și pereți reci cu risc de condens",
    opts: [["Da, anvelopată complet", 7], ["Parțial", 3], ["Nu", 0]] },
  { id: "acoperis", q: "Acoperișul / subsolul clădirii are probleme?", max: 7, risk: "Probleme la acoperiș/subsol — sursă de infiltrații și igrasie",
    opts: [["Fără probleme", 7], ["Probleme minore, rezolvate", 3], ["Da, probleme active", 0]] },
  { id: "renovare", q: "Ultima renovare majoră?", max: 6, risk: "Fără renovări recente — uzură acumulată la finisaje și instalații",
    opts: [["În ultimii 5 ani", 6], ["Acum 5-15 ani", 3], ["Peste 15 ani / niciodată", 0]] },
  { id: "documente", q: "Ai documentele tehnice (carte tehnică, certificat energetic, planuri)?", max: 6, risk: "Documentație lipsă — probleme la vânzare și lucrări viitoare",
    opts: [["Complete", 6], ["Parțiale", 3], ["Lipsesc", 0]] },
  { id: "verificari", q: "Verificările periodice (gaz, centrală, coș fum) sunt la zi?", max: 6, risk: "Verificări legale expirate — risc de siguranță și amenzi",
    opts: [["Toate la zi", 6], ["Parțial", 3], ["Nu / nu se aplică riguros", 0]] },
];

const verdictFor = (score) => {
  if (score >= 80) return { grade: "A", label: "Stare excelentă", color: "text-emerald-400", ring: "border-emerald-500/50" };
  if (score >= 60) return { grade: "B", label: "Stare bună", color: "text-lime-400", ring: "border-lime-500/50" };
  if (score >= 40) return { grade: "C", label: "Necesită atenție", color: "text-amber-400", ring: "border-amber-500/50" };
  return { grade: "D", label: "Risc ridicat", color: "text-red-400", ring: "border-red-500/50" };
};

export default function HealthScorePage() {
  const [answers, setAnswers] = useState({});
  const [showResult, setShowResult] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", consent: false });
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useSEO({
    title: "Scorul Casei Tale — calculator gratuit de sănătate a locuinței · PropManage",
    description: "Află în 2 minute scorul tehnic al locuinței tale (0-100): instalații, umiditate, izolație, riscuri. Gratuit, cu recomandări personalizate.",
    canonical: `${SITE_URL}/scorul-casei`,
  });

  const answered = Object.keys(answers).length;
  const { score, risks } = useMemo(() => {
    let total = 0;
    const r = [];
    QUESTIONS.forEach((q) => {
      const pts = answers[q.id];
      if (pts != null) {
        total += pts;
        if (pts < q.max / 2) r.push(q.risk);
      }
    });
    return { score: total, risks: r.slice(0, 5) };
  }, [answers]);

  const verdict = verdictFor(score);

  const submitEmail = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.consent) { setError("Bifează consimțământul GDPR."); return; }
    setSending(true);
    try {
      const answerLabels = {};
      QUESTIONS.forEach((q) => {
        const pts = answers[q.id];
        const opt = q.opts.find(([, p]) => p === pts);
        if (opt) answerLabels[q.id] = opt[0];
      });
      await axios.post(`${API}/api/public/lead-magnet`, {
        magnet: "health_score", name: form.name, email: form.email,
        consent: form.consent, score, risks, answers: answerLabels,
      });
      setSent(true);
    } catch (err) {
      setError(err?.response?.data?.detail || "A apărut o eroare. Încearcă din nou.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100">
      <header className="border-b border-white/5 sticky top-0 z-30 bg-[#0a0a0b]/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg font-semibold">PropManage</span>
          </Link>
          <Link to="/ghiduri" className="text-xs text-stone-400 hover:text-white flex items-center gap-1">
            <ArrowLeft className="w-3 h-3" /> Ghiduri
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        {!showResult ? (
          <>
            <div className="mb-8">
              <div className="inline-flex items-center gap-1.5 text-xs text-[#d4ff3a] bg-[#d4ff3a]/10 border border-[#d4ff3a]/20 rounded-full px-3 py-1 mb-4">
                <ShieldCheck className="w-3 h-3" /> Calculator gratuit · 2 minute
              </div>
              <h1 className="font-serif text-3xl sm:text-5xl tracking-tight leading-tight mb-3" data-testid="health-score-h1">
                Scorul Casei Tale
              </h1>
              <p className="text-stone-400 text-lg">Răspunde la 12 întrebări și află instant starea tehnică a locuinței tale, cu riscurile principale și recomandări.</p>
              <div className="mt-5 h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-[#d4ff3a] transition-all" style={{ width: `${(answered / QUESTIONS.length) * 100}%` }} />
              </div>
              <div className="text-xs text-stone-500 mt-2">{answered}/{QUESTIONS.length} întrebări</div>
            </div>

            <div className="space-y-6">
              {QUESTIONS.map((q, qi) => (
                <div key={q.id} className="glass-strong rounded-2xl p-5" data-testid={`hs-question-${q.id}`}>
                  <div className="font-medium mb-3 text-stone-100"><span className="text-[#d4ff3a] mr-2">{qi + 1}.</span>{q.q}</div>
                  <div className="grid sm:grid-cols-2 gap-2">
                    {q.opts.map(([label, pts]) => (
                      <button
                        key={label}
                        onClick={() => setAnswers((a) => ({ ...a, [q.id]: pts }))}
                        className={`text-left text-sm px-4 py-2.5 rounded-xl border transition ${answers[q.id] === pts ? "border-[#d4ff3a] bg-[#d4ff3a]/10 text-white" : "border-white/10 bg-white/[0.02] text-stone-300 hover:border-white/25"}`}
                        data-testid={`hs-opt-${q.id}-${pts}`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={() => { setShowResult(true); window.scrollTo({ top: 0, behavior: "smooth" }); }}
              disabled={answered < QUESTIONS.length}
              className="mt-8 w-full bg-[#d4ff3a] text-black py-3.5 rounded-full font-semibold hover:bg-[#bfe632] transition disabled:opacity-40 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
              data-testid="hs-calculate-btn"
            >
              Calculează scorul <ArrowRight className="w-4 h-4" />
            </button>
          </>
        ) : (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <div className={`glass-strong rounded-3xl p-8 text-center border-2 ${verdict.ring} mb-8`} data-testid="hs-result">
              <div className="text-xs uppercase tracking-wider text-stone-400 mb-2">Scorul casei tale</div>
              <div className={`font-serif text-7xl ${verdict.color}`} data-testid="hs-score">{score}<span className="text-3xl text-stone-500">/100</span></div>
              <div className={`text-xl font-medium mt-2 ${verdict.color}`}>{verdict.grade} — {verdict.label}</div>
            </div>

            <div className="glass-strong rounded-2xl p-6 mb-8" data-testid="hs-risks">
              <h2 className="font-serif text-xl mb-4">Riscurile principale identificate</h2>
              {risks.length === 0 ? (
                <p className="text-sm text-emerald-400 flex items-center gap-2"><CheckCircle2 className="w-4 h-4" /> Nu am identificat riscuri majore din răspunsurile tale. Felicitări!</p>
              ) : (
                <ul className="space-y-2.5">
                  {risks.map((r, i) => (
                    <li key={i} className="text-sm text-stone-300 flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" /> {r}
                    </li>
                  ))}
                </ul>
              )}
              <p className="text-xs text-stone-500 mt-4">Scor orientativ, calculat din răspunsurile tale. Pentru evaluare exactă (termoviziune, verificări instrumentale) e nevoie de un audit la fața locului.</p>
            </div>

            {!sent ? (
              <form onSubmit={submitEmail} className="glass-strong rounded-2xl p-6 mb-8" data-testid="hs-email-form">
                <h2 className="font-serif text-xl mb-1 flex items-center gap-2"><Mail className="w-5 h-5 text-[#d4ff3a]" /> Primește raportul complet pe email</h2>
                <p className="text-xs text-stone-400 mb-4">Gratuit: scorul + toate riscurile + recomandări de remediere prioritizate.</p>
                <div className="grid sm:grid-cols-2 gap-3 mb-3">
                  <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Numele tău" className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:border-[#d4ff3a] outline-none" data-testid="hs-name-input" />
                  <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="email@exemplu.ro" className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:border-[#d4ff3a] outline-none" data-testid="hs-email-input" />
                </div>
                <label className="flex items-start gap-2 text-xs text-stone-400 mb-4 cursor-pointer">
                  <input type="checkbox" checked={form.consent} onChange={(e) => setForm({ ...form, consent: e.target.checked })} className="mt-0.5" data-testid="hs-consent-checkbox" />
                  Sunt de acord cu prelucrarea datelor conform <Link to="/privacy" className="underline">politicii de confidențialitate</Link>.
                </label>
                {error && <div className="text-xs text-red-400 mb-3" data-testid="hs-error">{error}</div>}
                <button type="submit" disabled={sending} className="w-full bg-[#d4ff3a] text-black py-3 rounded-full font-semibold hover:bg-[#bfe632] transition inline-flex items-center justify-center gap-2" data-testid="hs-submit-btn">
                  {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />} Trimite raportul
                </button>
              </form>
            ) : (
              <div className="glass-strong rounded-2xl p-6 mb-8 text-center border border-emerald-500/30" data-testid="hs-sent-confirmation">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                <p className="text-sm text-stone-200">Raportul a fost trimis pe email. Verifică și folderul Spam.</p>
              </div>
            )}

            <div className="glass-strong rounded-2xl p-5 mb-8 text-center" data-testid="hs-share-block">
              <div className="text-sm text-stone-300 mb-3">Provoacă-ți prietenii: pot casele lor să treacă testul?</div>
              <div className="flex flex-wrap items-center justify-center gap-2">
                <a
                  href={`https://wa.me/?text=${encodeURIComponent(`Casa mea are scorul ${score}/100 la testul tehnic PropManage. Află-l pe al tău în 2 minute: https://propmanage.ro/scorul-casei?utm_source=share&utm_medium=whatsapp`)}`}
                  target="_blank" rel="noreferrer"
                  className="px-4 py-2 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-xs font-medium hover:bg-emerald-500/25 transition"
                  data-testid="hs-share-whatsapp"
                >WhatsApp</a>
                <a
                  href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent("https://propmanage.ro/scorul-casei?utm_source=share&utm_medium=facebook")}&quote=${encodeURIComponent(`Casa mea are scorul ${score}/100 la testul tehnic PropManage. Poate casa ta să treacă testul?`)}`}
                  target="_blank" rel="noreferrer"
                  className="px-4 py-2 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30 text-xs font-medium hover:bg-blue-500/25 transition"
                  data-testid="hs-share-facebook"
                >Facebook</a>
                <button
                  onClick={() => { navigator.clipboard?.writeText(`Casa mea are scorul ${score}/100 la testul tehnic PropManage. Află-l pe al tău: https://propmanage.ro/scorul-casei?utm_source=share&utm_medium=copy`); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
                  className="px-4 py-2 rounded-full bg-white/5 text-stone-300 border border-white/15 text-xs font-medium hover:bg-white/10 transition"
                  data-testid="hs-share-copy"
                >{copied ? "Copiat ✓" : "Copiază link"}</button>
              </div>
            </div>

            <div className="glass-strong rounded-3xl p-8 text-center" data-testid="hs-audit-cta">
              <h2 className="font-serif text-2xl mb-2">Vrei evaluarea exactă, făcută de un specialist?</h2>
              <p className="text-stone-400 text-sm mb-5 max-w-md mx-auto">Audit tehnic profesionist la fața locului — 350 RON. Identifică probleme care pot costa zeci de mii de RON.</p>
              <Link to="/imobile-verificate/sell" className="inline-block bg-[#d4ff3a] text-black px-7 py-2.5 rounded-full text-sm font-semibold hover:bg-[#bfe632] transition">
                Programează auditul →
              </Link>
            </div>

            <button onClick={() => { setShowResult(false); setAnswers({}); setSent(false); }} className="mt-6 text-xs text-stone-500 hover:text-white underline mx-auto block" data-testid="hs-restart-btn">
              Reia testul
            </button>
          </motion.div>
        )}
      </main>
    </div>
  );
}
