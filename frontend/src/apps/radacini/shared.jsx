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
};

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
