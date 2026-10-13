import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Store } from "lucide-react";
import { useAuth } from "../../../auth";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import { radaciniApi, errMsg } from "../api";
import { useMeta } from "../hooks";
import {
  Field,
  LISTING_CATEGORIES_FALLBACK,
  LISTING_MODES,
  LISTING_UNITS_FALLBACK,
  PICKUP_NOTICE,
  PageSkeleton,
  SelectField,
  optsOr,
  todayIso,
  toOpts,
  isoToDateInput,
} from "../shared";

const EMPTY = {
  product: "",
  category: "altele",
  unit: "kg",
  quantity_total: "",
  price: "",
  mode: "sale",
  exchange_for: "",
  locality: "",
  pickup_details: "",
  available_until: "",
};

// Cu ?product=&qty=&unit=&project_id= din recoltă, formularul se pre-completează.
const fromQuery = (sp) => ({
  ...EMPTY,
  product: sp.get("product") || "",
  quantity_total: sp.get("qty") || "",
  unit: sp.get("unit") || "kg",
});

export default function AnuntForm() {
  const { id } = useParams();
  const editing = !!id;
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const { meta } = useMeta();
  const categories = optsOr(meta?.listing_categories, LISTING_CATEGORIES_FALLBACK);
  const units = optsOr(meta?.listing_units, LISTING_UNITS_FALLBACK);
  const localities = toOpts(meta?.localities || []);
  const projectId = !editing ? searchParams.get("project_id") : null;

  const [form, setForm] = useState(() => (editing ? EMPTY : fromQuery(searchParams)));
  const [original, setOriginal] = useState(null);
  const [loading, setLoading] = useState(editing);
  const [loadError, setLoadError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!editing) return undefined;
    let alive = true;
    setLoading(true);
    radaciniApi
      .listing(id)
      .then((l) => {
        if (!alive) return;
        setOriginal(l);
        setForm({
          product: l.product || "",
          category: l.category || "altele",
          unit: l.unit || "kg",
          quantity_total: l.quantity_total != null ? String(l.quantity_total) : "",
          price: l.price_ron_per_unit != null ? String(l.price_ron_per_unit) : "",
          mode: l.mode || "sale",
          exchange_for: l.exchange_for || "",
          locality: l.locality || "",
          pickup_details: l.pickup_details || "",
          available_until: isoToDateInput(l.available_until),
        });
        setLoading(false);
      })
      .catch((e) => {
        if (!alive) return;
        setLoadError(e);
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [id, editing]);

  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));
  const needsPrice = form.mode === "sale" || form.mode === "both";
  const needsExchange = form.mode === "exchange" || form.mode === "both";
  const qty = Number(form.quantity_total);
  const price = Number(form.price);
  // La editare, cantitatea totală nu poate scădea sub ce e deja rezervat sau confirmat.
  const reserved = original ? Math.max(0, Number(original.quantity_total || 0) - Number(original.quantity_available || 0)) : 0;
  const product = form.product.trim();
  const pickup = form.pickup_details.trim();
  const exchangeFor = form.exchange_for.trim();

  // Primul motiv pentru care formularul nu poate fi trimis (afișat lângă buton).
  const validationError = (() => {
    if (product.length < 2 || product.length > 80) return "Produsul trebuie să aibă între 2 și 80 de caractere.";
    if (!form.category) return "Alege categoria.";
    if (!form.unit) return "Alege unitatea.";
    if (!(qty > 0)) return "Cantitatea totală trebuie să fie mai mare decât 0.";
    if (qty < reserved) return `Cantitatea totală nu poate fi sub ${reserved} (deja rezervat sau confirmat).`;
    if (needsPrice && !(price > 0 && price <= 10000)) return "Prețul trebuie să fie între 0 și 10 000 RON.";
    if (needsExchange && (exchangeFor.length < 3 || exchangeFor.length > 300)) return "Descrie ce accepți în schimb (3–300 de caractere).";
    if (!form.locality) return "Alege localitatea.";
    if (pickup.length < 3 || pickup.length > 300) return "Detaliile de ridicare trebuie să aibă între 3 și 300 de caractere.";
    if (form.available_until && form.available_until < todayIso()) return "Data „Disponibil până la” nu poate fi în trecut.";
    return null;
  })();
  const valid = !validationError;

  const submit = async (e) => {
    e.preventDefault();
    if (!valid || saving) return;
    const body = {
      product,
      category: form.category,
      unit: form.unit,
      quantity_total: qty,
      mode: form.mode,
      locality: form.locality,
      pickup_details: pickup,
      price_ron_per_unit: needsPrice ? price : null,
      exchange_for: needsExchange ? exchangeFor : null,
      available_until: form.available_until || null,
    };
    setSaving(true);
    try {
      if (editing) {
        const l = await radaciniApi.updateListing(id, body);
        toast.success("Anunțul a fost salvat");
        navigate(`/radacini/piata/${l?.id || id}`);
      } else {
        if (projectId) body.project_id = projectId;
        const l = await radaciniApi.createListing(body);
        toast.success("Anunțul a fost publicat");
        navigate(`/radacini/piata/${l.id}`);
      }
    } catch (err) {
      toast.error(errMsg(err, "Anunțul nu a putut fi salvat"));
    } finally {
      setSaving(false);
    }
  };

  const back = (
    <Link to={editing ? `/radacini/piata/${id}` : "/radacini/piata"} className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline">
      <ArrowLeft className="w-4 h-4" /> {editing ? "Înapoi la anunț" : "Înapoi la piață"}
    </Link>
  );

  if (loading) {
    return (
      <div className="space-y-4">
        {back}
        <PageSkeleton />
      </div>
    );
  }

  if (editing && (loadError || !original || original.seller_user_id !== user?.id || original.status !== "active")) {
    return (
      <div className="space-y-4">
        {back}
        <EmptyState
          icon={Store}
          title="Nu poți edita acest anunț"
          hint={loadError ? errMsg(loadError) : "Doar vânzătorul poate edita un anunț activ."}
          testid="radacini-anunt-editare-indisponibila"
        />
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-3xl" data-testid="radacini-anunt-form">
      {back}
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">{editing ? "Editează anunțul" : "Anunț nou"}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{PICKUP_NOTICE}</p>
        {projectId && <p className="text-sm text-emerald-700 dark:text-emerald-300 mt-1">Anunțul se leagă de un proiect agricol din care faci parte.</p>}
      </div>

      <form onSubmit={submit} className={`${CARD} p-4 md:p-5 grid grid-cols-1 sm:grid-cols-2 gap-4`} data-testid="radacini-anunt-formular">
        <div className="sm:col-span-2">
          <Field label="Produs" htmlFor="anunt-produs">
            <Input id="anunt-produs" value={form.product} maxLength={80} onChange={(e) => set("product")(e.target.value)} placeholder="ex. Roșii Cherry" data-testid="radacini-anunt-produs-input" />
          </Field>
        </div>
        <Field label="Categorie" htmlFor="anunt-categorie">
          <SelectField id="anunt-categorie" value={form.category} onValueChange={set("category")} options={categories} testid="radacini-anunt-categorie" />
        </Field>
        <Field label="Unitate" htmlFor="anunt-unitate">
          <SelectField id="anunt-unitate" value={form.unit} onValueChange={set("unit")} options={units} testid="radacini-anunt-unitate" />
        </Field>
        <Field label="Cantitate totală" htmlFor="anunt-cantitate" hint={reserved > 0 ? `Nu poate fi sub ${reserved} (deja rezervat sau confirmat).` : undefined}>
          <Input id="anunt-cantitate" type="number" min="0" step="any" value={form.quantity_total} onChange={(e) => set("quantity_total")(e.target.value)} data-testid="radacini-anunt-cantitate-input" />
        </Field>
        <Field label="Mod" htmlFor="anunt-mod">
          <SelectField id="anunt-mod" value={form.mode} onValueChange={set("mode")} options={LISTING_MODES} testid="radacini-anunt-mod" />
        </Field>
        {needsPrice && (
          <Field label="Preț (RON / unitate)" htmlFor="anunt-pret" hint="Între 0 și 10 000 RON.">
            <Input id="anunt-pret" type="number" min="0" step="0.01" value={form.price} onChange={(e) => set("price")(e.target.value)} data-testid="radacini-anunt-pret" />
          </Field>
        )}
        {needsExchange && (
          <div className="sm:col-span-2">
            <Field label="Ce accepți în schimb" htmlFor="anunt-schimb" hint="Text liber, între 3 și 300 de caractere.">
              <Textarea id="anunt-schimb" value={form.exchange_for} maxLength={300} onChange={(e) => set("exchange_for")(e.target.value)} data-testid="radacini-anunt-schimb" />
            </Field>
          </div>
        )}
        <Field label="Localitate" htmlFor="anunt-localitate">
          <SelectField id="anunt-localitate" value={form.locality} onValueChange={set("locality")} options={localities} placeholder="Alege localitatea" testid="radacini-anunt-localitate" />
        </Field>
        <Field label="Disponibil până la (opțional)" htmlFor="anunt-pana-la">
          <Input id="anunt-pana-la" type="date" min={todayIso()} value={form.available_until} onChange={(e) => set("available_until")(e.target.value)} data-testid="radacini-anunt-pana-la" />
        </Field>
        <div className="sm:col-span-2">
          <Field label="Detalii de ridicare" htmlFor="anunt-ridicare" hint="Unde și când se ridică. Între 3 și 300 de caractere.">
            <Textarea id="anunt-ridicare" value={form.pickup_details} maxLength={300} onChange={(e) => set("pickup_details")(e.target.value)} data-testid="radacini-anunt-ridicare" />
          </Field>
        </div>

        <div className="sm:col-span-2 flex flex-wrap items-center justify-end gap-2">
          {validationError && (
            <p role="status" className="mr-auto text-xs font-semibold text-amber-700 dark:text-amber-300" data-testid="radacini-anunt-eroare-validare">
              {validationError}
            </p>
          )}
          <Link to={editing ? `/radacini/piata/${id}` : "/radacini/piata"} className="inline-flex items-center rounded-xl px-3 py-2 text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5">
            Renunță
          </Link>
          <DSButton type="submit" variant="primary" disabled={!valid || saving} data-testid="radacini-anunt-salveaza">
            {saving ? "Se salvează…" : editing ? "Salvează modificările" : "Publică anunțul"}
          </DSButton>
        </div>
      </form>
    </div>
  );
}
