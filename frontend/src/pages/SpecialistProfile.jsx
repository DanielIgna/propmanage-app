// Public Specialist Profile Page
import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import { motion } from "framer-motion";
import { Star, CheckCircle2, Award, Briefcase, Calendar, ArrowLeft, Building2, Image as ImageIcon, Shield, Clock, Camera, AlertOctagon } from "lucide-react";
import { PortfolioGallery } from "./Portfolio";
import { HealthScoreBadge } from "../components/HealthScoreBadge";
import { useSEO } from "../hooks/useSEO";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const LEVEL_LABELS = {
  exemplary: { label: "Exemplar", color: "emerald", desc: "Performanță constant excelentă" },
  excellent: { label: "Excelent", color: "[#d4ff3a]", desc: "Foarte fiabil pentru proiecte importante" },
  good: { label: "Bun", color: "amber", desc: "Recomandat" },
  improving: { label: "În progres", color: "stone", desc: "Specialist nou în creștere" },
  new: { label: "Nou", color: "stone", desc: "Specialist nou pe platformă" },
};

const FACTOR_ICONS = { on_time_delivery: Clock, positive_feedback: Star, progress_photos: Camera, warranty_clean: Shield };
const FACTOR_LABELS = {
  on_time_delivery: "Livrare la timp",
  positive_feedback: "Recenzii pozitive",
  progress_photos: "Fotografii progres",
  warranty_clean: "Lipsa reclamațiilor",
};

const TrustScoreCard = ({ specialistId }) => {
  const [trust, setTrust] = useState(null);
  const [rollup, setRollup] = useState(null);
  useEffect(() => {
    axios.get(`${API}/specialists/${specialistId}/trust-score`)
      .then(r => setTrust(r.data))
      .catch(() => setTrust(null));
    axios.get(`${API}/marketplace/specialists/${specialistId}/trust`)
      .then(r => setRollup(r.data))
      .catch(() => setRollup(null));
  }, [specialistId]);
  if (!trust) return null;
  const lvl = LEVEL_LABELS[trust.level] || LEVEL_LABELS.new;
  return (
    <div className="glass-strong rounded-3xl p-6 mb-6" data-testid="trust-score-card">
      {/* GBOS P0.3 — Rebook > stele */}
      {rollup && (rollup.rebook?.show || rollup.recommenders > 0) && (
        <div className="flex flex-wrap gap-2 mb-4" data-testid="profile-trust-chips">
          {rollup.rebook?.show && (
            <span className="flex items-center gap-1.5 bg-rose-500/15 border border-rose-500/30 text-rose-300 px-3 py-1.5 rounded-full text-sm font-semibold" data-testid="profile-rebook"
              title={rollup.explain}>
              ❤️ {rollup.rebook.pct}% ar angaja din nou <span className="opacity-60 font-normal">({rollup.rebook.total} răspunsuri)</span>
            </span>
          )}
          {rollup.recommenders > 0 && (
            <span className="flex items-center gap-1.5 bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 px-3 py-1.5 rounded-full text-sm font-semibold" data-testid="profile-recommenders">
              Recomandat de {rollup.recommenders} {rollup.recommenders === 1 ? "proprietar" : "proprietari"}
            </span>
          )}
        </div>
      )}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className={`w-12 h-12 rounded-2xl bg-${lvl.color}-500/15 border border-${lvl.color}-500/40 flex items-center justify-center`}>
            <Shield className={`w-6 h-6 text-${lvl.color === "[#d4ff3a]" ? "[#d4ff3a]" : `${lvl.color}-300`}`} />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-stone-400">Scor de încredere PropManage</div>
            <div className="flex items-baseline gap-2">
              <span className={`font-serif text-3xl text-${lvl.color === "[#d4ff3a]" ? "[#d4ff3a]" : `${lvl.color}-300`}`} data-testid="trust-score-value">{trust.score}</span>
              <span className="text-sm text-stone-500">/ 100</span>
              <span className={`text-xs uppercase tracking-wider px-2 py-0.5 rounded-full bg-${lvl.color}-500/15 text-${lvl.color === "[#d4ff3a]" ? "[#d4ff3a]" : `${lvl.color}-300`} border border-${lvl.color}-500/30 ml-2`}>
                {lvl.label}
              </span>
            </div>
            <div className="text-xs text-stone-400 mt-0.5">{lvl.desc}</div>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {Object.entries(trust.factors).map(([key, f]) => {
          const Icon = FACTOR_ICONS[key];
          const pct = (f.points / f.max_points) * 100;
          return (
            <div key={key} className="bg-white/[0.03] rounded-2xl p-3" data-testid={`trust-factor-${key}`}>
              <div className="flex items-center gap-1.5 mb-1.5">
                <Icon className="w-3 h-3 text-stone-400" />
                <span className="text-[10px] uppercase tracking-wider text-stone-400">{FACTOR_LABELS[key]}</span>
              </div>
              <div className="text-sm font-medium">{f.points} / {f.max_points} pct</div>
              <div className="h-1 bg-white/5 rounded mt-1.5 overflow-hidden">
                <div className={`h-full bg-${lvl.color === "[#d4ff3a]" ? "[#d4ff3a]" : `${lvl.color}-400`}`} style={{ width: `${pct}%` }} />
              </div>
              {key === "on_time_delivery" && f.total_tasks > 0 && (
                <div className="text-[9px] text-stone-500 mt-1">{f.completed_tasks}/{f.total_tasks} task done · {f.rate}% la timp</div>
              )}
              {key === "warranty_clean" && (
                <div className="text-[9px] text-stone-500 mt-1">
                  {f.disputes > 0 ? `${f.disputes} reclamații` : "Zero reclamații"}
                </div>
              )}
              {key === "progress_photos" && (
                <div className="text-[9px] text-stone-500 mt-1">{f.uploaded} poze încărcate</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const CapabilitiesCard = ({ specialistId }) => {
  const [cap, setCap] = useState(null);
  useEffect(() => {
    axios.get(`${API}/specialists/${specialistId}/capabilities`).then(r => setCap(r.data)).catch(() => {});
  }, [specialistId]);
  if (!cap || (!cap.capabilities?.length && !cap.software?.length)) return null;
  const comp = cap.compatibility || {};
  const prog = cap.progression || {};
  const byPhase = {};
  (cap.capabilities || []).forEach(c => { (byPhase[c.phase] = byPhase[c.phase] || []).push(c); });
  return (
    <div className="glass-strong rounded-3xl p-6 mb-6" data-testid="capabilities-card">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <h2 className="font-serif text-2xl flex items-center gap-2">
          <Shield className="w-5 h-5 text-[#d4ff3a]" />Capabilități & Compatibilitate
        </h2>
        <div className="flex items-center gap-2">
          {prog.level && (
            <span className="inline-flex items-center gap-1 bg-white/5 border border-white/10 px-3 py-1 rounded-full text-[10px] uppercase tracking-wider" data-testid="sp-progression-level">
              <Award className="w-3 h-3 text-[#d4ff3a]" /> Nivel {prog.level}/7 · {prog.name}
            </span>
          )}
          <span className="inline-flex items-center gap-1 bg-[#d4ff3a]/15 border border-[#d4ff3a]/30 text-[#d4ff3a] px-3 py-1 rounded-full text-xs font-bold" data-testid="sp-compatibility-score">
            {comp.score ?? 0}/100 compatibilitate
          </span>
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5 mb-4">
        {(comp.badges || []).filter(b => b.earned).map(b => (
          <span key={b.id} className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-white/5 border border-white/10 text-stone-300" data-testid={`sp-badge-${b.id}`}>
            ✓ {b.label}
          </span>
        ))}
      </div>
      <div className="space-y-3">
        {Object.entries(byPhase).map(([phase, caps]) => (
          <div key={phase}>
            <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-1.5">{phase}</div>
            <div className="flex flex-wrap gap-1.5">
              {caps.map(c => (
                <span key={c.id} className="bg-white/5 px-3 py-1.5 rounded-full text-xs" data-testid={`sp-cap-${c.id}`}>
                  {c.label} <span className="text-stone-500">· {c.level_label}</span>
                </span>
              ))}
            </div>
          </div>
        ))}
        {(cap.software || []).length > 0 && (
          <div>
            <div className="text-[10px] uppercase tracking-wider text-stone-500 mb-1.5">Software & formate</div>
            <div className="flex flex-wrap gap-1.5">
              {cap.software.map(s => (
                <span key={s.id} className="bg-white/[0.03] border border-white/5 px-2.5 py-1 rounded-full text-[11px] text-stone-400">{s.label}</span>
              ))}
            </div>
          </div>
        )}
        {(cap.languages || []).length > 0 && (
          <div className="text-xs text-stone-500">Limbi: {cap.languages.join(" · ")}</div>
        )}
      </div>
    </div>
  );
};

export const SpecialistProfile = () => {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    axios.get(`${API}/specialists/${id}/profile`)
      .then(r => setData(r.data))
      .catch(() => setError(true));
  }, [id]);

  // Dynamic SEO — only injected once profile data is loaded.
  const seoTitle = data
    ? `${data.name}${data.specialty ? ` · ${data.specialty}` : ""} · Specialist verificat PropManage`
    : "Profil specialist · PropManage";
  const seoDesc = data
    ? `${data.name}${data.verified ? " (specialist VERIFIED)" : ""}${data.specialty ? `, ${data.specialty}` : ""} pe PropManage. ${data.reviews_count || 0} recenzii, rating ${data.rating || "—"}/5. Contactează prin platformă cu plată escrow.`
    : "Profil public specialist verificat pe marketplace-ul PropManage.";

  useSEO({
    title: seoTitle,
    description: seoDesc,
    canonical: `https://propmanage.ro/specialists/${id}`,
    noindex: error,    // 404 — don't index broken profiles
    jsonLd: data ? {
      "@context": "https://schema.org",
      "@type": "Person",
      "name": data.name,
      "jobTitle": data.specialty || "Specialist",
      "url": `https://propmanage.ro/specialists/${id}`,
      "aggregateRating": data.reviews_count
        ? {
            "@type": "AggregateRating",
            "ratingValue": data.rating || 0,
            "reviewCount": data.reviews_count,
            "bestRating": 5,
          }
        : undefined,
      "memberOf": {
        "@type": "Organization",
        "name": "PropManage",
        "url": "https://propmanage.ro",
      },
      "knowsAbout": data.service_categories || (data.specialty ? [data.specialty] : []),
    } : null,
  });

  if (error) return (
    <div className="min-h-screen flex items-center justify-center text-stone-400">
      Specialist negăsit. <Link to="/" className="text-[#d4ff3a] ml-2">Înapoi acasă</Link>
    </div>
  );
  if (!data) return <div className="min-h-screen flex items-center justify-center text-stone-400">Se încarcă...</div>;

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100">
      <header className="border-b border-white/5 sticky top-0 z-30 bg-[#0a0a0b]/80 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" data-testid="sp-back">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg font-semibold">PropManage</span>
          </Link>
          <Link to="/login" className="text-xs text-stone-400 hover:text-white flex items-center gap-1">
            <ArrowLeft className="w-3 h-3" /> Login
          </Link>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-12">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-strong rounded-3xl p-10 mb-6">
          <div className="flex items-start gap-6 mb-6">
            <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-stone-600 to-stone-800 flex items-center justify-center text-3xl font-medium shrink-0">
              {data.name?.[0]}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="font-serif text-4xl" data-testid="sp-name">{data.name}</h1>
                {data.verified && (
                  <span className="inline-flex items-center gap-1 bg-[#d4ff3a]/15 text-[#d4ff3a] text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-full border border-[#d4ff3a]/30">
                    <CheckCircle2 className="w-3 h-3" />Verified
                  </span>
                )}
              </div>
              <div className="text-sm text-stone-400 mb-3 capitalize">{data.specialty || "Specialist"}</div>
              <div className="flex items-center gap-6 text-sm">
                <div className="flex items-center gap-1.5">
                  <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                  <span className="font-medium">{data.rating || "—"}</span>
                  <span className="text-stone-500">({data.reviews_count} reviews)</span>
                </div>
                <div className="flex items-center gap-1.5 text-stone-400">
                  <Briefcase className="w-4 h-4" />{data.completed_jobs} joburi
                </div>
                {data.tier && (
                  <div className="flex items-center gap-1.5 text-amber-400">
                    <Award className="w-4 h-4" />{data.tier}
                  </div>
                )}
                {data.health && <HealthScoreBadge health={data.health} />}
              </div>
            </div>
          </div>
          
          {data.specialties.length > 0 && (
            <div className="pt-6 border-t border-white/5">
              <div className="text-xs uppercase tracking-wider text-stone-400 mb-3">Specialități</div>
              <div className="flex flex-wrap gap-2">
                {data.specialties.map((s, i) => (
                  <span key={i} className="bg-white/5 px-3 py-1.5 rounded-full text-xs capitalize">
                    {s.category} <span className="text-stone-500">· {s.count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        {/* Capabilities & Compatibility (Capability Engine D1) */}
        <CapabilitiesCard specialistId={id} />

        {/* Trust Score */}
        <TrustScoreCard specialistId={id} />

        {/* Portfolio */}
        <div className="glass-strong rounded-3xl p-8 mb-6">
          <h2 className="font-serif text-2xl mb-6 flex items-center gap-2">
            <ImageIcon className="w-5 h-5 text-[#d4ff3a]" />Portofoliu de proiecte
          </h2>
          <PortfolioGallery specialistId={id} />
        </div>

        {/* Reviews */}
        <div className="glass-strong rounded-3xl p-8">
          <h2 className="font-serif text-2xl mb-6">Recenzii recente</h2>
          {data.reviews.length === 0 ? (
            <div className="text-center text-sm text-stone-500 py-12">Nicio recenzie încă</div>
          ) : (
            <div className="space-y-4">
              {data.reviews.map((r, i) => (
                <div key={i} className="bg-white/5 rounded-2xl p-5" data-testid={`review-${i}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex gap-0.5">
                      {[1,2,3,4,5].map(n => (
                        <Star key={n} className={`w-3.5 h-3.5 ${n <= r.rating ? "fill-amber-400 text-amber-400" : "text-stone-700"}`} />
                      ))}
                    </div>
                    <div className="text-[10px] text-stone-500">
                      {new Date(r.created_at).toLocaleDateString("ro-RO")}
                    </div>
                  </div>
                  {r.comment && <p className="text-sm text-stone-300 leading-relaxed">"{r.comment}"</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
