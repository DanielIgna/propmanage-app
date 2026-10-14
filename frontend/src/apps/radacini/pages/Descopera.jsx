import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sprout, Store, Users } from "lucide-react";
import ApproxMap from "../components/ApproxMap";
import { s6bApi } from "../api_s6b";
import { asList } from "../api";
import { fmtArea, fmtPrice } from "../shared";

// Pagină publică (fără cont): prezentare Rădăcini, hartă cu terenuri aproximative, piață, comunități deschise.
// Nu folosește layout-ul autentificat. Rută sugerată: /radacini/descopera (top-level, ca /radacini/login).
const loginHref = (next) => `/radacini/login?next=${encodeURIComponent(next)}`;

const card = "rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4";
const primary = "inline-flex items-center justify-center rounded-xl bg-[#d4ff3a] px-5 py-2.5 text-sm font-bold text-black hover:brightness-95";
const secondary = "inline-flex items-center justify-center rounded-xl border border-slate-300 dark:border-white/20 px-5 py-2.5 text-sm font-bold text-slate-900 dark:text-white hover:bg-slate-100 dark:hover:bg-white/10";

function useLoad(fn) {
  const [s, setS] = useState({ loading: true, items: [], error: false });
  useEffect(() => {
    let alive = true;
    fn()
      .then((d) => alive && setS({ loading: false, items: asList(d), error: false }))
      .catch(() => alive && setS({ loading: false, items: [], error: true }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return s;
}

const Section = ({ icon: Icon, title, children }) => (
  <section className="space-y-3">
    <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900 dark:text-white">
      <Icon className="w-5 h-5 text-emerald-600 dark:text-[#d4ff3a]" /> {title}
    </h2>
    {children}
  </section>
);

const Muted = ({ children }) => <p className="text-sm text-slate-500 dark:text-slate-400">{children}</p>;

export default function Descopera() {
  const parcels = useLoad(() => s6bApi.publicParcels({ limit: 50 }));
  const listings = useLoad(() => s6bApi.publicListings({ limit: 6 }));
  const communities = useLoad(() => s6bApi.publicCommunities({ limit: 6 }));

  useEffect(() => {
    document.title = "Descoperă Rădăcini";
    const m = document.createElement("meta");
    m.name = "robots";
    m.content = "noindex";
    document.head.appendChild(m);
    return () => {
      document.head.removeChild(m);
    };
  }, []);

  const points = parcels.items.map((p) => ({
    id: p.id,
    lat: p.lat,
    lng: p.lng,
    title: p.title,
    subtitle: `${p.locality} · ${fmtArea(p.area_m2)}`,
  }));

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0b0c0d]" data-testid="radacini-descopera">
      <div className="mx-auto max-w-5xl px-4 py-8 md:py-12 space-y-10">
        <header className="space-y-5">
          <p className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-emerald-700 dark:text-[#d4ff3a]">
            <Sprout className="w-5 h-5" /> Rădăcini
          </p>
          <h1 className="text-3xl md:text-5xl font-extrabold text-slate-900 dark:text-white leading-tight">
            Pământ, oameni și recolte, de la tine din zonă.
          </h1>
          <p className="max-w-2xl text-base md:text-lg text-slate-600 dark:text-slate-300">
            Găsește un teren de cultivat, lucrează împreună cu o comunitate și vinde sau schimbă local ce ai recoltat. Plata se face direct, la ridicare.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/radacini/login" className={primary} data-testid="radacini-descopera-intra">Intră</Link>
            <Link to="/register?next=/radacini" className={secondary} data-testid="radacini-descopera-cont">Creează cont</Link>
          </div>
        </header>

        <Section icon={Sprout} title="Terenuri din zonă">
          <Muted>Locațiile apar aproximativ, ca zone. Detaliile și contactul sunt pentru membri.</Muted>
          <ApproxMap points={points} height="380px" emptyLabel={parcels.loading ? "Se încarcă…" : "Niciun teren publicat încă."} />
        </Section>

        <Section icon={Store} title="Ultimele anunțuri din piață">
          {listings.loading ? (
            <Muted>Se încarcă…</Muted>
          ) : listings.items.length === 0 ? (
            <Muted>{listings.error ? "Nu am putut încărca anunțurile." : "Niciun anunț activ momentan."}</Muted>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {listings.items.map((l) => (
                <Link key={l.id} to={loginHref(`/radacini/piata/${l.id}`)} className={`${card} block hover:border-emerald-400 transition-colors`} data-testid={`radacini-descopera-anunt-${l.id}`}>
                  <p className="font-bold text-slate-900 dark:text-white break-words">{l.product}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{l.locality}</p>
                  <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">
                    {Number(l.quantity_available || 0).toLocaleString("ro-RO")} {l.unit}
                    {l.price_ron_per_unit != null && <> · {fmtPrice(l.price_ron_per_unit, l.unit)}</>}
                  </p>
                  {l.seller_name && <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Vânzător: {l.seller_name}</p>}
                </Link>
              ))}
            </div>
          )}
        </Section>

        <Section icon={Users} title="Comunități deschise">
          {communities.loading ? (
            <Muted>Se încarcă…</Muted>
          ) : communities.items.length === 0 ? (
            <Muted>{communities.error ? "Nu am putut încărca comunitățile." : "Nicio comunitate deschisă încă."}</Muted>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {communities.items.map((c) => (
                <Link key={c.id} to={loginHref(`/radacini/comunitati/${c.id}`)} className={`${card} block hover:border-emerald-400 transition-colors`} data-testid={`radacini-descopera-comunitate-${c.id}`}>
                  <p className="font-bold text-slate-900 dark:text-white break-words">{c.name}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {c.locality} · {c.members_count ?? 0} {c.members_count === 1 ? "membru" : "membri"}
                  </p>
                  {c.description && <p className="mt-2 text-sm text-slate-600 dark:text-slate-300 line-clamp-3">{c.description}</p>}
                </Link>
              ))}
            </div>
          )}
        </Section>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 dark:border-white/10 pt-6">
          <Muted>Ai deja cont? Intră ca să vezi detaliile și să te alături.</Muted>
          <div className="flex gap-3">
            <Link to="/radacini/login" className={primary}>Intră</Link>
            <Link to="/register?next=/radacini" className={secondary}>Creează cont</Link>
          </div>
        </footer>
      </div>
    </div>
  );
}
