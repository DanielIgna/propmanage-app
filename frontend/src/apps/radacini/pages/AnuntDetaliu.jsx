import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Pencil, Store, XCircle } from "lucide-react";
import { useAuth } from "../../../auth";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import { useConfirm } from "../components/ConfirmDialog";
import { radaciniApi, errMsg } from "../api";
import { useMeta } from "../hooks";
import {
  Field,
  LISTING_CATEGORIES_FALLBACK,
  LISTING_MODES,
  LISTING_UNITS_FALLBACK,
  PICKUP_NOTICE,
  PageSkeleton,
  RESERVATION_MODES_FALLBACK,
  ReservationBadge,
  SelectField,
  Stars,
  StatusBadge,
  allowedReservationModes,
  fmtDate,
  fmtPrice,
  labelOf,
  linkBtnCls,
  optsOr,
} from "../shared";

// Dialog de rezervare: cantitate, mod (limitat de anunț), ce oferi la schimb, mesaj.
function ReserveDialog({ open, onOpenChange, listing, reservationModes, onDone }) {
  const modes = allowedReservationModes(listing.mode);
  const modeOpts = reservationModes.filter((m) => modes.includes(m.id));
  const available = Number(listing.quantity_available || 0);
  const unit = listing.unit;
  const [form, setForm] = useState({ quantity: "", mode: modes[0], exchange_offer: "", message: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) setForm({ quantity: "", mode: allowedReservationModes(listing.mode)[0], exchange_offer: "", message: "" });
  }, [open, listing.id, listing.mode]);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const qty = Number(form.quantity);
  const isExchange = form.mode === "exchange";
  const valid =
    qty > 0 && qty <= available && !!form.mode && (!isExchange || form.exchange_offer.trim().length > 0);

  const save = async () => {
    if (!valid) return;
    setSaving(true);
    try {
      const body = { quantity: qty, mode: form.mode };
      if (isExchange) body.exchange_offer = form.exchange_offer.trim();
      if (form.message.trim()) body.message = form.message.trim();
      await radaciniApi.createReservation(listing.id, body);
      toast.success("Rezervarea a fost trimisă. Vânzătorul o va confirma.");
      onOpenChange(false);
      onDone();
    } catch (e) {
      toast.error(errMsg(e, "Rezervarea nu a putut fi trimisă"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="radacini-rezervare-dialog" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Rezervă {listing.product}</DialogTitle>
          <DialogDescription>
            Disponibil: {available.toLocaleString("ro-RO")} {labelOf(LISTING_UNITS_FALLBACK, unit)}. {PICKUP_NOTICE}
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 gap-4">
          <Field label={`Cantitate (${labelOf(LISTING_UNITS_FALLBACK, unit)})`} htmlFor="rezervare-cantitate">
            <Input
              id="rezervare-cantitate"
              type="number"
              min="0"
              step="any"
              max={available}
              value={form.quantity}
              onChange={(e) => set("quantity")(e.target.value)}
              data-testid="radacini-rezervare-cantitate"
            />
          </Field>
          <Field label="Mod de plată sau schimb" htmlFor="rezervare-mod">
            <SelectField
              id="rezervare-mod"
              value={form.mode}
              onValueChange={set("mode")}
              options={modeOpts}
              testid="radacini-rezervare-mod"
            />
          </Field>
          {isExchange && (
            <Field label="Ce oferi în schimb" htmlFor="rezervare-schimb" hint="Text liber. Nu există monedă internă sau sold de schimb.">
              <Textarea
                id="rezervare-schimb"
                value={form.exchange_offer}
                maxLength={300}
                onChange={(e) => set("exchange_offer")(e.target.value)}
                data-testid="radacini-rezervare-schimb"
              />
            </Field>
          )}
          <Field label="Mesaj pentru vânzător (opțional)" htmlFor="rezervare-mesaj">
            <Textarea id="rezervare-mesaj" value={form.message} maxLength={300} onChange={(e) => set("message")(e.target.value)} data-testid="radacini-rezervare-mesaj" />
          </Field>
        </div>

        <DialogFooter>
          <DSButton variant="secondary" onClick={() => onOpenChange(false)} data-testid="radacini-rezervare-anuleaza">
            Renunță
          </DSButton>
          <DSButton variant="primary" disabled={!valid || saving} onClick={save} data-testid="radacini-rezervare-trimite">
            {saving ? "Se trimite…" : "Trimite rezervarea"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function AnuntDetaliu() {
  const { id } = useParams();
  const { user } = useAuth();
  const { meta } = useMeta();
  const [confirm, confirmDialog] = useConfirm();
  const [state, setState] = useState({ loading: true, listing: null, error: null });
  const [tick, setTick] = useState(0);
  const [reserveOpen, setReserveOpen] = useState(false);
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true }));
    radaciniApi
      .listing(id)
      .then((listing) => alive && setState({ loading: false, listing, error: null }))
      .catch((error) => alive && setState({ loading: false, listing: null, error }));
    return () => {
      alive = false;
    };
  }, [id, tick]);

  const refresh = () => setTick((t) => t + 1);
  const back = (
    <Link to="/radacini/piata" className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline">
      <ArrowLeft className="w-4 h-4" /> Înapoi la piață
    </Link>
  );

  if (state.loading && !state.listing) {
    return (
      <div className="space-y-4">
        {back}
        <PageSkeleton />
      </div>
    );
  }

  const l = state.listing;
  if (state.error || !l) {
    return (
      <div className="space-y-4">
        {back}
        <EmptyState icon={Store} title="Anunțul nu există sau nu ai acces" hint={state.error ? errMsg(state.error) : undefined} testid="radacini-anunt-negasit" />
      </div>
    );
  }

  const isSeller = !!user && l.seller_user_id === user.id;
  const active = l.status === "active";
  const available = Number(l.quantity_available || 0);
  const myReservation = l.my_reservation || null;
  const canReserve = !!user && !isSeller && active && available > 0 && !myReservation;
  const unit = labelOf(optsOr(meta?.listing_units, LISTING_UNITS_FALLBACK), l.unit);
  const category = labelOf(optsOr(meta?.listing_categories, LISTING_CATEGORIES_FALLBACK), l.category);
  const price = fmtPrice(l.price_ron_per_unit, unit);
  const reference = fmtPrice(l.reference_price, unit);
  const rating = l.seller_rating;

  const close = async () => {
    if (
      !(await confirm({
        title: "Închizi anunțul?",
        description: "Rezervările în așteptare se anulează, iar cumpărătorii sunt anunțați.",
        confirmLabel: "Închide anunțul",
        danger: true,
      }))
    )
      return;
    setClosing(true);
    try {
      await radaciniApi.closeListing(l.id);
      toast.success("Anunțul a fost închis");
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Anunțul nu a putut fi închis"));
    } finally {
      setClosing(false);
    }
  };

  return (
    <div className="space-y-5 max-w-3xl" data-testid="radacini-anunt-detaliu">
      {back}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white break-words" data-testid="radacini-anunt-produs">
            {l.product}
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {l.locality} · {category}
          </p>
        </div>
        <StatusBadge status={l.status} testid="radacini-anunt-status" />
      </div>

      <section className={`${CARD} p-4 md:p-5 grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm`}>
        <div>
          <p className="text-xs text-slate-500 dark:text-slate-400">Disponibil</p>
          <p className="font-bold text-slate-900 dark:text-white" data-testid="radacini-anunt-disponibil">
            {available.toLocaleString("ro-RO")} din {Number(l.quantity_total || 0).toLocaleString("ro-RO")} {unit}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500 dark:text-slate-400">Mod</p>
          <p className="font-semibold text-slate-900 dark:text-white">{labelOf(LISTING_MODES, l.mode)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500 dark:text-slate-400">Preț</p>
          <p className="font-semibold text-slate-900 dark:text-white">{price ?? "Doar schimb"}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500 dark:text-slate-400">Preț de referință</p>
          <p className="font-semibold text-slate-900 dark:text-white" data-testid="radacini-anunt-referinta">
            {reference ?? "—"}
          </p>
        </div>
        {(l.mode === "exchange" || l.mode === "both") && l.exchange_for && (
          <div className="sm:col-span-2">
            <p className="text-xs text-slate-500 dark:text-slate-400">Schimb pe</p>
            <p className="text-slate-800 dark:text-slate-100">{l.exchange_for}</p>
          </div>
        )}
        <div className="sm:col-span-2">
          <p className="text-xs text-slate-500 dark:text-slate-400">Ridicare</p>
          <p className="text-slate-800 dark:text-slate-100 break-words">{l.pickup_details || "—"}</p>
        </div>
        {l.available_until && (
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">Disponibil până la</p>
            <p className="text-slate-800 dark:text-slate-100">{fmtDate(l.available_until)}</p>
          </div>
        )}
        <div>
          <p className="text-xs text-slate-500 dark:text-slate-400">Vânzător</p>
          <p className="text-slate-800 dark:text-slate-100">{l.seller_name || "—"}</p>
          {rating && <Stars value={rating.avg} count={rating.count} testid="radacini-anunt-vanzator-rating" />}
        </div>
      </section>

      <p className="text-xs text-slate-500 dark:text-slate-400">{PICKUP_NOTICE}</p>

      {!active && (
        <div className="rounded-xl border border-slate-200 dark:border-white/10 p-4 text-sm text-slate-600 dark:text-slate-300" data-testid="radacini-anunt-inchis">
          Anunțul este închis. Nu mai poate fi rezervat.
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {canReserve && (
          <DSButton variant="primary" onClick={() => setReserveOpen(true)} data-testid="radacini-anunt-btn-rezerva">
            Rezervă
          </DSButton>
        )}
        {isSeller && active && (
          <>
            <Link to={`/radacini/piata/${l.id}/editare`} className={linkBtnCls("secondary")} data-testid="radacini-anunt-btn-editeaza">
              <Pencil className="w-3.5 h-3.5" /> Editează
            </Link>
            <DSButton variant="danger" icon={XCircle} disabled={closing} onClick={close} data-testid="radacini-anunt-btn-inchide">
              {closing ? "Se închide…" : "Închide anunțul"}
            </DSButton>
          </>
        )}
        {isSeller && (
          <Link to="/radacini/rezervari?tab=seller" className={linkBtnCls("secondary")} data-testid="radacini-anunt-btn-rezervari">
            Vezi rezervările
          </Link>
        )}
        {myReservation && (
          <div className="flex flex-wrap items-center gap-2" data-testid="radacini-anunt-rezervarea-mea">
            <span className="text-sm text-slate-600 dark:text-slate-300">Ai deja o rezervare:</span>
            <ReservationBadge status={myReservation.status} testid="radacini-anunt-rezervare-status" />
            <Link to="/radacini/rezervari?tab=buyer" className={linkBtnCls("secondary")} data-testid="radacini-anunt-btn-rezervarea-mea">
              Vezi rezervarea
            </Link>
          </div>
        )}
        {!user && <p className="text-sm text-slate-500 dark:text-slate-400">Autentifică-te pentru a rezerva.</p>}
      </div>

      {canReserve && (
        <ReserveDialog
          open={reserveOpen}
          onOpenChange={setReserveOpen}
          listing={l}
          reservationModes={optsOr(meta?.reservation_modes, RESERVATION_MODES_FALLBACK)}
          onDone={refresh}
        />
      )}
      {confirmDialog}
    </div>
  );
}
