import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Tractor } from "lucide-react";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { Checkbox } from "../../../components/ui/checkbox";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import { asList, errMsg } from "../api";
import { s7Api } from "../api_s7";
import { useMeta } from "../hooks";
import { CheckGroup, Field, PageHeader, PageSkeleton, Stars, fmtArea, fmtPeriod, toOpts } from "../shared";
import { PRICE_NOTE, typeLabel, useServiceTypes } from "../components/project/ServiceTab";

function OfferDialog({ request, types, onClose, onSaved }) {
  const [price, setPrice] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    setPrice("");
    setMessage("");
  }, [request?.id]);
  const p = price === "" ? null : Number(price);
  const valid = message.trim().length >= 3 && (p === null || p >= 0);

  const send = async () => {
    if (!valid) return;
    setSaving(true);
    try {
      const body = { message: message.trim() };
      if (p !== null) body.price_ron_indicative = p;
      await s7Api.sendOffer(request.id, body);
      toast.success("Oferta a fost trimisă");
      onClose();
      onSaved();
    } catch (e) {
      toast.error(errMsg(e, "Oferta nu a putut fi trimisă"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={!!request} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-oferta-dialog">
        <DialogHeader>
          <DialogTitle>Trimite ofertă · {request && typeLabel(types, request.service_type)}</DialogTitle>
          <DialogDescription>{PRICE_NOTE}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <Field label="Preț orientativ (RON, opțional)" htmlFor="offer-price">
            <Input id="offer-price" type="number" min="0" step="any" value={price} onChange={(e) => setPrice(e.target.value)} data-testid="radacini-oferta-pret" />
          </Field>
          <Field label="Mesaj" htmlFor="offer-msg">
            <Textarea id="offer-msg" rows={3} maxLength={1000} value={message} onChange={(e) => setMessage(e.target.value)} data-testid="radacini-oferta-mesaj" />
          </Field>
        </div>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton variant="primary" disabled={!valid || saving} onClick={send} data-testid="radacini-oferta-trimite">
            {saving ? "Se trimite…" : "Trimite oferta"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Prestator() {
  const { meta } = useMeta();
  const types = useServiceTypes();
  const [state, setState] = useState({ loaded: false, provider: null });
  const [form, setForm] = useState({ services: [], localities: [], note: "", active: true });
  const [saving, setSaving] = useState(false);
  const [open, setOpen] = useState({ loaded: false, items: [] });
  const [tick, setTick] = useState(0);
  const [offerFor, setOfferFor] = useState(null);

  useEffect(() => {
    let alive = true;
    s7Api
      .providerMe()
      .then((d) => {
        if (!alive) return;
        const p = d?.provider || null;
        setState({ loaded: true, provider: p });
        if (p) setForm({ services: p.services || [], localities: p.localities || [], note: p.note || "", active: p.active !== false });
      })
      .catch((e) => {
        if (!alive) return;
        toast.error(errMsg(e, "Nu am putut încărca profilul"));
        setState({ loaded: true, provider: null });
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    s7Api
      .openServiceRequests()
      .then((d) => alive && setOpen({ loaded: true, items: asList(d) }))
      .catch(() => alive && setOpen({ loaded: true, items: [] }));
    return () => {
      alive = false;
    };
  }, [tick, state.provider]);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const valid = form.services.length > 0 && form.localities.length > 0;

  const save = async () => {
    if (!valid) return;
    setSaving(true);
    try {
      const d = await s7Api.saveProvider({ services: form.services, localities: form.localities, note: form.note.trim(), active: form.active });
      setState({ loaded: true, provider: d?.provider || d || {} });
      toast.success("Profilul de prestator a fost salvat");
    } catch (e) {
      toast.error(errMsg(e, "Profilul nu a putut fi salvat"));
    } finally {
      setSaving(false);
    }
  };

  if (!state.loaded) return <PageSkeleton />;
  const registered = !!state.provider;

  return (
    <div className="space-y-6 max-w-4xl" data-testid="radacini-prestator">
      <PageHeader title="Prestator" subtitle={`Oferă lucrări mecanizate proiectelor din zonă. ${PRICE_NOTE}`} />

      <section className={`${CARD} p-4 md:p-5 space-y-4`} data-testid="radacini-prestator-profil">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-bold text-slate-900 dark:text-white">{registered ? "Profilul meu" : "Devino prestator"}</h3>
          {registered && state.provider.rating_count > 0 && <Stars value={state.provider.rating_avg} count={state.provider.rating_count} testid="radacini-prestator-rating" />}
        </div>
        <Field label="Servicii oferite">
          <CheckGroup name="prest-srv" testid="radacini-prestator-servicii" options={types} value={form.services} onChange={set("services")} columns="sm:grid-cols-2 lg:grid-cols-3" />
        </Field>
        <Field label="Localități deservite">
          <CheckGroup name="prest-loc" testid="radacini-prestator-localitati" options={toOpts(meta?.localities || [])} value={form.localities} onChange={set("localities")} columns="sm:grid-cols-2 lg:grid-cols-3" />
        </Field>
        <Field label="Notă (echipamente, disponibilitate)" htmlFor="prest-note">
          <Textarea id="prest-note" rows={3} maxLength={500} value={form.note} onChange={(e) => set("note")(e.target.value)} data-testid="radacini-prestator-nota" />
        </Field>
        <label htmlFor="prest-active" className="flex items-center gap-2.5 text-sm text-slate-700 dark:text-slate-200 cursor-pointer">
          <Checkbox id="prest-active" checked={form.active} onCheckedChange={(v) => set("active")(!!v)} data-testid="radacini-prestator-activ" />
          Activ (primesc notificări pentru cereri potrivite)
        </label>
        <DSButton variant="primary" disabled={!valid || saving} onClick={save} data-testid="radacini-prestator-salveaza">
          {saving ? "Se salvează…" : registered ? "Salvează profilul" : "Mă înscriu ca prestator"}
        </DSButton>
      </section>

      {registered && (
        <section className="space-y-3" data-testid="radacini-prestator-cereri">
          <h3 className="font-bold text-slate-900 dark:text-white">Lucrări deschise pentru mine</h3>
          {!open.loaded ? (
            <PageSkeleton />
          ) : open.items.length === 0 ? (
            <EmptyState icon={Tractor} title="Nicio cerere potrivită acum" hint="Vei fi notificat când apare o cerere pentru serviciile și localitățile tale." testid="radacini-prestator-cereri-gol" />
          ) : (
            <ul className="space-y-3">
              {open.items.map((r) => (
                <li key={r.id} className={`${CARD} p-4 space-y-2`} data-testid={`radacini-prestator-cerere-${r.id}`}>
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-bold text-slate-900 dark:text-white">{typeLabel(types, r.service_type)}</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        {fmtPeriod(r.window_from, r.window_to)}
                        {r.area_m2 ? ` · ${fmtArea(r.area_m2)}` : ""}
                        {r.locality ? ` · ${r.locality}` : ""}
                      </p>
                    </div>
                    {r.my_offer ? (
                      <span className="inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200">Ofertă trimisă</span>
                    ) : (
                      <DSButton variant="primary" onClick={() => setOfferFor(r)} data-testid={`radacini-prestator-oferta-${r.id}`}>
                        Trimite ofertă
                      </DSButton>
                    )}
                  </div>
                  {r.description && <p className="text-sm text-slate-600 dark:text-slate-300 break-words">{r.description}</p>}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <OfferDialog request={offerFor} types={types} onClose={() => setOfferFor(null)} onSaved={() => setTick((t) => t + 1)} />
    </div>
  );
}
