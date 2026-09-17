import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Building2, MapPin, ArrowRight, ShieldCheck, Info } from "lucide-react";
import { PmMarkersMap } from "./PmMap";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SOURCE_BADGE = {
  hartablocuri: { label: "HartaBlocuri", cls: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  both: { label: "PropManage + HartaBlocuri", cls: "bg-[#d4ff3a]/15 text-[#d4ff3a] border-[#d4ff3a]/30" },
  propmanage: { label: "PropManage", cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
};

export const BuildingDiscovery = () => {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState(false);
  const timer = useRef(null);
  const reqId = useRef(0);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (q.trim().length < 2) { setResults([]); setTotal(0); setTouched(false); return; }
    setLoading(true);
    setTouched(true);
    const myReq = ++reqId.current;
    timer.current = setTimeout(async () => {
      try {
        const r = await fetch(`${API}/public/buildings/search?q=${encodeURIComponent(q.trim())}&limit=8`);
        const d = await r.json();
        if (myReq !== reqId.current) return; // ignoră răspuns învechit
        setResults(d.buildings || []);
        setTotal(d.total || 0);
      } catch { if (myReq === reqId.current) setResults([]); }
      finally { if (myReq === reqId.current) setLoading(false); }
    }, 350);
    return () => timer.current && clearTimeout(timer.current);
  }, [q]);

  return (
    <section id="gaseste-blocul" className="relative py-24 px-6 bg-[#0a0a0b] border-t border-white/5" data-testid="building-discovery">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }} transition={{ duration: 0.6 }}>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#d4ff3a]/10 border border-[#d4ff3a]/25 mb-6">
            <MapPin className="w-3.5 h-3.5 text-[#d4ff3a]" />
            <span className="text-[11px] uppercase tracking-widest text-[#d4ff3a] font-semibold">Blocuri din Cluj · 3.400+ clădiri</span>
          </div>
          <h2 className="text-4xl sm:text-5xl font-bold tracking-tight text-stone-50">
            Găsește-ți blocul
          </h2>
          <p className="mt-4 text-base sm:text-lg text-stone-400 max-w-2xl leading-relaxed">
            Caută-ți adresa și pornește <span className="text-stone-200 font-medium">Cartea Casei</span> — gratuit.
            Blocul tău e deja în baza noastră de referință pentru Cluj. Conectează-ți apartamentul și
            preia contextul clădirii într-un cont nou.
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }} transition={{ duration: 0.6, delay: 0.1 }}
          className="mt-8 relative">
          <div className="relative">
            <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-stone-500" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Ex: Aleea Muscel, Mănăștur, Bloc A1, Cluj-Napoca..."
              className="w-full rounded-2xl bg-white/[0.04] border border-white/10 pl-14 pr-5 py-5 text-base text-stone-100 placeholder:text-stone-600 focus:outline-none focus:border-[#d4ff3a]/40 focus:bg-white/[0.06] transition-colors"
              data-testid="discovery-search-input"
            />
          </div>

          <AnimatePresence>
            {touched && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }} className="mt-3 space-y-2 overflow-hidden">
                {!loading && results.some((b) => b.lat_approx && b.lng_approx) && (
                  <div data-testid="discovery-mini-map">
                    <PmMarkersMap
                      points={results.filter((b) => b.lat_approx && b.lng_approx).map((b) => ({
                        id: b.id, lat: b.lat_approx, lng: b.lng_approx,
                        title: b.name,
                        subtitle: `${b.address || ""}${b.neighborhood ? ` · ${b.neighborhood}` : ""} · locație aproximativă${b.source !== "propmanage" ? " · date externe HartaBlocuri" : ""}`,
                        href: `/register?binvite=${b.id}`, hrefLabel: "Conectează",
                      }))}
                      height="clamp(220px, 40vh, 340px)"
                      emptyLabel="Blocurile găsite nu au coordonate."
                    />
                    <p className="mt-1.5 text-[10px] text-stone-600 flex items-center gap-1">
                      <Info className="w-3 h-3" /> Locații aproximative (~1&nbsp;km). Coordonatele exacte sunt private, disponibile după conectare.
                    </p>
                  </div>
                )}
                {loading && (
                  <div className="text-sm text-stone-500 py-6 text-center" data-testid="discovery-loading">Căutăm blocuri…</div>
                )}
                {!loading && results.length === 0 && (
                  <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 text-center" data-testid="discovery-empty">
                    <p className="text-sm text-stone-400">Niciun bloc găsit pentru „{q}".</p>
                    <p className="mt-1 text-xs text-stone-500">
                      Nu-l găsești? Îl poți adăuga manual după ce îți creezi contul — PropManage nu se limitează la HartaBlocuri.
                    </p>
                    <Link to="/register" className="btn-accent mt-4 inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-medium"
                      data-testid="discovery-empty-register">
                      Creează cont gratuit <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                )}
                {!loading && results.map((b, i) => {
                  const badge = SOURCE_BADGE[b.source] || SOURCE_BADGE.hartablocuri;
                  return (
                    <motion.div key={b.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}>
                      <Link to={`/register?binvite=${b.id}`} data-testid={`discovery-result-${b.id}`}
                        className="group flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4 hover:border-[#d4ff3a]/30 hover:bg-white/[0.06] transition-colors">
                        <span className="w-11 h-11 rounded-xl bg-white/5 flex items-center justify-center shrink-0">
                          <Building2 className="w-5 h-5 text-stone-400 group-hover:text-[#d4ff3a] transition-colors" />
                        </span>
                        <span className="flex-1 min-w-0">
                          <span className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-semibold text-stone-100 truncate">{b.name}</span>
                            <span className={`text-[9px] uppercase tracking-wide px-2 py-0.5 rounded-full border ${badge.cls}`}>{badge.label}</span>
                            {b.verified && <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />}
                          </span>
                          <span className="block text-xs text-stone-500 truncate mt-0.5">
                            {b.address}{b.neighborhood ? ` · ${b.neighborhood}` : ""}
                          </span>
                          {b.verification_note && (
                            <span className="mt-1 inline-flex items-center gap-1 text-[10px] text-amber-400/80">
                              <Info className="w-3 h-3" /> {b.verification_note}
                            </span>
                          )}
                        </span>
                        <span className="shrink-0 text-xs font-medium text-stone-500 group-hover:text-[#d4ff3a] transition-colors inline-flex items-center gap-1">
                          Conectează <ArrowRight className="w-4 h-4" />
                        </span>
                      </Link>
                    </motion.div>
                  );
                })}
                {!loading && total > results.length && (
                  <p className="text-center text-xs text-stone-500 pt-1" data-testid="discovery-more">
                    +{total - results.length} alte rezultate — rafinează căutarea sau
                    <Link to="/register" className="text-[#d4ff3a] hover:underline ml-1">creează cont</Link>
                  </p>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {!touched && (
            <p className="mt-4 text-xs text-stone-600 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5" />
              Datele HartaBlocuri sunt referință externă, neverificate de PropManage — le confirmi tu la conectare.
            </p>
          )}
        </motion.div>
      </div>
    </section>
  );
};

export default BuildingDiscovery;
