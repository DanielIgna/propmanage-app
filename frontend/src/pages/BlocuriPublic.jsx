import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useLocation, Link } from "react-router-dom";
import axios from "axios";
import { Building2, MapPin, ArrowRight, Info, ExternalLink, Search, Layers, Home, ShieldCheck } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ── Google Maps loader (abstraction; feature-flag + fallback) ───────────────
let _mapsPromise = null;
const loadGoogleMaps = (key) => {
  if (window.google?.maps) return Promise.resolve(window.google.maps);
  if (_mapsPromise) return _mapsPromise;
  _mapsPromise = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = `https://maps.googleapis.com/maps/api/js?key=${key}&libraries=marker`;
    s.async = true; s.defer = true;
    s.onload = () => resolve(window.google.maps);
    s.onerror = reject;
    document.head.appendChild(s);
  });
  return _mapsPromise;
};

const ERA_OPTS = [
  { v: "", l: "Toate erele" },
  { v: "comunist 1950-1969", l: "Comunist 1950–1969" },
  { v: "comunist 1968-1979", l: "Comunist 1968–1979" },
  { v: "comunist 1977-1990", l: "Comunist 1977–1990" },
  { v: "post-1990", l: "Post-1990" },
  { v: "interbelic/antebelic", l: "Interbelic/antebelic" },
];
const TYP_OPTS = [{ v: "", l: "Toate tipologiile" }, { v: "C1", l: "Panou P+4" }, { v: "C4", l: "Turn înalt" }];

const GoogleMap = ({ markers, apiKey }) => {
  const ref = useRef(null);
  const mapRef = useRef(null);
  useEffect(() => {
    let cancelled = false;
    loadGoogleMaps(apiKey).then((maps) => {
      if (cancelled || !ref.current) return;
      if (!mapRef.current) {
        mapRef.current = new maps.Map(ref.current, { center: { lat: 46.77, lng: 23.6 }, zoom: 12, mapId: "DEMO_MAP_ID" });
      }
      (mapRef.current._markers || []).forEach((m) => (m.map = null));
      const ms = markers.slice(0, 1500).map((b) => new maps.Marker({
        position: { lat: b.lat, lng: b.lng }, map: mapRef.current, title: b.name,
      }));
      mapRef.current._markers = ms;
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [markers, apiKey]);
  return <div ref={ref} className="w-full h-[520px] rounded-2xl border border-white/10" data-testid="blocuri-google-map" />;
};

const FallbackMap = ({ markers }) => (
  <div className="w-full rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="blocuri-fallback-map">
    <div className="flex items-center gap-2 text-xs text-amber-400/80 mb-3">
      <Info className="w-3.5 h-3.5" /> Hartă interactivă indisponibilă (cheie Google Maps neconfigurată). Listă cu navigație.
    </div>
    <div className="grid sm:grid-cols-2 gap-2 max-h-[460px] overflow-y-auto">
      {markers.slice(0, 200).map((b) => (
        <div key={b.id} className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.02] p-3" data-testid={`blocuri-fallback-item-${b.id}`}>
          <MapPin className="w-4 h-4 text-[#d4ff3a] shrink-0" />
          <div className="flex-1 min-w-0">
            <Link to={`/blocuri/cladire/${b.id}`} className="text-sm font-semibold text-stone-100 hover:text-[#d4ff3a] truncate block">{b.name}</Link>
            <div className="text-[11px] text-stone-500 truncate">{b.address}</div>
          </div>
          <a href={`https://www.google.com/maps/search/?api=1&query=${b.lat},${b.lng}`} target="_blank" rel="noreferrer nofollow"
            className="text-[10px] text-stone-400 hover:text-[#d4ff3a] inline-flex items-center gap-1 shrink-0">Google <ExternalLink className="w-3 h-3" /></a>
        </div>
      ))}
    </div>
  </div>
);

// ── /blocuri — Map + cluster explorer ───────────────────────────────────────
export const BlocuriExplorer = () => {
  const [cfg, setCfg] = useState(null);
  const [markers, setMarkers] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [city, setCity] = useState("Cluj-Napoca");
  const [era, setEra] = useState("");
  const [typ, setTyp] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => { axios.get(`${API}/public/maps/config`).then(r => setCfg(r.data)).catch(() => setCfg({ fallback: true })); }, []);
  useEffect(() => { axios.get(`${API}/public/blocuri/clusters`).then(r => setClusters(r.data.clusters || [])).catch(() => {}); }, []);
  useEffect(() => {
    setLoading(true);
    const p = new URLSearchParams();
    if (city) p.set("city", city); if (era) p.set("era", era); if (typ) p.set("typology", typ);
    axios.get(`${API}/public/blocuri/map?${p.toString()}&limit=3000`).then(r => setMarkers(r.data.markers || [])).finally(() => setLoading(false));
  }, [city, era, typ]);

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100 py-24 px-6" data-testid="blocuri-explorer">
      <div className="max-w-6xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#d4ff3a]/10 border border-[#d4ff3a]/25 mb-4">
          <MapPin className="w-3.5 h-3.5 text-[#d4ff3a]" />
          <span className="text-[11px] uppercase tracking-widest text-[#d4ff3a] font-semibold">HartaBlocuri · Județul Cluj</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight">Harta blocurilor</h1>
        <p className="mt-3 text-stone-400 max-w-2xl">Explorează fondul construit din baza de referință HartaBlocuri. <span className="text-amber-400/80">Date externe — neverificate de PropManage.</span></p>

        <div className="flex flex-wrap gap-3 mt-6" data-testid="blocuri-filters">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
            <input value={city} onChange={e => setCity(e.target.value)} placeholder="Localitate"
              className="rounded-full bg-white/[0.04] border border-white/10 pl-10 pr-4 py-2.5 text-sm" data-testid="blocuri-filter-city" />
          </div>
          <select value={era} onChange={e => setEra(e.target.value)} className="rounded-full bg-white/[0.04] border border-white/10 px-4 py-2.5 text-sm" data-testid="blocuri-filter-era">
            {ERA_OPTS.map(o => <option key={o.v} value={o.v} className="bg-stone-900">{o.l}</option>)}
          </select>
          <select value={typ} onChange={e => setTyp(e.target.value)} className="rounded-full bg-white/[0.04] border border-white/10 px-4 py-2.5 text-sm" data-testid="blocuri-filter-typology">
            {TYP_OPTS.map(o => <option key={o.v} value={o.v} className="bg-stone-900">{o.l}</option>)}
          </select>
          <span className="inline-flex items-center text-sm text-stone-500" data-testid="blocuri-marker-count">{loading ? "…" : `${markers.length} blocuri`}</span>
        </div>

        <div className="mt-6">
          {cfg?.enabled ? <GoogleMap markers={markers} apiKey={cfg.api_key} /> : <FallbackMap markers={markers} />}
        </div>

        {clusters.length > 0 && (
          <div className="mt-12" data-testid="blocuri-cluster-index">
            <h2 className="text-lg font-semibold flex items-center gap-2"><Layers className="w-4 h-4 text-[#d4ff3a]" /> Categorii de blocuri</h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
              {clusters.map(c => (
                <Link key={c.slug} to={c.slug} data-testid={`blocuri-cluster-link-${c.slug}`}
                  className="rounded-xl border border-white/10 bg-white/[0.03] p-4 hover:border-[#d4ff3a]/30 transition-colors">
                  <div className="text-sm font-semibold truncate">{c.value_label}</div>
                  <div className="text-xs text-stone-500 mt-1">{c.building_count} blocuri · {c.locality || c.county}</div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ── /blocuri/cladire/:id — public Building Context + funnel ─────────────────
export const BlocuriBuildingDetail = () => {
  const { id } = useParams();
  const [b, setB] = useState(null);
  const [err, setErr] = useState(false);
  useEffect(() => { axios.get(`${API}/public/buildings/${id}`).then(r => setB(r.data.building)).catch(() => setErr(true)); }, [id]);

  if (err) return <div className="min-h-screen bg-[#0a0a0b] text-stone-400 flex items-center justify-center">Blocul nu a fost găsit.</div>;
  if (!b) return <div className="min-h-screen bg-[#0a0a0b] text-stone-400 flex items-center justify-center">Se încarcă…</div>;
  const tl = b.truth_layer;
  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100 py-24 px-6" data-testid="blocuri-building-detail">
      <div className="max-w-3xl mx-auto">
        <Link to="/blocuri" className="text-xs text-stone-500 hover:text-[#d4ff3a] inline-flex items-center gap-1 mb-6"><MapPin className="w-3 h-3" /> Harta blocurilor</Link>
        <h1 className="text-3xl sm:text-4xl font-bold">{b.name}</h1>
        <p className="text-stone-400 mt-2">{b.address}{b.neighborhood ? ` · ${b.neighborhood}` : ""}</p>
        <div className="mt-2 inline-flex items-center gap-1.5 text-[11px] text-amber-400/80"><Info className="w-3.5 h-3.5" /> Date externe HartaBlocuri — neverificate de PropManage</div>

        {tl && (
          <div className="mt-6 grid sm:grid-cols-2 gap-3" data-testid="blocuri-detail-truthlayer">
            {tl.era?.value && <Fact label="Eră" value={tl.era.value} conf={tl.era.confidence} />}
            {tl.form?.value !== "unknown" && <Fact label="Formă" value={tl.form?.value} conf={tl.form?.confidence} />}
            {tl.regime?.derived_floors != null && <Fact label="Regim" value={`P+${tl.regime.derived_floors}`} conf={tl.regime.confidence} />}
            {tl.project_family?.family && <Fact label="Familie proiect" value={tl.project_family.family} conf={tl.project_family.confidence} />}
          </div>
        )}
        {(tl?.typology_profiles || []).length > 0 && (
          <div className="mt-4 space-y-2" data-testid="blocuri-detail-profiles">
            {tl.typology_profiles.map(p => (
              <div key={p.code} className="rounded-xl border border-amber-500/25 bg-amber-500/5 p-3" data-testid={`blocuri-detail-profile-${p.code}`}>
                <span className="text-[9px] font-black uppercase px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300">Candidate · {p.code}</span>
                <span className="ml-2 text-sm font-semibold">{p.label}</span>
                <div className="text-[10px] text-amber-400/70 mt-1">{p.disclaimer}</div>
              </div>
            ))}
          </div>
        )}

        {b.google_maps_url && (
          <a href={b.google_maps_url} target="_blank" rel="noreferrer nofollow" data-testid="blocuri-detail-gmaps"
            className="mt-4 inline-flex items-center gap-1.5 text-sm text-stone-400 hover:text-[#d4ff3a]"><MapPin className="w-4 h-4" /> Deschide în Google Maps <ExternalLink className="w-3 h-3" /></a>
        )}

        {/* Funnel CTA */}
        <div className="mt-8 rounded-2xl border border-[#d4ff3a]/25 bg-[#d4ff3a]/[0.04] p-6" data-testid="blocuri-detail-cta">
          <h3 className="text-lg font-semibold">Preia contextul acestui bloc</h3>
          <p className="text-sm text-stone-400 mt-1">Conectează-ți apartamentul, pornește Cartea Casei și evaluează starea locuinței cu Scorul Casei.</p>
          <div className="flex flex-wrap gap-3 mt-4">
            <Link to={b.cta?.add_property || "/register"} className="btn-accent inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium" data-testid="blocuri-cta-add">
              Adaugă locuința <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/cartea-casei" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm border border-white/15 hover:border-[#d4ff3a]/40" data-testid="blocuri-cta-cartea"><Home className="w-4 h-4" /> Cartea Casei</Link>
            <Link to="/scorul-casei" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm border border-white/15 hover:border-[#d4ff3a]/40" data-testid="blocuri-cta-health"><ShieldCheck className="w-4 h-4" /> Scorul Casei</Link>
          </div>
        </div>
      </div>
    </div>
  );
};

const Fact = ({ label, value, conf }) => (
  <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
    <div className="text-[10px] text-stone-500 uppercase">{label}</div>
    <div className="text-sm font-bold">{value} {conf && <span className="text-[9px] text-stone-500">· {conf}</span>}</div>
  </div>
);

// ── /blocuri/* — public cluster page ────────────────────────────────────────
export const BlocuriCluster = () => {
  const loc = useLocation();
  const [c, setC] = useState(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    axios.get(`${API}/public/blocuri/cluster?slug=${encodeURIComponent(loc.pathname)}`)
      .then(r => setC(r.data.cluster)).catch(() => setErr(true));
  }, [loc.pathname]);

  if (err) return <div className="min-h-screen bg-[#0a0a0b] text-stone-400 flex items-center justify-center" data-testid="blocuri-cluster-404">Categorie indisponibilă.</div>;
  if (!c) return <div className="min-h-screen bg-[#0a0a0b] text-stone-400 flex items-center justify-center">Se încarcă…</div>;
  const a = c.aggregates || {};
  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100 py-24 px-6" data-testid="blocuri-cluster-page">
      <div className="max-w-4xl mx-auto">
        <Link to="/blocuri" className="text-xs text-stone-500 hover:text-[#d4ff3a] inline-flex items-center gap-1 mb-6"><MapPin className="w-3 h-3" /> Harta blocurilor</Link>
        <h1 className="text-3xl sm:text-4xl font-bold" data-testid="blocuri-cluster-h1">{c.content?.h1}</h1>
        <div className="mt-2 inline-flex items-center gap-1.5 text-[11px] text-amber-400/80"><Info className="w-3.5 h-3.5" /> Date externe — neverificate de PropManage{c.provenance?.typology_note ? ` · ${c.provenance.typology_note}` : ""}</div>
        <p className="mt-5 text-stone-300 leading-relaxed">{c.content?.intro}</p>

        <div className="grid sm:grid-cols-2 gap-3 mt-8">
          <InfoBox title="Ce înseamnă" text={c.content?.what_it_means} />
          <InfoBox title="Ce NU înseamnă" text={c.content?.what_it_does_not_mean} amber />
        </div>

        {(a.era_distribution || []).length > 0 && <Dist title="Distribuție eră" items={a.era_distribution} />}
        {(a.floors_distribution || []).length > 0 && <Dist title="Distribuție regim" items={a.floors_distribution} />}
        {(a.neighborhood_distribution || []).length > 0 && <Dist title="Cartiere" items={a.neighborhood_distribution} />}

        {(a.sample_buildings || []).length > 0 && (
          <div className="mt-8" data-testid="blocuri-cluster-samples">
            <h2 className="text-lg font-semibold">Exemple de blocuri</h2>
            <div className="grid sm:grid-cols-2 gap-2 mt-3">
              {a.sample_buildings.map(s => (
                <Link key={s.id} to={`/blocuri/cladire/${s.id}`} className="rounded-xl border border-white/10 bg-white/[0.03] p-3 hover:border-[#d4ff3a]/30">
                  <div className="text-sm font-semibold truncate">{s.name}</div>
                  <div className="text-[11px] text-stone-500 truncate">{s.address}</div>
                </Link>
              ))}
            </div>
          </div>
        )}

        <div className="mt-10 flex flex-wrap gap-3" data-testid="blocuri-cluster-cta">
          <Link to="/blocuri" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm border border-white/15 hover:border-[#d4ff3a]/40"><MapPin className="w-4 h-4" /> Vezi pe hartă</Link>
          <Link to="/cartea-casei" className="btn-accent inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium">Pornește Cartea Casei <ArrowRight className="w-4 h-4" /></Link>
        </div>

        {(c.internal_links?.related_guides || []).length > 0 && (
          <div className="mt-10 text-sm" data-testid="blocuri-cluster-guides">
            <div className="text-stone-500 mb-2">Ghiduri utile</div>
            <div className="flex flex-wrap gap-2">
              {c.internal_links.related_guides.map(g => (
                <Link key={g.slug} to={g.href} className="px-3 py-1.5 rounded-full border border-white/10 hover:border-[#d4ff3a]/40 text-stone-300">{g.title}</Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const InfoBox = ({ title, text, amber }) => (
  <div className={`rounded-xl border p-4 ${amber ? "border-amber-500/25 bg-amber-500/5" : "border-white/10 bg-white/[0.03]"}`}>
    <div className={`text-xs font-black uppercase tracking-wider mb-1 ${amber ? "text-amber-400" : "text-stone-400"}`}>{title}</div>
    <div className="text-sm text-stone-300">{text}</div>
  </div>
);
const Dist = ({ title, items }) => (
  <div className="mt-6">
    <div className="text-xs font-black uppercase tracking-wider text-stone-500 mb-2">{title}</div>
    <div className="flex flex-wrap gap-2">
      {items.map((it, i) => <span key={i} className="px-3 py-1 rounded-full bg-white/[0.04] border border-white/10 text-xs">{it.value} <b className="text-[#d4ff3a]">{it.count}</b></span>)}
    </div>
  </div>
);
