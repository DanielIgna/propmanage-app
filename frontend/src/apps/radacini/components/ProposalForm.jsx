import React, { useState } from "react";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import { DSButton } from "../../../design-system";
import { Field, fmtArea, isoToDateInput, SelectField } from "../shared";

// Formularul de propunere (cerere, contrapropunere, termenii acordului) — o singură sursă de adevăr.
// Starea e în formă de formular (stringuri); buildProposal o transformă în corpul din API.

export const proposalToForm = (proposal = {}, model = "") => ({
  model: model || proposal.model || "",
  area_m2: proposal.area_m2 ?? "",
  start_date: isoToDateInput(proposal.start_date),
  end_date: isoToDateInput(proposal.end_date),
  price_ron_per_year: proposal.price_ron_per_year ?? "",
  harvest_share_percent: proposal.harvest_share_percent ?? "",
  crops: (proposal.crops || []).join(", "),
  note: proposal.note || "",
  custom_clauses: proposal.custom_clauses || "",
});

const isBlank = (v) => v === "" || v == null;

// Validare de bază în UI (regulile finale le aplică backend-ul; erorile lui apar ca toast).
// includeModel=false pentru acorduri (modelul e fix). Returnează {body} sau {error}.
export function buildProposal(f, { includeModel = true, withNote = true, withClauses = false, areaMax } = {}) {
  if (includeModel && !f.model) return { error: "Alege modelul de colaborare." };

  const area = Number(f.area_m2);
  if (isBlank(f.area_m2) || !Number.isFinite(area)) return { error: "Introdu suprafața în m²." };
  if (area < 100) return { error: "Suprafața minimă este de 100 m²." };
  if (areaMax && area > areaMax) return { error: `Suprafața nu poate depăși ${fmtArea(areaMax)}.` };

  if (!f.start_date || !f.end_date) return { error: "Completează perioada colaborării." };
  if (f.end_date <= f.start_date) return { error: "Data de sfârșit trebuie să fie după data de început." };

  const body = {
    area_m2: area,
    start_date: f.start_date,
    end_date: f.end_date,
    crops: String(f.crops || "")
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean),
  };
  if (includeModel) body.model = f.model;

  if (!isBlank(f.price_ron_per_year)) {
    const price = Number(f.price_ron_per_year);
    if (!Number.isFinite(price) || price < 0) return { error: "Prețul nu este valid." };
    body.price_ron_per_year = price;
  }

  if (f.model === "harvest_share") {
    const share = Number(f.harvest_share_percent);
    if (isBlank(f.harvest_share_percent) || !Number.isFinite(share) || share < 1 || share > 90) {
      return { error: "Procentul din recoltă trebuie să fie între 1 și 90." };
    }
    body.harvest_share_percent = share;
  }

  if (withNote && f.note.trim()) body.note = f.note.trim();
  if (withClauses) body.custom_clauses = (f.custom_clauses || "").trim();

  return { body };
}

export default function ProposalForm({
  idPrefix = "prop",
  testidPrefix = "radacini-prop",
  models = [], // [{id,label}] — din oferta terenului, cu etichete din meta
  lockedModel = null, // acorduri: modelul nu se schimbă, câmpul nu apare
  areaMax, // suprafața terenului (sau a termenilor acordului)
  initial, // formă de formular (vezi proposalToForm)
  showNote = true,
  showClauses = false,
  submitLabel = "Trimite",
  submitting = false,
  onSubmit, // (body) => void
  onCancel,
}) {
  const [f, setF] = useState(() => ({
    ...proposalToForm({}, lockedModel || models[0]?.id || ""),
    ...(initial || {}),
    model: lockedModel || initial?.model || models[0]?.id || "",
  }));
  const [error, setError] = useState(null);
  const upd = (k, v) => setF((s) => ({ ...s, [k]: v }));
  const includeModel = !lockedModel;

  const submit = (e) => {
    e.preventDefault();
    const r = buildProposal(f, { includeModel, withNote: showNote, withClauses: showClauses, areaMax });
    if (r.error) {
      setError(r.error);
      return;
    }
    setError(null);
    onSubmit?.(r.body);
  };

  const id = (s) => `${idPrefix}-${s}`;
  const tid = (s) => `${testidPrefix}-${s}`;

  return (
    <form onSubmit={submit} className="space-y-4" data-testid={testidPrefix} noValidate>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {includeModel && (
          <Field label="Model de colaborare" htmlFor={id("model")}>
            <SelectField
              id={id("model")}
              value={f.model}
              onValueChange={(v) => upd("model", v)}
              options={models}
              placeholder="Alege modelul"
              testid={tid("model")}
            />
          </Field>
        )}

        <Field label="Suprafață (m²)" htmlFor={id("area")} hint={areaMax ? `Între 100 m² și ${fmtArea(areaMax)}.` : "Minimum 100 m²."}>
          <Input
            id={id("area")}
            type="number"
            min={100}
            max={areaMax || undefined}
            value={f.area_m2}
            onChange={(e) => upd("area_m2", e.target.value)}
            data-testid={tid("area")}
          />
        </Field>

        <Field label="Data de început" htmlFor={id("start")}>
          <Input id={id("start")} type="date" value={f.start_date} onChange={(e) => upd("start_date", e.target.value)} data-testid={tid("start")} />
        </Field>

        <Field label="Data de sfârșit" htmlFor={id("end")}>
          <Input id={id("end")} type="date" value={f.end_date} onChange={(e) => upd("end_date", e.target.value)} data-testid={tid("end")} />
        </Field>

        <Field label="Preț (RON / an)" htmlFor={id("price")} hint="Opțional.">
          <Input
            id={id("price")}
            type="number"
            min={0}
            value={f.price_ron_per_year}
            onChange={(e) => upd("price_ron_per_year", e.target.value)}
            data-testid={tid("price")}
          />
        </Field>

        {f.model === "harvest_share" && (
          <Field label="Parte din recoltă (%)" htmlFor={id("share")} hint="Între 1% și 90%.">
            <Input
              id={id("share")}
              type="number"
              min={1}
              max={90}
              value={f.harvest_share_percent}
              onChange={(e) => upd("harvest_share_percent", e.target.value)}
              data-testid={tid("share")}
            />
          </Field>
        )}

        <Field label="Culturi" htmlFor={id("crops")} hint="Separate prin virgulă, ex. grâu, porumb.">
          <Input id={id("crops")} value={f.crops} onChange={(e) => upd("crops", e.target.value)} placeholder="ex. grâu, porumb" data-testid={tid("crops")} />
        </Field>
      </div>

      {showNote && (
        <Field label="Mesaj (opțional)" htmlFor={id("note")}>
          <Textarea id={id("note")} rows={3} maxLength={1000} value={f.note} onChange={(e) => upd("note", e.target.value)} data-testid={tid("note")} />
        </Field>
      )}

      {showClauses && (
        <Field label="Clauze suplimentare" htmlFor={id("clauses")} hint="Maximum 5000 de caractere.">
          <Textarea
            id={id("clauses")}
            rows={5}
            maxLength={5000}
            value={f.custom_clauses}
            onChange={(e) => upd("custom_clauses", e.target.value)}
            data-testid={tid("clauses")}
          />
        </Field>
      )}

      {error && (
        <p role="alert" className="text-sm font-semibold text-rose-600 dark:text-rose-400" data-testid={tid("error")}>
          {error}
        </p>
      )}

      <div className="flex flex-wrap justify-end gap-2 pt-1">
        {onCancel && (
          <DSButton type="button" variant="secondary" onClick={onCancel} data-testid={tid("cancel")}>
            Anulează
          </DSButton>
        )}
        <DSButton type="submit" variant="primary" disabled={submitting} data-testid={tid("submit")}>
          {submitLabel}
        </DSButton>
      </div>
    </form>
  );
}
