import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../../auth";
import { CARD, EmptyState } from "../../../design-system";
import { Layers } from "lucide-react";
import { radaciniApi, asList } from "../api";
import { useMember, useMeta } from "../hooks";
import { labelOf, linkBtnCls, PageSkeleton } from "../shared";

const pluralTeren = (n) => (n === 1 ? "1 teren" : `${n} terenuri`);

function InterestCard({ id, label, parcelCount }) {
  const base = `${CARD} p-5 flex flex-col gap-3`;

  if (id === "land") {
    return (
      <div className={base} data-testid="radacini-card-land">
        <p className="font-bold text-slate-900 dark:text-white">{label}</p>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {parcelCount === null ? "Se încarcă…" : pluralTeren(parcelCount)}
        </p>
        <div className="mt-auto flex flex-wrap gap-2">
          <Link to="/radacini/terenurile-mele/nou" className={linkBtnCls()} data-testid="radacini-btn-adauga-teren">
            Adaugă teren
          </Link>
          <Link to="/radacini/terenurile-mele" className={linkBtnCls("secondary")}>
            Terenurile mele
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
        <div className="mt-auto">
          <Link to="/radacini/terenuri" className={linkBtnCls()} data-testid="radacini-btn-cauta-teren">
            Caută teren
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
  const [apiStatus, setApiStatus] = useState("checking"); // checking | ok | down
  const [parcelCount, setParcelCount] = useState(null);
  const wantsLand = !!member?.interests?.includes("land");

  useEffect(() => {
    radaciniApi.health().then(() => setApiStatus("ok")).catch(() => setApiStatus("down"));
  }, []);

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

  const badge =
    apiStatus === "ok"
      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300"
      : apiStatus === "down"
      ? "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300"
      : "bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-300";
  const badgeLabel = apiStatus === "ok" ? "API conectat" : apiStatus === "down" ? "API indisponibil" : "Se verifică…";

  return (
    <div className="space-y-6" data-testid="radacini-panou">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Bun venit în Rădăcini</h2>
          {user?.email && <p className="text-sm text-slate-500 dark:text-slate-400">Conectat ca {user.email}</p>}
        </div>
        <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${badge}`} data-testid="radacini-api-status">
          {badgeLabel}
        </span>
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
            />
          ))}
        </div>
      )}
    </div>
  );
}
