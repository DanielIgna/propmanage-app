import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { AlertTriangle, ArrowLeftRight } from "lucide-react";
import { CARD, DSButton, EmptyState, TabBar } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { Textarea } from "../../../components/ui/textarea";
import { useConfirm } from "../components/ConfirmDialog";
import { radaciniApi, asList, errMsg } from "../api";
import { useMeta } from "../hooks";
import {
  Field,
  LISTING_UNITS_FALLBACK,
  PageHeader,
  PageSkeleton,
  RESERVATION_MODES_FALLBACK,
  ReservationBadge,
  fmtDateTime,
  labelOf,
  linkBtnCls,
  optsOr,
} from "../shared";

const TABS = [
  ["buyer", "Cumpăr"],
  ["seller", "Vând"],
];

// Evaluare 1–5 stele + comentariu (o singură dată, după ridicare).
function RateDialog({ reservation, onOpenChange, onDone }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (reservation) {
      setRating(0);
      setComment("");
    }
  }, [reservation]);

  const save = async () => {
    if (!reservation || rating < 1) return;
    setSaving(true);
    try {
      const body = { rating };
      if (comment.trim()) body.comment = comment.trim();
      await radaciniApi.rateReservation(reservation.id, body);
      toast.success("Mulțumim pentru evaluare");
      onOpenChange(false);
      onDone();
    } catch (e) {
      toast.error(errMsg(e, "Evaluarea nu a putut fi salvată"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={!!reservation} onOpenChange={onOpenChange}>
      <DialogContent data-testid="radacini-evaluare-dialog">
        <DialogHeader>
          <DialogTitle>Evaluează vânzătorul</DialogTitle>
          <DialogDescription>{reservation?.listing_product} · {reservation?.counterpart_name}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-center gap-1" role="radiogroup" aria-label="Notă">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                role="radio"
                aria-checked={rating === n}
                aria-label={`${n} ${n === 1 ? "stea" : "stele"}`}
                onClick={() => setRating(n)}
                data-testid={`radacini-evaluare-stea-${n}`}
                className={`text-3xl leading-none px-1 ${n <= rating ? "text-amber-500" : "text-slate-300 dark:text-slate-600"}`}
              >
                ★
              </button>
            ))}
          </div>
          <Field label="Comentariu (opțional)" htmlFor="evaluare-comentariu">
            <Textarea id="evaluare-comentariu" value={comment} maxLength={300} onChange={(e) => setComment(e.target.value)} data-testid="radacini-evaluare-comentariu" />
          </Field>
        </div>

        <DialogFooter>
          <DSButton variant="secondary" onClick={() => onOpenChange(false)} data-testid="radacini-evaluare-anuleaza">
            Renunță
          </DSButton>
          <DSButton variant="primary" disabled={rating < 1 || saving} onClick={save} data-testid="radacini-evaluare-salveaza">
            {saving ? "Se salvează…" : "Trimite evaluarea"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ReservationCard({ r, role, units, modes, busy, onAction, onRate }) {
  const isSeller = role === "seller";
  const unit = labelOf(units, r.listing_unit);
  const status = r.status;
  const actions = [];
  if (isSeller && status === "requested") {
    actions.push({ key: "confirm", label: "Confirmă", variant: "success", testid: "confirma", run: () => onAction(r, "confirm") });
    actions.push({ key: "decline", label: "Refuză", variant: "danger", testid: "refuza", run: () => onAction(r, "decline") });
  }
  if (isSeller && status === "confirmed") {
    actions.push({ key: "picked", label: "Ridicat", variant: "success", testid: "ridicat", run: () => onAction(r, "picked-up") });
    actions.push({ key: "noshow", label: "Nu s-a prezentat", variant: "danger", testid: "neprezentare", run: () => onAction(r, "no-show") });
  }
  // Anulează: cumpărătorul din requested/confirmed, vânzătorul din confirmed.
  if (status === "confirmed" || (!isSeller && status === "requested")) {
    actions.push({ key: "cancel", label: "Anulează", variant: "secondary", testid: "anuleaza", run: () => onAction(r, "cancel") });
  }
  if (!isSeller && status === "picked_up" && r.rating == null) {
    actions.push({ key: "rate", label: "Evaluează", variant: "primary", testid: "evalueaza", run: () => onRate(r) });
  }

  return (
    <li className={`${CARD} p-4 space-y-3`} data-testid={`radacini-rezervare-${r.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-bold text-slate-900 dark:text-white break-words">{r.listing_product}</p>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {Number(r.quantity || 0).toLocaleString("ro-RO")} {unit} · {isSeller ? "Cumpărător" : "Vânzător"}: {r.counterpart_name || "—"}
          </p>
        </div>
        <ReservationBadge status={status} testid={`radacini-rezervare-status-${r.id}`} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-slate-700 dark:text-slate-200">
        <p>Mod: {labelOf(modes, r.mode)}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 self-center">Creată: {fmtDateTime(r.created_at)}</p>
      </div>
      {r.exchange_offer && <p className="text-sm text-slate-700 dark:text-slate-200">Ce oferă în schimb: {r.exchange_offer}</p>}
      {r.message && <p className="text-sm text-slate-600 dark:text-slate-300 break-words">„{r.message}”</p>}
      {r.rating != null && (
        <p className="text-sm text-slate-700 dark:text-slate-200" data-testid={`radacini-rezervare-rating-${r.id}`}>
          Evaluare: <span className="text-amber-500">{"★".repeat(r.rating)}</span>
          <span className="text-slate-300 dark:text-slate-600">{"★".repeat(5 - r.rating)}</span>
          {r.rating_comment ? ` · ${r.rating_comment}` : ""}
        </p>
      )}

      {actions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {actions.map((a) => (
            <DSButton
              key={a.key}
              variant={a.variant}
              disabled={busy === r.id}
              onClick={a.run}
              data-testid={`radacini-rezervare-${a.testid}-${r.id}`}
            >
              {a.label}
            </DSButton>
          ))}
        </div>
      )}
    </li>
  );
}

export default function Rezervari() {
  const { meta } = useMeta();
  const [confirm, confirmDialog] = useConfirm();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") === "seller" ? "seller" : "buyer";
  const setTab = (t) => setSearchParams(t === "seller" ? { tab: t } : {}, { replace: true });
  const [state, setState] = useState({ loaded: false, items: [], error: null });
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(null);
  const [rateTarget, setRateTarget] = useState(null);
  const units = optsOr(meta?.listing_units, LISTING_UNITS_FALLBACK);
  const modes = optsOr(meta?.reservation_modes, RESERVATION_MODES_FALLBACK);

  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loaded: false, error: null }));
    radaciniApi
      .myReservations(tab)
      .then((d) => alive && setState({ loaded: true, items: asList(d), error: null }))
      .catch((error) => alive && setState({ loaded: true, items: [], error }));
    return () => {
      alive = false;
    };
  }, [tab, tick]);

  const refresh = () => setTick((t) => t + 1);

  // Acțiunile irevocabile cer confirmare; „Confirmă” (acceptarea) se face direct.
  const CONFIRM = {
    decline: { title: "Refuzi rezervarea?", description: "Cumpărătorul va fi anunțat.", confirmLabel: "Refuză", danger: true },
    cancel: { title: "Anulezi rezervarea?", description: "Dacă era confirmată, cantitatea revine în anunț.", confirmLabel: "Anulează", danger: true },
    "picked-up": { title: "Marchezi ca ridicată?", description: "Cantitatea rămâne scăzută din anunț.", confirmLabel: "Marchează" },
    "no-show": { title: "Marchezi neprezentare?", description: "Cantitatea revine în anunț.", confirmLabel: "Neprezentare", danger: true },
  };
  const FN = {
    confirm: radaciniApi.confirmReservation,
    decline: radaciniApi.declineReservation,
    cancel: radaciniApi.cancelReservation,
    "picked-up": radaciniApi.pickedUpReservation,
    "no-show": radaciniApi.noShowReservation,
  };
  const DONE = {
    confirm: "Rezervarea a fost confirmată",
    decline: "Rezervarea a fost refuzată",
    cancel: "Rezervarea a fost anulată",
    "picked-up": "Marcată ca ridicată",
    "no-show": "Marcată ca neprezentare",
  };

  const onAction = async (r, action) => {
    if (CONFIRM[action] && !(await confirm(CONFIRM[action]))) return;
    setBusy(r.id);
    try {
      await FN[action](r.id);
      toast.success(DONE[action]);
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Acțiunea nu a putut fi realizată"));
    } finally {
      setBusy(null);
    }
  };

  const { loaded, items, error } = state;

  return (
    <div className="space-y-5 max-w-4xl" data-testid="radacini-rezervari">
      <PageHeader title="Rezervări" subtitle="Rezervările pentru produsele pe care le cumperi sau le vinzi. Plata se face la ridicare." />

      <TabBar tabs={TABS} active={tab} onChange={setTab} testidPrefix="radacini-rezervari-tab" />

      {!loaded ? (
        <PageSkeleton />
      ) : error ? (
        <EmptyState icon={AlertTriangle} title="Nu am putut încărca rezervările" hint={errMsg(error)} testid="radacini-rezervari-error" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={ArrowLeftRight}
          title={tab === "buyer" ? "Nicio rezervare ca cumpărător" : "Nicio rezervare ca vânzător"}
          hint={tab === "buyer" ? "Rezervările tale apar aici după ce rezervi un produs din piață." : "Rezervările pentru anunțurile tale apar aici."}
          action={
            tab === "buyer" ? (
              <Link to="/radacini/piata" className={linkBtnCls("secondary")}>
                Mergi la piață
              </Link>
            ) : undefined
          }
          testid="radacini-rezervari-empty"
        />
      ) : (
        <ul className="space-y-3" data-testid="radacini-rezervari-lista">
          {items.map((r) => (
            <ReservationCard
              key={r.id}
              r={r}
              role={tab}
              units={units}
              modes={modes}
              busy={busy}
              onAction={onAction}
              onRate={setRateTarget}
            />
          ))}
        </ul>
      )}

      <RateDialog reservation={rateTarget} onOpenChange={(o) => !o && setRateTarget(null)} onDone={refresh} />
      {confirmDialog}
    </div>
  );
}
