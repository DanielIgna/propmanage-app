import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { MapPin, AlertTriangle } from "lucide-react";
import ApproxMap from "../components/ApproxMap";
import NearFilter, { NEAR_OFF, nearParams } from "../components/NearFilter";
import { radaciniApi, asList, errMsg } from "../api";
import { useMeta } from "../hooks";
import { Chips, COUNTY, Field, fmtArea, labelOf, PageHeader, PageSkeleton, SelectField, toOpts } from "../shared";

const PAGE = 50;
const ALL = "all";

// Parametrii pentru GET /parcels (filtre locality/model, paginare skip/limit).
const buildParams = (filters, skip, near) => ({
  ...nearParams(near),
  limit: PAGE,
  skip,
  locality: filters.locality !== ALL ? filters.locality : undefined,
  model: filters.model !== ALL ? filters.model : undefined,
});

const fmtDist = (d) => (Number.isFinite(d) ? `${d < 10 ? d.toFixed(1) : Math.round(d)} km` : null);

function ParcelCard({ p, modelOptions }) {
  return (
    <Link
      to={`/radacini/terenuri/${p.id}`}
      className={`${CARD} p-4 flex flex-col gap-3 hover:border-emerald-400 transition-colors`}
      data-testid={`radacini-parcel-card-${p.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="font-bold text-slate-900 dark:text-white">{p.title}</p>
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 whitespace-nowrap">{fmtArea(p.area_m2)}</span>
      </div>
      <p className="text-sm text-slate-500 dark:text-slate-400">
        {p.locality} · {COUNTY}
      </p>
      <Chips items={(p.offer?.models || []).map((m) => labelOf(modelOptions, m))} />
      {fmtDist(p.distance_km) && (
        <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-300" data-testid={`radacini-parcel-distanta-${p.id}`}>
          La {fmtDist(p.distance_km)} de tine
        </p>
      )}
      {p.owner_name && <p className="text-xs text-slate-500 dark:text-slate-400 mt-auto">Proprietar: {p.owner_name}</p>}
    </Link>
  );
}

export default function Terenuri() {
  const { meta, loading: metaLoading } = useMeta();
  const [filters, setFilters] = useState({ locality: ALL, model: ALL });
  const [near, setNear] = useState(NEAR_OFF);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [moreLoading, setMoreLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    radaciniApi
      .parcels(buildParams(filters, 0, near))
      .then((d) => {
        if (!alive) return;
        const list = asList(d);
        setItems(list);
        setHasMore(list.length === PAGE);
      })
      .catch((e) => alive && setError(e))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [filters, near]);

  const loadMore = async () => {
    setMoreLoading(true);
    try {
      const list = asList(await radaciniApi.parcels(buildParams(filters, items.length, near)));
      setItems((prev) => [...prev, ...list]);
      setHasMore(list.length === PAGE);
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut încărca mai multe terenuri"));
    } finally {
      setMoreLoading(false);
    }
  };

  const localityOpts = [{ id: ALL, label: "Toate localitățile" }, ...toOpts(meta?.localities || [])];
  const modelOpts = [{ id: ALL, label: "Toate modelele" }, ...(meta?.offer_models || [])];
  const points = items.map((p) => ({
    id: p.id,
    lat: p.lat,
    lng: p.lng,
    title: p.title,
    subtitle: `${p.locality} · ${fmtArea(p.area_m2)}`,
    href: `/radacini/terenuri/${p.id}`,
    hrefLabel: "Vezi detaliu",
  }));

  return (
    <div className="space-y-5" data-testid="radacini-terenuri">
      <PageHeader
        title="Terenuri disponibile"
        subtitle="Terenuri publicate din Cluj. Locația apare aproximativ, până la contact."
      />

      {metaLoading ? (
        <PageSkeleton />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field label="Localitate" htmlFor="radacini-filtru-localitate">
            <SelectField
              id="radacini-filtru-localitate"
              value={filters.locality}
              onValueChange={(v) => setFilters((f) => ({ ...f, locality: v }))}
              options={localityOpts}
              testid="radacini-filtru-localitate"
            />
          </Field>
          <Field label="Model de ofertă" htmlFor="radacini-filtru-model">
            <SelectField
              id="radacini-filtru-model"
              value={filters.model}
              onValueChange={(v) => setFilters((f) => ({ ...f, model: v }))}
              options={modelOpts}
              testid="radacini-filtru-model"
            />
          </Field>
        </div>
      )}

      {!metaLoading && <NearFilter value={near} onChange={setNear} allowLocality={false} />}

      <ApproxMap points={points} height="380px" emptyLabel={loading ? "Se încarcă terenurile…" : "Niciun teren cu aceste filtre."} />

      {loading ? (
        <PageSkeleton />
      ) : error ? (
        <EmptyState icon={AlertTriangle} title="Nu am putut încărca terenurile" hint={errMsg(error)} testid="radacini-terenuri-error" />
      ) : items.length === 0 ? (
        <EmptyState icon={MapPin} title="Nu există terenuri publicate" hint="Încearcă alte filtre." testid="radacini-terenuri-empty" />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {items.map((p) => (
            <ParcelCard key={p.id} p={p} modelOptions={meta?.offer_models} />
          ))}
        </div>
      )}

      {hasMore && (
        <div className="flex justify-center">
          <DSButton variant="secondary" onClick={loadMore} disabled={moreLoading} data-testid="radacini-terenuri-mai-multe">
            {moreLoading ? "Se încarcă…" : "Încarcă mai multe"}
          </DSButton>
        </div>
      )}
    </div>
  );
}
