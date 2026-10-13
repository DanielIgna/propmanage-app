import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../../auth";
import { CARD, EmptyState } from "../../../design-system";
import { Layers } from "lucide-react";
import { radaciniApi, asList } from "../api";
import { useMember, useMeta } from "../hooks";
import { ACTIVE_REQUEST, counterOf, fmtPrice, labelOf, linkBtnCls, PageSkeleton, fmtPeriod } from "../shared";

const pluralTeren = (n) => (n === 1 ? "1 teren" : `${n} terenuri`);

// Proiectele mele: contoarele vin din GET /projects (activități viitoare, contribuții în așteptare).
function ProiecteCard() {
  const [state, setState] = useState({ loaded: false, items: [] });

  useEffect(() => {
    let alive = true;
    radaciniApi
      .projects()
      .then((d) => alive && setState({ loaded: true, items: asList(d) }))
      .catch(() => alive && setState({ loaded: true, items: [] }));
    return () => {
      alive = false;
    };
  }, []);

  if (!state.loaded) return <PageSkeleton />;

  return (
    <section className={`${CARD} p-5 space-y-4`} data-testid="radacini-card-proiecte">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-bold text-slate-900 dark:text-white">Proiectele mele</h3>
        <Link to="/radacini/proiecte" className="text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline" data-testid="radacini-card-proiecte-toate">
          Vezi toate
        </Link>
      </div>

      {state.items.length === 0 ? (
        <p className="text-sm text-slate-600 dark:text-slate-300" data-testid="radacini-card-proiecte-gol">
          Nu participi la niciun proiect. Proiectul apare când un acord este semnat.
        </p>
      ) : (
        <ul className="divide-y divide-slate-100 dark:divide-white/5">
          {state.items.slice(0, 3).map((p) => (
            <li key={p.id} className="py-3 flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <Link to={`/radacini/proiecte/${p.id}`} className="font-semibold text-slate-900 dark:text-white hover:underline break-words">
                  {p.title || "Proiect agricol"}
                </Link>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {p.start_date ? fmtPeriod(p.start_date, p.end_date) : "—"}
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-xs font-semibold">
                <span className="rounded-md bg-sky-50 dark:bg-sky-500/15 px-2 py-1 text-sky-700 dark:text-sky-300" data-testid={`radacini-card-proiecte-activitati-${p.id}`}>
                  Activități următoare: {counterOf(p, "upcoming_activities")}
                </span>
                <span className="rounded-md bg-amber-50 dark:bg-amber-500/15 px-2 py-1 text-amber-700 dark:text-amber-300" data-testid={`radacini-card-proiecte-contributii-${p.id}`}>
                  Contribuții de confirmat: {counterOf(p, "contributions_to_review")}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// Ultimele anunțuri din localitatea mea (interes consume).
function ConsumeCard({ label, listings, localities }) {
  const base = `${CARD} p-5 flex flex-col gap-3`;
  return (
    <div className={base} data-testid="radacini-card-consume">
      <p className="font-bold text-slate-900 dark:text-white">{label}</p>
      {listings === null ? (
        <p className="text-sm text-slate-600 dark:text-slate-300">Se încarcă…</p>
      ) : listings.length === 0 ? (
        <p className="text-sm text-slate-600 dark:text-slate-300" data-testid="radacini-card-consume-gol">
          Niciun anunț nou în {localities || "localitatea ta"}.
        </p>
      ) : (
        <ul className="space-y-2" data-testid="radacini-card-consume-lista">
          {listings.map((l) => (
            <li key={l.id} className="text-sm">
              <Link to={`/radacini/piata/${l.id}`} className="font-semibold text-slate-900 dark:text-white hover:underline break-words">
                {l.product}
              </Link>
              <span className="text-slate-500 dark:text-slate-400">
                {" "}· {Number(l.quantity_available || 0).toLocaleString("ro-RO")} {l.unit}
                {fmtPrice(l.price_ron_per_unit, l.unit) ? ` · ${fmtPrice(l.price_ron_per_unit, l.unit)}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-auto flex flex-wrap gap-2">
        <Link to={`/radacini/piata${localities ? `?locality=${encodeURIComponent(localities)}` : ""}`} className={linkBtnCls()} data-testid="radacini-btn-piata">
          Vezi piața
        </Link>
      </div>
    </div>
  );
}

// Rezervările care așteaptă confirmarea mea (interes sell).
function SellCard({ label, toConfirm }) {
  const base = `${CARD} p-5 flex flex-col gap-3`;
  return (
    <div className={base} data-testid="radacini-card-sell">
      <p className="font-bold text-slate-900 dark:text-white">{label}</p>
      <p className="text-sm text-slate-600 dark:text-slate-300" data-testid="radacini-card-sell-confirmare">
        {toConfirm === null ? "Se încarcă…" : `Rezervări de confirmat: ${toConfirm}`}
      </p>
      <div className="mt-auto flex flex-wrap gap-2">
        <Link to="/radacini/piata/nou" className={linkBtnCls()} data-testid="radacini-btn-publica-anunt">
          Publică un anunț
        </Link>
        <Link to="/radacini/rezervari?tab=seller" className={linkBtnCls("secondary")} data-testid="radacini-btn-rezervari">
          Rezervările mele
        </Link>
      </div>
    </div>
  );
}

function InterestCard({ id, label, parcelCount, requestCount, localListings, toConfirm, localities }) {
  const base = `${CARD} p-5 flex flex-col gap-3`;

  if (id === "consume") {
    return <ConsumeCard label={label} listings={localListings} localities={localities} />;
  }

  if (id === "sell") {
    return <SellCard label={label} toConfirm={toConfirm} />;
  }

  if (id === "land") {
    return (
      <div className={base} data-testid="radacini-card-land">
        <p className="font-bold text-slate-900 dark:text-white">{label}</p>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {parcelCount === null ? "Se încarcă…" : pluralTeren(parcelCount)}
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-300" data-testid="radacini-card-land-cereri">
          {requestCount === null ? "Cereri: se încarcă…" : `Cereri primite în așteptare: ${requestCount}`}
        </p>
        <div className="mt-auto flex flex-wrap gap-2">
          <Link to="/radacini/terenurile-mele/nou" className={linkBtnCls()} data-testid="radacini-btn-adauga-teren">
            Adaugă teren
          </Link>
          <Link to="/radacini/terenurile-mele" className={linkBtnCls("secondary")}>
            Terenurile mele
          </Link>
          <Link to="/radacini/cereri" className={linkBtnCls("secondary")} data-testid="radacini-btn-cereri-primite">
            Vezi cererile
          </Link>
        </div>
      </div>
    );
  }

  if (id === "grow") {
    return (
      <div className={base} data-testid="radacini-card-grow">
        <p className="font-bold text-slate-900 dark:text-white">{label}</p>
        <p className="text-sm text-slate-600 dark:text-slate-300">Găsește un teren publicat din zona ta.</p>
        <p className="text-sm text-slate-600 dark:text-slate-300" data-testid="radacini-card-grow-cereri">
          {requestCount === null ? "Cereri active: se încarcă…" : `Cereri active trimise: ${requestCount}`}
        </p>
        <div className="mt-auto flex flex-wrap gap-2">
          <Link to="/radacini/terenuri" className={linkBtnCls()} data-testid="radacini-btn-cauta-teren">
            Caută teren
          </Link>
          <Link to="/radacini/cereri" className={linkBtnCls("secondary")} data-testid="radacini-btn-cererile-mele">
            Cererile mele
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className={base} data-testid={`radacini-card-${id}`}>
      <p className="font-bold text-slate-900 dark:text-white">{label}</p>
      <span className="mt-auto inline-flex w-fit rounded-md bg-slate-100 dark:bg-white/10 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-slate-500 dark:text-slate-300">
        În curând
      </span>
    </div>
  );
}

export default function Panou() {
  const { user } = useAuth();
  const { exists, member, loading } = useMember();
  const { meta } = useMeta();
  const [parcelCount, setParcelCount] = useState(null);
  const wantsLand = !!member?.interests?.includes("land");
  const wantsGrow = !!member?.interests?.includes("grow");
  // received = cereri primite încă active (terenuri) · sent = cereri trimise încă active (cultivare)
  const [requestCounts, setRequestCounts] = useState({ received: null, sent: null });
  const wantsConsume = !!member?.interests?.includes("consume");
  const wantsSell = !!member?.interests?.includes("sell");
  const [localListings, setLocalListings] = useState(null);
  const [toConfirm, setToConfirm] = useState(null);

  useEffect(() => {
    if (!wantsLand) return undefined;
    let alive = true;
    radaciniApi
      .myParcels()
      .then((d) => alive && setParcelCount(asList(d).length))
      .catch(() => alive && setParcelCount(0));
    return () => {
      alive = false;
    };
  }, [wantsLand]);

  useEffect(() => {
    if (!wantsConsume || !member?.locality) return undefined;
    let alive = true;
    radaciniApi
      .listings({ locality: member.locality, limit: 3 })
      .then((d) => alive && setLocalListings(asList(d).slice(0, 3)))
      .catch(() => alive && setLocalListings([]));
    return () => {
      alive = false;
    };
  }, [wantsConsume, member?.locality]);

  useEffect(() => {
    if (!wantsSell) return undefined;
    let alive = true;
    radaciniApi
      .myReservations("seller")
      .then((d) => alive && setToConfirm(asList(d).filter((r) => r.status === "requested").length))
      .catch(() => alive && setToConfirm(0));
    return () => {
      alive = false;
    };
  }, [wantsSell]);

  useEffect(() => {
    if (!wantsLand && !wantsGrow) return undefined;
    let alive = true;
    const countActive = (d) => asList(d).filter((r) => ACTIVE_REQUEST.includes(r.status)).length;
    if (wantsLand) {
      radaciniApi
        .requestsReceived()
        .then((d) => alive && setRequestCounts((c) => ({ ...c, received: countActive(d) })))
        .catch(() => alive && setRequestCounts((c) => ({ ...c, received: 0 })));
    }
    if (wantsGrow) {
      radaciniApi
        .requestsSent()
        .then((d) => alive && setRequestCounts((c) => ({ ...c, sent: countActive(d) })))
        .catch(() => alive && setRequestCounts((c) => ({ ...c, sent: 0 })));
    }
    return () => {
      alive = false;
    };
  }, [wantsLand, wantsGrow]);

  return (
    <div className="space-y-6" data-testid="radacini-panou">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Bun venit în Rădăcini</h2>
        {user?.email && <p className="text-sm text-slate-500 dark:text-slate-400">Conectat ca {user.email}</p>}
      </div>

      {loading ? (
        <PageSkeleton />
      ) : !exists ? (
        <div className={`${CARD} p-5 flex flex-col sm:flex-row sm:items-center gap-4`} data-testid="radacini-cta-profil">
          <div className="flex-1 space-y-1">
            <p className="text-base font-bold text-slate-900 dark:text-white">Completează profilul</p>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Alege ce vrei să faci în Rădăcini și din ce localitate ești. Durează un minut.
            </p>
          </div>
          <Link to="/radacini/profil" className={linkBtnCls()} data-testid="radacini-cta-profil-btn">
            Completează profilul
          </Link>
        </div>
      ) : (member.interests || []).length === 0 ? (
        <EmptyState icon={Layers} title="Niciun interes ales" hint="Editează profilul ca să alegi ce vrei să faci." testid="radacini-panou-empty" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {member.interests.map((id) => (
            <InterestCard
              key={id}
              id={id}
              label={labelOf(meta?.interests, id)}
              parcelCount={parcelCount}
              requestCount={id === "land" ? requestCounts.received : id === "grow" ? requestCounts.sent : null}
              localListings={localListings}
              toConfirm={toConfirm}
              localities={member?.locality}
            />
          ))}
        </div>
      )}

      <ProiecteCard />
    </div>
  );
}
