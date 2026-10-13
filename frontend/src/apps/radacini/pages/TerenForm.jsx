import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { AlertTriangle } from "lucide-react";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import LocationPicker from "../components/LocationPicker";
import { radaciniApi, errMsg } from "../api";
import { useMeta } from "../hooks";
import {
  CheckGroup,
  COUNTY,
  Field,
  isoToDateInput,
  PageHeader,
  PageSkeleton,
  SelectField,
  StatusBadge,
  toOpts,
  linkBtnCls,
} from "../shared";

const EDITABLE_STATUS = ["draft", "rejected", "paused"];
const SUBMITTABLE_STATUS = ["draft", "rejected"];

const EMPTY = {
  title: "",
  locality: "",
  area_m2: "",
  access: "",
  water_sources: [],
  current_crops: "",
  description: "",
  availability_from: "",
  availability_to: "",
  location: null,
  models: [],
  harvest_share_percent: "",
  terms: "",
  price_ron_per_year: "",
};

const fromParcel = (p) => ({
  title: p.title || "",
  locality: p.locality || "",
  area_m2: p.area_m2 ?? "",
  access: p.access || "",
  water_sources: p.water_sources || [],
  current_crops: (p.current_crops || []).join(", "),
  description: p.description || "",
  availability_from: isoToDateInput(p.availability_from),
  availability_to: isoToDateInput(p.availability_to),
  location: p.lat != null && p.lng != null ? { lat: p.lat, lng: p.lng } : null,
  models: p.offer?.models || [],
  harvest_share_percent: p.offer?.harvest_share_percent ?? "",
  terms: p.offer?.terms || "",
  price_ron_per_year: p.offer?.price_ron_per_year ?? "",
});

// Validări client (aceleași reguli ca serverul; serverul rămâne sursa de adevăr).
const validate = (f) => {
  const t = f.title.trim();
  if (t.length < 3 || t.length > 120) return "Titlul trebuie să aibă între 3 și 120 de caractere.";
  if (!f.locality) return "Alege localitatea.";
  const area = Number(f.area_m2);
  if (!area || area < 100 || area > 10000000) return "Suprafața trebuie să fie între 100 și 10.000.000 m².";
  if (!f.location) return "Marchează terenul pe hartă.";
  if (!f.models.length) return "Alege cel puțin un model de ofertă.";
  if (f.models.includes("harvest_share")) {
    const h = Number(f.harvest_share_percent);
    if (!h || h < 1 || h > 90) return "Procentul din recoltă trebuie să fie între 1 și 90.";
  }
  return null;
};

const toBody = (f) => {
  const body = {
    title: f.title.trim(),
    county: COUNTY,
    locality: f.locality,
    lat: f.location.lat,
    lng: f.location.lng,
    area_m2: Number(f.area_m2),
    access: f.access.trim(),
    water_sources: f.water_sources,
    current_crops: f.current_crops.split(",").map((s) => s.trim()).filter(Boolean),
    description: f.description.trim(),
    offer: { models: f.models, terms: f.terms.trim() },
  };
  if (f.availability_from) body.availability_from = f.availability_from;
  if (f.availability_to) body.availability_to = f.availability_to;
  if (f.price_ron_per_year !== "" && f.price_ron_per_year != null) body.offer.price_ron_per_year = Number(f.price_ron_per_year);
  if (f.models.includes("harvest_share")) body.offer.harvest_share_percent = Number(f.harvest_share_percent);
  return body;
};

const Section = ({ title, children }) => (
  <section className={`${CARD} p-5 md:p-6 space-y-5`}>
    <h3 className="text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">{title}</h3>
    {children}
  </section>
);

export default function TerenForm() {
  const { id: routeId } = useParams();
  const navigate = useNavigate();
  const { meta, loading: metaLoading, error: metaError } = useMeta();
  const [editId, setEditId] = useState(routeId || null);
  const [status, setStatus] = useState("draft");
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(!!routeId);
  const [loadError, setLoadError] = useState(null);
  const [saving, setSaving] = useState(false);

  const isEdit = !!editId;
  const canEdit = !isEdit || EDITABLE_STATUS.includes(status);
  const canSubmit = !isEdit || SUBMITTABLE_STATUS.includes(status);
  const upd = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    if (!routeId) return undefined;
    let alive = true;
    radaciniApi
      .parcel(routeId)
      .then((p) => {
        if (!alive) return;
        setStatus(p.status);
        setForm(fromParcel(p));
      })
      .catch((e) => alive && setLoadError(e))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [routeId]);

  const persist = async ({ submit }) => {
    const err = validate(form);
    if (err) return toast.error(err);
    setSaving(true);
    let id = editId;
    try {
      const body = toBody(form);
      if (isEdit) {
        await radaciniApi.updateParcel(editId, body);
      } else {
        const created = await radaciniApi.createParcel(body);
        id = (created?.parcel ?? created)?.id;
        setEditId(id);
        setStatus("draft");
      }
      if (submit) {
        await radaciniApi.submitParcel(id);
        setStatus("pending_verification");
      }
      toast.success(submit ? "Trimis spre verificare" : "Ciorna a fost salvată");
      navigate("/radacini/terenurile-mele");
    } catch (e) {
      const msg = errMsg(e, "Nu am putut salva terenul");
      toast.error(id && submit ? `Ciorna a fost salvată, dar nu am putut trimite: ${msg}` : msg);
    } finally {
      setSaving(false);
    }
  };

  const back = (
    <Link to="/radacini/terenurile-mele" className="text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline">
      ← Înapoi la terenurile mele
    </Link>
  );

  if (metaLoading || loading) return <PageSkeleton />;
  if (metaError || !meta) {
    return <EmptyState icon={AlertTriangle} title="Nu am putut încărca formularul" hint={errMsg(metaError)} testid="radacini-teren-form-error" />;
  }
  if (loadError) {
    return (
      <div className="space-y-4">
        {back}
        <EmptyState icon={AlertTriangle} title="Terenul nu a fost găsit" hint={errMsg(loadError)} testid="radacini-teren-form-404" />
      </div>
    );
  }

  const headerTitle = isEdit ? "Editează terenul" : "Teren nou";

  if (!canEdit) {
    return (
      <div className="space-y-4 max-w-2xl">
        {back}
        <PageHeader title={headerTitle} />
        <div className={`${CARD} p-5 space-y-3`} data-testid="radacini-teren-blocat">
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-600 dark:text-slate-300">Stare:</span>
            <StatusBadge status={status} />
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {status === "pending_verification"
              ? "Terenul este în verificare și nu poate fi editat până la decizia operatorului."
              : "Terenul trebuie pus pe pauză înainte de editare."}
          </p>
          <Link to="/radacini/terenurile-mele" className={linkBtnCls("secondary")}>
            Înapoi la terenurile mele
          </Link>
        </div>
      </div>
    );
  }

  const models = meta.offer_models;
  const harvestChosen = form.models.includes("harvest_share");

  return (
    <div className="space-y-5 max-w-3xl" data-testid="radacini-teren-form">
      {back}
      <PageHeader
        title={headerTitle}
        subtitle="Completează detaliile și marchează locația pe hartă. Apoi salvează ciorna sau trimite-l spre verificare."
        actions={isEdit ? <StatusBadge status={status} testid="radacini-teren-form-status" /> : null}
      />

      <form
        className="space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          persist({ submit: false });
        }}
      >
        <Section title="Date generale">
          <Field label="Titlu" htmlFor="teren-titlu" hint="3–120 de caractere">
            <Input id="teren-titlu" maxLength={120} value={form.title} onChange={(e) => upd("title", e.target.value)} placeholder="ex. Teren lângă Florești, 1 ha" data-testid="radacini-form-title" />
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Localitate" htmlFor="teren-localitate">
              <SelectField
                id="teren-localitate"
                value={form.locality || undefined}
                onValueChange={(v) => upd("locality", v)}
                options={toOpts(meta.localities)}
                placeholder="Alege localitatea"
                testid="radacini-form-localitate"
              />
            </Field>
            <Field label="Județ">
              <Input value={COUNTY} disabled />
            </Field>
            <Field label="Suprafață (m²)" htmlFor="teren-suprafata" hint="Între 100 și 10.000.000 m²">
              <Input id="teren-suprafata" type="number" min={100} max={10000000} value={form.area_m2} onChange={(e) => upd("area_m2", e.target.value)} data-testid="radacini-form-suprafata" />
            </Field>
            <Field label="Acces" htmlFor="teren-acces" hint="opțional">
              <Input id="teren-acces" value={form.access} onChange={(e) => upd("access", e.target.value)} placeholder="ex. drum de pământ, 300 m de DN" />
            </Field>
          </div>

          <Field label="Surse de apă">
            <CheckGroup name="water" options={meta.water_sources} value={form.water_sources} onChange={(v) => upd("water_sources", v)} testid="radacini-form-apa" />
          </Field>

          <Field label="Culturi actuale" htmlFor="teren-culturi" hint="Separate prin virgulă. opțional">
            <Input id="teren-culturi" value={form.current_crops} onChange={(e) => upd("current_crops", e.target.value)} placeholder="ex. grâu, porumb" />
          </Field>

          <Field label="Descriere" htmlFor="teren-descriere" hint="opțional">
            <Textarea id="teren-descriere" rows={4} value={form.description} onChange={(e) => upd("description", e.target.value)} />
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Disponibil de la" htmlFor="teren-disp-de">
              <Input id="teren-disp-de" type="date" value={form.availability_from} onChange={(e) => upd("availability_from", e.target.value)} />
            </Field>
            <Field label="Disponibil până la" htmlFor="teren-disp-pana">
              <Input id="teren-disp-pana" type="date" value={form.availability_to} onChange={(e) => upd("availability_to", e.target.value)} />
            </Field>
          </div>
        </Section>

        <Section title="Locație">
          <LocationPicker value={form.location} onChange={(loc) => upd("location", loc)} />
        </Section>

        <Section title="Ofertă">
          <Field label="Model de ofertă" hint="Alege cel puțin unul.">
            <CheckGroup name="model" options={models} value={form.models} onChange={(v) => upd("models", v)} testid="radacini-form-model" columns="sm:grid-cols-1" />
          </Field>

          {harvestChosen && (
            <Field label="Procent din recoltă (%)" htmlFor="teren-recolta" hint="Între 1 și 90">
              <Input id="teren-recolta" type="number" min={1} max={90} value={form.harvest_share_percent} onChange={(e) => upd("harvest_share_percent", e.target.value)} data-testid="radacini-form-recolta" />
            </Field>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Preț (RON / an)" htmlFor="teren-pret" hint="opțional">
              <Input id="teren-pret" type="number" min={0} value={form.price_ron_per_year} onChange={(e) => upd("price_ron_per_year", e.target.value)} />
            </Field>
          </div>

          <Field label="Condiții" htmlFor="teren-conditii" hint="opțional">
            <Textarea id="teren-conditii" rows={3} value={form.terms} onChange={(e) => upd("terms", e.target.value)} placeholder="ex. durata, plata, cine suportă costurile de irigare" />
          </Field>
        </Section>

        <div className="sticky bottom-0 -mx-4 md:mx-0 px-4 md:px-0 py-3 bg-slate-50/95 dark:bg-[#0b0c0d]/95 backdrop-blur flex flex-wrap justify-end gap-2">
          <Link to="/radacini/terenurile-mele" className={linkBtnCls("secondary")}>
            Anulează
          </Link>
          <DSButton type="submit" variant="secondary" disabled={saving} data-testid="radacini-form-salveaza-ciorna">
            {saving ? "Se salvează…" : "Salvează ciorna"}
          </DSButton>
          {canSubmit && (
            <DSButton type="button" disabled={saving} onClick={() => persist({ submit: true })} data-testid="radacini-form-trimite">
              Salvează și trimite spre verificare
            </DSButton>
          )}
        </div>
      </form>
    </div>
  );
}
