import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ClipboardCheck, MapPin, Store, XCircle } from "lucide-react";
import { DataTable, DSButton } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Textarea } from "../../../../components/ui/textarea";
import { errMsg, radaciniApi } from "../../api";
import { useMeta } from "../../hooks";
import {
  fmtArea, fmtDate, fmtPrice, labelOf, LISTING_MODES, linkBtnCls, SelectField, StatusBadge, toOpts,
} from "../../shared";
import { clean, ErrorBox, nf, TabSkeleton, usePaged } from "./adminShared";

const PARCEL_STATUS_OPTS = [
  { id: "all", label: "Toate stările" },
  { id: "pending_verification", label: "În verificare" },
  { id: "published", label: "Publicate" },
  { id: "draft", label: "Ciorne" },
  { id: "paused", label: "În pauză" },
  { id: "rejected", label: "Respinse" },
];
const LISTING_STATUS_OPTS = [
  { id: "active", label: "Active" },
  { id: "closed", label: "Închise" },
  { id: "all", label: "Toate" },
];
const PAGE = 50;
const REASON_MIN = 3;
const REASON_MAX = 300;

const SectionHead = ({ icon: Icon, title, children }) => (
  <div className="flex flex-wrap items-center justify-between gap-2">
    <h3 className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
      <Icon className="w-4 h-4 text-emerald-600" aria-hidden="true" /> {title}
    </h3>
    {children}
  </div>
);

const MoreButton = ({ hasMore, loading, failed, onClick, testid }) => (
  <>
    {failed && (
      <p className="text-sm text-rose-600 dark:text-rose-400" role="alert">
        Nu am putut încărca rândurile următoare.
      </p>
    )}
    {hasMore && (
      <div className="flex justify-center">
        <DSButton variant="secondary" disabled={loading} onClick={onClick} data-testid={testid}>
          {loading ? "Se încarcă…" : "Încarcă mai multe"}
        </DSButton>
      </div>
    )}
  </>
);

function ParcelsSection() {
  const { meta } = useMeta();
  const [status, setStatus] = useState("pending_verification");
  const [locality, setLocality] = useState("all");
  const { rows, total, loading, loadingMore, error, moreError, hasMore, loadMore, reload } = usePaged(
    (skip) => radaciniApi.adminParcels(clean({ status, locality, skip: skip || "", limit: PAGE })),
    [status, locality],
    { pageSize: PAGE }
  );

  const columns = [
    {
      key: "title",
      label: "Teren",
      render: (r) => (
        <Link to={`/radacini/terenuri/${r.id}`} className="font-semibold text-emerald-700 dark:text-emerald-300 hover:underline">
          {r.title || "Teren fără titlu"}
        </Link>
      ),
    },
    { key: "locality", label: "Localitate", render: (r) => r.locality || "—" },
    { key: "area_m2", label: "Suprafață", render: (r) => fmtArea(r.area_m2) },
    { key: "status", label: "Stare", render: (r) => <StatusBadge status={r.status} /> },
    { key: "owner_name", label: "Proprietar", render: (r) => r.owner_name || "—" },
    { key: "updated_at", label: "Actualizat", render: (r) => fmtDate(r.updated_at) },
  ];

  return (
    <section className="space-y-3" data-testid="radacini-admin-moderare-parcels">
      <SectionHead icon={MapPin} title="Terenuri">
        <Link to="/radacini/operator" className={linkBtnCls("secondary")} data-testid="radacini-admin-open-operator">
          <ClipboardCheck className="w-3.5 h-3.5" /> Coada operatorului
        </Link>
      </SectionHead>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:max-w-xl">
        <SelectField value={status} onValueChange={setStatus} options={PARCEL_STATUS_OPTS} testid="radacini-admin-parcels-status" />
        <SelectField
          value={locality}
          onValueChange={setLocality}
          options={[{ id: "all", label: "Toate localitățile" }, ...toOpts(meta?.localities || [])]}
          testid="radacini-admin-parcels-locality"
        />
      </div>
      {loading && rows.length === 0 && !error ? (
        <TabSkeleton />
      ) : error ? (
        <ErrorBox title="Nu am putut încărca terenurile" error={error} onRetry={reload} testid="radacini-admin-parcels-error" />
      ) : (
        <>
          <DataTable
            title={`${nf(total ?? rows.length)} ${(total ?? rows.length) === 1 ? "teren" : "terenuri"}`}
            columns={columns}
            rows={rows}
            searchKeys={["title", "locality", "owner_name"]}
            emptyTitle="Niciun teren pentru aceste filtre"
            emptyHint="Schimbă starea sau localitatea."
            maxHeight="26rem"
            testid="radacini-admin-parcels-table"
          />
          <MoreButton hasMore={hasMore} loading={loadingMore} failed={moreError} onClick={loadMore} testid="radacini-admin-parcels-more" />
        </>
      )}
    </section>
  );
}

function ListingsSection() {
  const { meta } = useMeta();
  const [status, setStatus] = useState("active");
  const { rows, total, loading, loadingMore, error, moreError, hasMore, loadMore, reload } = usePaged(
    (skip) => radaciniApi.adminListings(clean({ status, skip: skip || "", limit: PAGE })),
    [status],
    { pageSize: PAGE }
  );
  const [closing, setClosing] = useState(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const trimmed = reason.trim();
  const valid = trimmed.length >= REASON_MIN && trimmed.length <= REASON_MAX;

  const close = async () => {
    if (!closing || !valid) return;
    setBusy(true);
    try {
      const res = await radaciniApi.adminCloseListing(closing.id, trimmed);
      const n = res?.cancelled_reservations || 0;
      toast.success(n ? `Anunț închis. Vânzătorul a fost notificat; ${n} ${n === 1 ? "rezervare anulată" : "rezervări anulate"}.` : "Anunț închis. Vânzătorul a fost notificat.");
      setClosing(null);
      setReason("");
      reload();
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut închide anunțul"));
    } finally {
      setBusy(false);
    }
  };

  const catLabel = (id) => labelOf(meta?.listing_categories, id);
  const columns = [
    {
      key: "product",
      label: "Produs",
      render: (r) => (
        <Link to={`/radacini/piata/${r.id}`} className="font-semibold text-emerald-700 dark:text-emerald-300 hover:underline">
          {r.product || r.title || "Anunț"}
        </Link>
      ),
    },
    { key: "category", label: "Categorie", render: (r) => catLabel(r.category) || "—" },
    {
      key: "quantity_available",
      label: "Disponibil",
      render: (r) => `${nf(r.quantity_available)} / ${nf(r.quantity_total)} ${r.unit || ""}`.trim(),
    },
    { key: "price_ron_per_unit", label: "Preț", render: (r) => fmtPrice(r.price_ron_per_unit, r.unit) || "—" },
    { key: "mode", label: "Mod", render: (r) => labelOf(LISTING_MODES, r.mode) || "—" },
    { key: "locality", label: "Localitate", render: (r) => r.locality || "—" },
    { key: "seller_name", label: "Vânzător", render: (r) => r.seller_name || "—" },
    { key: "created_at", label: "Publicat", render: (r) => fmtDate(r.created_at) },
    { key: "status", label: "Stare", render: (r) => <StatusBadge status={r.status} /> },
    {
      key: "actions",
      label: "",
      sortable: false,
      render: (r) =>
        r.status === "active" ? (
          <DSButton
            variant="danger"
            icon={XCircle}
            onClick={() => {
              setClosing(r);
              setReason("");
            }}
            data-testid={`radacini-admin-listing-close-${r.id}`}
          >
            Închide anunțul
          </DSButton>
        ) : null,
    },
  ];

  return (
    <section className="space-y-3" data-testid="radacini-admin-moderare-listings">
      <SectionHead icon={Store} title="Anunțuri din piață">
        <div className="w-full sm:w-44">
          <SelectField value={status} onValueChange={setStatus} options={LISTING_STATUS_OPTS} testid="radacini-admin-listings-status" />
        </div>
      </SectionHead>
      {loading && rows.length === 0 && !error ? (
        <TabSkeleton />
      ) : error ? (
        <ErrorBox title="Nu am putut încărca anunțurile" error={error} onRetry={reload} testid="radacini-admin-listings-error" />
      ) : (
        <>
          <DataTable
            title={`${nf(total ?? rows.length)} ${(total ?? rows.length) === 1 ? "anunț" : "anunțuri"}`}
            columns={columns}
            rows={rows}
            searchKeys={["product", "locality", "seller_name"]}
            emptyTitle={status === "active" ? "Niciun anunț activ" : "Niciun anunț pentru acest filtru"}
            emptyHint="Anunțurile apar când membrii publică produse în piață."
            maxHeight="26rem"
            testid="radacini-admin-listings-table"
          />
          <MoreButton hasMore={hasMore} loading={loadingMore} failed={moreError} onClick={loadMore} testid="radacini-admin-listings-more" />
        </>
      )}

      <Dialog open={!!closing} onOpenChange={(open) => !open && !busy && setClosing(null)}>
        <DialogContent data-testid="radacini-admin-close-dialog">
          <DialogHeader>
            <DialogTitle>Închizi anunțul?</DialogTitle>
            <DialogDescription>
              {closing?.product ? `„${closing.product}”` : "Anunțul"} nu va mai putea fi rezervat
              {closing?.pending_reservations > 0 ? `, iar ${closing.pending_reservations} ${closing.pending_reservations === 1 ? "rezervare în așteptare va fi anulată" : "rezervări în așteptare vor fi anulate"}` : ""}. Scrie motivul: vânzătorul îl primește prin notificare și rămâne în jurnalul de audit.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Textarea
              rows={4}
              maxLength={REASON_MAX}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="ex. anunțul încalcă regulile pieței locale."
              aria-label="Motivul închiderii"
              data-testid="radacini-admin-close-reason"
            />
            <p className={`text-xs ${trimmed.length > 0 && !valid ? "text-rose-600 dark:text-rose-400" : "text-slate-500 dark:text-slate-400"}`}>
              {trimmed.length}/{REASON_MAX} · minimum {REASON_MIN} caractere
            </p>
          </div>
          <DialogFooter>
            <DSButton variant="secondary" disabled={busy} onClick={() => setClosing(null)} data-testid="radacini-admin-close-cancel">
              Renunță
            </DSButton>
            <DSButton variant="danger" disabled={!valid || busy} onClick={close} data-testid="radacini-admin-close-confirm">
              {busy ? "Se închide…" : "Închide anunțul"}
            </DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

export default function Moderare() {
  return (
    <div className="space-y-8" data-testid="radacini-admin-moderare">
      <ParcelsSection />
      <ListingsSection />
    </div>
  );
}
