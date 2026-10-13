import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { AlertTriangle, Plus, Store } from "lucide-react";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Input } from "../../../components/ui/input";
import { radaciniApi, asList, errMsg } from "../api";
import { useMeta } from "../hooks";
import {
  Field,
  LISTING_CATEGORIES_FALLBACK,
  LISTING_MODES,
  LISTING_UNITS_FALLBACK,
  PICKUP_NOTICE,
  PageHeader,
  PageSkeleton,
  SelectField,
  Stars,
  fmtPrice,
  labelOf,
  linkBtnCls,
  optsOr,
  toOpts,
} from "../shared";

const PAGE = 50;
const ALL = "all";

const MODE_CLS = {
  sale: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  exchange: "bg-sky-50 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300",
  both: "bg-violet-50 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300",
};

// Parametrii pentru GET /listings (filtre + paginare skip/limit).
const buildParams = (f, q, skip) => ({
  limit: PAGE,
  skip,
  locality: f.locality !== ALL ? f.locality : undefined,
  category: f.category !== ALL ? f.category : undefined,
  mode: f.mode !== ALL ? f.mode : undefined,
  q: q || undefined,
});

function ListingCard({ l, categories, units }) {
  const unit = labelOf(units, l.unit);
  const price = fmtPrice(l.price_ron_per_unit, unit);
  const reference = fmtPrice(l.reference_price, unit);
  const showExchange = l.mode === "exchange" || l.mode === "both";
  return (
    <Link
      to={`/radacini/piata/${l.id}`}
      className={`${CARD} block p-4 md:p-5 space-y-3 hover:border-emerald-300 dark:hover:border-emerald-500/40 transition-colors`}
      data-testid={`radacini-anunt-${l.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-bold text-slate-900 dark:text-white break-words">{l.product}</p>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {l.locality} · {labelOf(categories, l.category)}
          </p>
        </div>
        <span className="text-sm font-bold text-slate-900 dark:text-white whitespace-nowrap" data-testid={`radacini-anunt-cantitate-${l.id}`}>
          {Number(l.quantity_available || 0).toLocaleString("ro-RO")} {unit}
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-bold ${MODE_CLS[l.mode] || MODE_CLS.sale}`}>
          {labelOf(LISTING_MODES, l.mode)}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
        <p className="text-slate-700 dark:text-slate-200">
          Preț: <span className="font-semibold">{price ?? "doar schimb"}</span>
        </p>
        <p className="text-slate-700 dark:text-slate-200" data-testid={`radacini-anunt-referinta-${l.id}`}>
          Preț de referință: <span className="font-semibold">{reference ?? "—"}</span>
        </p>
      </div>

      {showExchange && l.exchange_for && <p className="text-sm text-slate-600 dark:text-slate-300">Schimb pe: {l.exchange_for}</p>}

      <div className="flex flex-wrap items-center justify-between gap-2 mt-auto text-xs text-slate-600 dark:text-slate-300">
        <span>Vânzător: {l.seller_name || "—"}</span>
        {l.seller_rating && <Stars value={l.seller_rating.avg} count={l.seller_rating.count} testid={`radacini-anunt-rating-${l.id}`} />}
      </div>
    </Link>
  );
}

export default function Piata() {
  const [searchParams] = useSearchParams();
  const { meta, loading: metaLoading } = useMeta();
  const categories = optsOr(meta?.listing_categories, LISTING_CATEGORIES_FALLBACK);
  const units = optsOr(meta?.listing_units, LISTING_UNITS_FALLBACK);
  const localityParam = searchParams.get("locality");
  const [filters, setFilters] = useState({ locality: localityParam || ALL, category: ALL, mode: ALL });
  const [q, setQ] = useState("");
  const [qDebounced, setQDebounced] = useState("");
  const [state, setState] = useState({ loading: true, items: [], total: 0, error: null });
  const [moreLoading, setMoreLoading] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setQDebounced(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    radaciniApi
      .listings(buildParams(filters, qDebounced, 0))
      .then((d) => {
        if (!alive) return;
        const list = asList(d);
        setState({ loading: false, items: list, total: Number(d?.total ?? list.length), error: null });
      })
      .catch((error) => alive && setState((s) => ({ ...s, loading: false, error })));
    return () => {
      alive = false;
    };
  }, [filters, qDebounced]);

  const loadMore = async () => {
    setMoreLoading(true);
    try {
      const d = await radaciniApi.listings(buildParams(filters, qDebounced, state.items.length));
      const list = asList(d);
      setState((s) => ({ ...s, items: [...s.items, ...list], total: Number(d?.total ?? s.total) }));
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut încărca mai multe anunțuri"));
    } finally {
      setMoreLoading(false);
    }
  };

  const localityOpts = [{ id: ALL, label: "Toate localitățile" }, ...toOpts(meta?.localities || [])];
  const categoryOpts = [{ id: ALL, label: "Toate categoriile" }, ...categories];
  const modeOpts = [{ id: ALL, label: "Toate modurile" }, ...LISTING_MODES];
  const { loading, items, total, error } = state;

  return (
    <div className="space-y-5 max-w-5xl" data-testid="radacini-piata">
      <PageHeader
        title="Piață locală"
        subtitle="Produse de la membrii Rădăcini din zona ta."
        actions={
          <Link to="/radacini/piata/nou" className={linkBtnCls()} data-testid="radacini-piata-btn-nou">
            <Plus className="w-3.5 h-3.5" /> Publică un anunț
          </Link>
        }
      />

      <div className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-200" data-testid="radacini-piata-notice">
        {PICKUP_NOTICE}
      </div>

      {metaLoading ? null : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          <Field label="Localitate" htmlFor="piata-filtru-localitate">
            <SelectField
              id="piata-filtru-localitate"
              value={filters.locality}
              onValueChange={(v) => setFilters((f) => ({ ...f, locality: v }))}
              options={localityOpts}
              testid="radacini-piata-filtru-localitate"
            />
          </Field>
          <Field label="Categorie" htmlFor="piata-filtru-categorie">
            <SelectField
              id="piata-filtru-categorie"
              value={filters.category}
              onValueChange={(v) => setFilters((f) => ({ ...f, category: v }))}
              options={categoryOpts}
              testid="radacini-piata-filtru-categorie"
            />
          </Field>
          <Field label="Mod" htmlFor="piata-filtru-mod">
            <SelectField
              id="piata-filtru-mod"
              value={filters.mode}
              onValueChange={(v) => setFilters((f) => ({ ...f, mode: v }))}
              options={modeOpts}
              testid="radacini-piata-filtru-mod"
            />
          </Field>
          <Field label="Caută produs" htmlFor="piata-cautare">
            <Input id="piata-cautare" value={q} onChange={(e) => setQ(e.target.value)} placeholder="ex. roșii" maxLength={80} data-testid="radacini-piata-cautare" />
          </Field>
        </div>
      )}

      {loading && items.length === 0 ? (
        <PageSkeleton />
      ) : error ? (
        <EmptyState icon={AlertTriangle} title="Nu am putut încărca anunțurile" hint={errMsg(error)} testid="radacini-piata-error" />
      ) : items.length === 0 ? (
        <EmptyState icon={Store} title="Niciun anunț cu aceste filtre" hint="Încearcă alte filtre sau publică tu primul anunț." testid="radacini-piata-empty" />
      ) : (
        <>
          <p className="text-sm text-slate-500 dark:text-slate-400" data-testid="radacini-piata-total">
            {total} {total === 1 ? "anunț" : "anunțuri"}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" data-testid="radacini-piata-lista">
            {items.map((l) => (
              <ListingCard key={l.id} l={l} categories={categories} units={units} />
            ))}
          </div>
          {items.length < total && (
            <div className="flex justify-center">
              <DSButton variant="secondary" disabled={moreLoading} onClick={loadMore} data-testid="radacini-piata-mai-multe">
                {moreLoading ? "Se încarcă…" : "Încarcă mai multe"}
              </DSButton>
            </div>
          )}
        </>
      )}
    </div>
  );
}
