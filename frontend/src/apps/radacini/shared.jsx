import React from "react";
import { Checkbox } from "../../components/ui/checkbox";
import { Label } from "../../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { BUTTON_STYLES, DSSkeleton } from "../../design-system";

export const COUNTY = "Cluj";

export const STATUS = {
  draft: { label: "Ciornă", cls: "bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-200" },
  pending_verification: { label: "În verificare", cls: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  published: { label: "Publicat", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  rejected: { label: "Respins", cls: "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300" },
  paused: { label: "Pauză", cls: "bg-sky-50 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300" },
  // Cereri de teren (S2)
  sent: { label: "Trimisă", cls: "bg-sky-50 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300" },
  viewed: { label: "Văzută", cls: "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300" },
  negotiating: { label: "În negociere", cls: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  accepted: { label: "Acceptată", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  declined: { label: "Refuzată", cls: "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300" },
  withdrawn: { label: "Retrasă", cls: "bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300" },
  expired: { label: "Expirată", cls: "bg-slate-100 text-slate-500 dark:bg-white/10 dark:text-slate-400" },
  // Acorduri (S2): „draft" = Ciornă, deja în STATUS
  proposed: { label: "Trimis spre semnare", cls: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  signed: { label: "Semnat", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  cancelled: { label: "Anulat", cls: "bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300" },
  // Proiecte (S3)
  active: { label: "Activ", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  completed: { label: "Finalizat", cls: "bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-200" },
  planned: { label: "Planificată", cls: "bg-sky-50 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300" },
  sown: { label: "Semănată", cls: "bg-lime-50 text-lime-700 dark:bg-lime-500/15 dark:text-lime-300" },
  growing: { label: "În creștere", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  harvested: { label: "Recoltată", cls: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  scheduled: { label: "Programată", cls: "bg-sky-50 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300" },
  done: { label: "Făcută", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  logged: { label: "În așteptare", cls: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  confirmed: { label: "Confirmată", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  disputed: { label: "Contestată", cls: "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300" },
  // Recoltă și alocare (S4). „confirmed" e deja în listă (Confirmată).
  recorded: { label: "Înregistrată", cls: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  allocated: { label: "Alocat", cls: "bg-sky-50 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300" },
  received: { label: "Primit", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  // Piață (S4): „cancelled" are alt sens la rezervări, vezi RESERVATION_STATUS.
  closed: { label: "Închis", cls: "bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300" },
  requested: { label: "Cerută", cls: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  picked_up: { label: "Ridicată", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  no_show: { label: "Neprezentare", cls: "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300" },
};

export const PROJECT_ROLE = {
  owner: { label: "Proprietar", cls: "bg-violet-50 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300" },
  coordinator: { label: "Coordonator", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  participant: { label: "Participant", cls: "bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-200" },
};

export const RoleBadge = ({ role, testid }) => {
  const r = PROJECT_ROLE[role] || { label: role || "—", cls: "bg-slate-100 text-slate-600" };
  return (
    <span data-testid={testid} className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-bold whitespace-nowrap ${r.cls}`}>
      {r.label}
    </span>
  );
};

export const ACTIVITY_TYPES = [
  { id: "planting", label: "Plantare" },
  { id: "maintenance", label: "Întreținere" },
  { id: "irrigation", label: "Irigare" },
  { id: "harvest", label: "Recoltare" },
  { id: "work_day", label: "Zi de lucru" },
  { id: "other", label: "Altele" },
];

export const CONTRIBUTION_KINDS = [
  { id: "labor_hours", label: "Muncă (ore)", unit: "ore" },
  { id: "materials", label: "Materiale", unit: "buc" },
  { id: "money", label: "Bani cheltuiți", unit: "RON" },
  { id: "tools", label: "Unelte", unit: "buc" },
  { id: "land", label: "Teren", unit: "m²" },
];

// Unitățile forțate de backend (nu se pot schimba).
export const FORCED_UNIT = { labor_hours: "ore", money: "RON" };

export const CROP_STATUSES = [
  { id: "planned", label: "Planificată" },
  { id: "sown", label: "Semănată" },
  { id: "growing", label: "În creștere" },
  { id: "harvested", label: "Recoltată" },
];

export const PROJECT_TABS = [
  ["prezentare", "Prezentare"],
  ["plan", "Plan culturi"],
  ["calendar", "Calendar"],
  ["contributii", "Contribuții"],
  ["recolta", "Recoltă"],
  ["membri", "Membri"],
];

export const PROJECT_DISCLAIMER =
  "Contribuțiile sunt o evidență a implicării. Nu reprezintă bani, puncte sau drepturi asupra recoltei; împărțirea recoltei urmează acordul semnat.";

// Contoarele din GET /projects (counters = {crops, upcoming_activities, pending_contributions}).
export const counterOf = (p, key) => p?.counts?.[key] ?? 0;

// Opțiuni {id,label} din meta (dacă există), altfel valorile implicite.
export const optsOr = (fromMeta, fallback) =>
  Array.isArray(fromMeta) && fromMeta.length ? fromMeta.map((x) => ({ id: x.id, label: x.label })) : fallback;

// Ziua de azi ca "YYYY-MM-DD" (ora locală), pentru input type=date.
export const todayIso = () => {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

// Cereri încă active (negociabile); celelalte stări sunt finale.
export const ACTIVE_REQUEST = ["sent", "viewed", "negotiating"];

export const ROLE_LABEL = { owner: "Proprietar", cultivator: "Cultivator" };

// Semnătura contează doar pentru versiunea curentă; o modificare resetează semnăturile în backend.
export const signedFor = (a, userId) => (a?.signatures || []).some((s) => s.user_id === userId && s.version === a.version);
export const signedCount = (a) => (a?.parties || []).filter((p) => signedFor(a, p.user_id)).length;

export const fmtRon = (v) => (v == null || v === "" ? null : `${Number(v).toLocaleString("ro-RO")} RON / an`);
export const fmtPeriod = (from, to) => `${fmtDate(from)} – ${fmtDate(to)}`;
export const fmtDateTime = (iso) =>
  iso ? new Date(iso).toLocaleString("ro-RO", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

export const ROLES = [
  { id: "operator", label: "Operator" },
  { id: "manager", label: "Manager" },
];

export const StatusBadge = ({ status, testid }) => {
  const s = STATUS[status] || { label: status || "—", cls: "bg-slate-100 text-slate-600" };
  return (
    <span data-testid={testid} className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-bold whitespace-nowrap ${s.cls}`}>
      {s.label}
    </span>
  );
};

export const labelOf = (list, id) => list?.find((x) => x.id === id)?.label ?? id;

// Listele de stringuri (localități) → opțiuni {id,label}.
export const toOpts = (arr = []) => arr.map((x) => (typeof x === "string" ? { id: x, label: x } : x));

export const linkBtnCls = (variant = "primary") =>
  `inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold transition-colors ${BUTTON_STYLES[variant]}`;

export const fmtArea = (m2) => `${Number(m2 || 0).toLocaleString("ro-RO")} m²`;
export const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString("ro-RO") : "—");
// Backend-ul păstrează disponibilitatea ca "YYYY-MM-DD"; input type=date le folosește direct.
export const isoToDateInput = (iso) => (iso ? String(iso).slice(0, 10) : "");

export const PageHeader = ({ title, subtitle, actions }) => (
  <div className="flex flex-wrap items-start justify-between gap-3">
    <div>
      <h2 className="text-xl font-bold text-slate-900 dark:text-white">{title}</h2>
      {subtitle && <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>}
    </div>
    {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
  </div>
);

export const Chips = ({ items }) =>
  items?.length ? (
    <div className="flex flex-wrap gap-1.5">
      {items.map((i) => (
        <span key={i} className="rounded-md bg-slate-100 dark:bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:text-slate-300">
          {i}
        </span>
      ))}
    </div>
  ) : null;

export const Field = ({ label, hint, htmlFor, children }) => (
  <div className="space-y-1.5 min-w-0">
    <Label htmlFor={htmlFor} className="text-sm font-semibold text-slate-700 dark:text-slate-200">
      {label}
    </Label>
    {children}
    {hint && <p className="text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
  </div>
);

export const SelectField = ({ id, value, onValueChange, options, placeholder, testid }) => (
  <Select value={value} onValueChange={onValueChange}>
    <SelectTrigger id={id} className="w-full" data-testid={testid}>
      <SelectValue placeholder={placeholder} />
    </SelectTrigger>
    <SelectContent>
      {options.map((o) => (
        <SelectItem key={o.id} value={o.id}>
          {o.label}
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
);

// Grup de checkbox-uri (multi-select) cu aspect de carduri.
export const CheckGroup = ({ name, options, value = [], onChange, testid, columns = "sm:grid-cols-2" }) => (
  <div className={`grid grid-cols-1 ${columns} gap-2`} data-testid={testid}>
    {options.map((o) => {
      const checked = value.includes(o.id);
      const id = `${name}-${o.id}`;
      return (
        <label
          key={o.id}
          htmlFor={id}
          className={`flex items-center gap-2.5 rounded-xl border px-3 py-2.5 text-sm cursor-pointer transition-colors ${
            checked
              ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10"
              : "border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5"
          }`}
        >
          <Checkbox
            id={id}
            checked={checked}
            onCheckedChange={(v) => onChange(v ? [...value, o.id] : value.filter((x) => x !== o.id))}
            data-testid={`${testid}-${o.id}`}
          />
          <span className="text-slate-700 dark:text-slate-200">{o.label}</span>
        </label>
      );
    })}
  </div>
);

export const PageSkeleton = () => (
  <div className="space-y-4">
    <DSSkeleton kpis={3} blocks={2} />
  </div>
);

// ── Recoltă, alocare, piață (S4) ────────────────────────────────────────────

export const BASIS_LABEL = { agreement_share: "Conform acordului", manual: "Manual" };
export const BASIS_CLS = {
  agreement_share: "bg-violet-50 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300",
  manual: "bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-200",
};

const RES_CANCELLED = { label: "Anulată", cls: "bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300" };
export const RESERVATION_STATUS = {
  requested: STATUS.requested,
  confirmed: STATUS.confirmed,
  picked_up: STATUS.picked_up,
  cancelled: RES_CANCELLED,
  no_show: STATUS.no_show,
  declined: STATUS.declined,
};

// Fallback-uri pentru meta (folosite până apare în GET /meta).
export const LISTING_CATEGORIES_FALLBACK = [
  { id: "legume", label: "Legume" },
  { id: "fructe", label: "Fructe" },
  { id: "cereale", label: "Cereale" },
  { id: "lactate", label: "Lactate" },
  { id: "ouă", label: "Ouă" },
  { id: "miere", label: "Miere" },
  { id: "conserve", label: "Conserve" },
  { id: "altele", label: "Altele" },
];
export const LISTING_UNITS_FALLBACK = [
  { id: "kg", label: "kg" },
  { id: "buc", label: "buc" },
  { id: "legătură", label: "legătură" },
  { id: "borcan", label: "borcan" },
  { id: "litru", label: "litru" },
];
export const RESERVATION_MODES_FALLBACK = [
  { id: "cash_on_pickup", label: "Plată la ridicare" },
  { id: "exchange", label: "Schimb" },
];
// Modurile anunțului nu vin din meta (sunt fixe în contract).
export const LISTING_MODES = [
  { id: "sale", label: "Vânzare" },
  { id: "exchange", label: "Schimb" },
  { id: "both", label: "Vânzare sau schimb" },
];
export const PICKUP_NOTICE = "Plata se face la ridicare, direct între voi. Rădăcini nu procesează plăți.";

// Modurile de rezervare permise de un anunț (sale → plată, exchange → schimb, both → ambele).
export const allowedReservationModes = (listingMode) =>
  listingMode === "exchange" ? ["exchange"] : listingMode === "sale" ? ["cash_on_pickup"] : ["cash_on_pickup", "exchange"];

export const fmtKg = (v) => `${Number(v || 0).toLocaleString("ro-RO", { maximumFractionDigits: 1 })} kg`;
export const fmtPrice = (v, unit) =>
  v == null || v === "" ? null : `${Number(v).toLocaleString("ro-RO", { maximumFractionDigits: 2 })} RON/${unit || "unitate"}`;

export const StatusPill = ({ def, testid }) => (
  <span data-testid={testid} className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-bold whitespace-nowrap ${def.cls}`}>
    {def.label}
  </span>
);

export const ReservationBadge = ({ status, testid }) => (
  <StatusPill def={RESERVATION_STATUS[status] || { label: status || "—", cls: "bg-slate-100 text-slate-600" }} testid={testid} />
);

export const BasisBadge = ({ basis, testid }) => (
  <span data-testid={testid} className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-bold whitespace-nowrap ${BASIS_CLS[basis] || BASIS_CLS.manual}`}>
    {BASIS_LABEL[basis] || basis || "—"}
  </span>
);

// Stele pentru rating (value = număr sau null).
export const Stars = ({ value, count, testid }) => {
  if (!count) return <span data-testid={testid} className="text-xs text-slate-500 dark:text-slate-400">Fără evaluări</span>;
  return (
    <span data-testid={testid} className="inline-flex items-center gap-1 text-xs font-semibold text-slate-700 dark:text-slate-200">
      <span className="text-amber-500">★</span>
      {Number(value || 0).toLocaleString("ro-RO", { maximumFractionDigits: 1 })}
      <span className="text-slate-500 dark:text-slate-400">({count})</span>
    </span>
  );
};
