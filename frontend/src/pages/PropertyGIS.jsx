import React, { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import { MapPin, ExternalLink, FileText, Home, ShieldCheck, Wrench, Boxes, ArrowRight, Info, Lock } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

let _mp = null;
const loadMaps = (key) => {
  if (window.google?.maps) return Promise.resolve(window.google.maps);
  if (_mp) return _mp;
  _mp = new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = `https://maps.googleapis.com/maps/api/js?key=${key}`;
    s.async = true; s.defer = true; s.onload = () => res(window.google.maps); s.onerror = rej;
    document.head.appendChild(s);
  });
  return _mp;
};

const PropertyMap = ({ lat, lng, apiKey, enabled }) => {
  const ref = useRef(null);
  useEffect(() => {
    if (!enabled || !apiKey || !lat || !lng) return;
    let cancelled = false;
    loadMaps(apiKey).then((maps) => {
      if (cancelled || !ref.current) return;
      const m = new maps.Map(ref.current, { center: { lat, lng }, zoom: 17, mapTypeId: "hybrid" });
      new maps.Marker({ position: { lat, lng }, map: m });
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [lat, lng, apiKey, enabled]);
  if (!enabled) {
    return (
      <div className="w-full h-[360px] rounded-2xl border border-white/10 bg-white/[0.03] flex flex-col items-center justify-center gap-3" data-testid="property-map-fallback">
        <MapPin className="w-8 h-8 text-[#d4ff3a]" />
        <div className="text-sm text-stone-400">Hartă interactivă indisponibilă (Google Maps neactivat).</div>
        {lat && lng && (
          <a href={`https://www.google.com/maps/search/?api=1&query=${lat},${lng}`} target="_blank" rel="noreferrer"
            className="text-sm text-[#d4ff3a] inline-flex items-center gap-1" data-testid="property-map-gmaps-link">Deschide în Google Maps <ExternalLink className="w-3.5 h-3.5" /></a>
        )}
      </div>
    );
  }
  return <div ref={ref} className="w-full h-[360px] rounded-2xl border border-white/10" data-testid="property-map-google" />;
};

const CTA_ICON = { cartea_casei: Home, add_document: FileText, build_twin: Boxes, house_health: ShieldCheck, specialist: Wrench };

export const PropertyGISPage = () => {
  const { id } = useParams();
  const [gis, setGis] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => { axios.get(`${API}/public/maps/config`).then(r => setCfg(r.data)).catch(() => setCfg({ enabled: false })); }, []);
  useEffect(() => {
    axios.get(`${API}/properties/${id}/gis`)
      .then(r => setGis(r.data))
      .catch(e => setErr(e?.response?.status === 403 ? "forbidden" : (e?.response?.status === 401 ? "auth" : "error")));
  }, [id]);

  if (err === "forbidden") return <Guard icon={Lock} text="Nu ai acces la această proprietate." testid="property-gis-403" />;
  if (err === "auth") return <Guard icon={Lock} text="Autentifică-te pentru a vedea harta proprietății." cta testid="property-gis-401" />;
  if (err) return <Guard icon={Info} text="Nu am putut încărca datele GIS." testid="property-gis-error" />;
  if (!gis) return <div className="min-h-screen bg-[#0a0a0b] text-stone-400 flex items-center justify-center">Se încarcă…</div>;

  const b = gis.building;
  const loc = gis.location;
  const docs = gis.documentation_status || {};
  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100 py-24 px-6" data-testid="property-gis-page">
      <div className="max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#d4ff3a]/10 border border-[#d4ff3a]/25 mb-4">
          <MapPin className="w-3.5 h-3.5 text-[#d4ff3a]" />
          <span className="text-[11px] uppercase tracking-widest text-[#d4ff3a] font-semibold">Harta locuinței mele · privat</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold">{b?.name || "Locuința mea"}</h1>
        <p className="text-stone-400 mt-2">{b?.address}</p>
        <div className="mt-2 inline-flex items-center gap-1.5 text-[11px] text-amber-400/80"><Info className="w-3.5 h-3.5" /> {gis.provenance_note}</div>

        <div className="mt-6">
          <PropertyMap lat={loc?.lat} lng={loc?.lng} apiKey={cfg?.api_key} enabled={cfg?.enabled} />
        </div>

        {/* Layers */}
        <div className="mt-6 flex flex-wrap gap-2" data-testid="property-gis-layers">
          {gis.layers.map(l => (
            <span key={l.id} className="px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/10 text-xs" data-testid={`property-gis-layer-${l.id}`}>
              <b className="text-[#d4ff3a]">{l.id}</b> {l.label}
            </span>
          ))}
        </div>

        {/* Documentation status */}
        <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-5" data-testid="property-gis-docs">
          <h3 className="text-lg font-semibold flex items-center gap-2"><FileText className="w-4 h-4 text-[#d4ff3a]" /> Documentație ({docs.present}/{docs.present + docs.missing})</h3>
          <div className="text-[11px] text-stone-500 mt-1">{docs.note}</div>
          <div className="grid sm:grid-cols-2 gap-2 mt-3">
            {(docs.recommended || []).map(d => (
              <div key={d.category} className="flex items-center gap-2 text-sm">
                <span className={`w-2 h-2 rounded-full ${d.status === "present" ? "bg-emerald-400" : "bg-amber-400"}`} />
                <span className={d.status === "present" ? "text-stone-300" : "text-stone-400"}>{d.label}</span>
                {d.status === "missing" && <span className="text-[10px] text-amber-400/70">recomandat</span>}
              </div>
            ))}
          </div>
        </div>

        {/* Contextual CTAs (real data) */}
        <div className="mt-8" data-testid="property-gis-ctas">
          <h3 className="text-lg font-semibold mb-3">Ce poți face acum</h3>
          <div className="grid sm:grid-cols-2 gap-3">
            {gis.ctas.map(c => {
              const Icon = CTA_ICON[c.key] || ArrowRight;
              return (
                <Link key={c.key} to={c.href} data-testid={`property-gis-cta-${c.key}`}
                  className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 hover:border-[#d4ff3a]/30 transition-colors">
                  <Icon className="w-5 h-5 text-[#d4ff3a] shrink-0" />
                  <span className="text-sm font-medium flex-1">{c.label}</span>
                  <ArrowRight className="w-4 h-4 text-stone-500" />
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

const Guard = ({ icon: Icon, text, cta, testid }) => (
  <div className="min-h-screen bg-[#0a0a0b] text-stone-300 flex flex-col items-center justify-center gap-4 px-6" data-testid={testid}>
    <Icon className="w-10 h-10 text-amber-400" />
    <div className="text-lg">{text}</div>
    {cta && <Link to="/login" className="btn-accent px-6 py-2.5 rounded-full text-sm font-medium">Autentificare</Link>}
  </div>
);

export default PropertyGISPage;
