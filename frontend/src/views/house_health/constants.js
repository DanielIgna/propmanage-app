// Shared constants & helpers for House Health sections.
import {
  Wind, Thermometer, Droplets, Zap as Bolt, Radio, Gauge, FileText, Clock, Lightbulb,
} from "lucide-react";

export const SECTIONS = [
  { key: "score",       label: "Scor proprietate",    icon: Gauge },
  { key: "air",         label: "Calitatea aerului",   icon: Wind },
  { key: "thermal",     label: "Analiză termică",     icon: Thermometer },
  { key: "humidity",    label: "Umiditate & infiltrații", icon: Droplets },
  { key: "electric",    label: "Siguranță electrică", icon: Bolt },
  { key: "radon",       label: "Radon",               icon: Radio },
  { key: "docs",        label: "Documentație tehnică", icon: FileText },
  { key: "history",     label: "Istoric verificări",  icon: Clock },
  { key: "recommendations", label: "Recomandări",     icon: Lightbulb },
];

export const EVALUATION_KINDS = ["air", "thermal", "humidity", "electric", "radon"];

export const DOC_CATEGORIES = [
  { key: "certificat_energetic", label: "Certificat energetic" },
  { key: "carte_tehnica", label: "Carte tehnică" },
  { key: "cadastru", label: "Cadastru" },
  { key: "extras_cf", label: "Extras CF" },
  { key: "facturi_renovari", label: "Facturi renovări" },
  { key: "garantii", label: "Garanții" },
  { key: "manuale", label: "Manuale" },
  { key: "procese_verbale", label: "Procese verbale" },
  { key: "hh_report", label: "Raport House Health" },
  { key: "other", label: "Altele" },
];

export const EXT_TYPES = [
  { key: "google_drive", label: "Google Drive" },
  { key: "dropbox", label: "Dropbox" },
  { key: "onedrive", label: "OneDrive" },
  { key: "custom", label: "Link personalizat" },
];

export const EVAL_META = {
  air:      { title: "Calitatea aerului", icon: Wind, fields: ["temperatura", "umiditate", "viteza_aerului", "CO2"] },
  thermal:  { title: "Analiză termică", icon: Thermometer, fields: ["zone_investigate"] },
  humidity: { title: "Umiditate & infiltrații", icon: Droplets, fields: ["zone_afectate", "severitate"] },
  electric: { title: "Siguranță electrică", icon: Bolt, fields: ["tensiuni", "continuitate", "probleme"] },
  radon:    { title: "Radon", icon: Radio, fields: ["valoare_medie", "perioada", "status"] },
};

export const STATUS_COLORS = {
  draft: "bg-stone-500/20 text-stone-300",
  pending_approval: "bg-amber-500/20 text-amber-300",
  approved: "bg-emerald-500/20 text-emerald-300",
  rejected: "bg-rose-500/20 text-rose-300",
};

export const PRIORITY_META = {
  urgent:      { label: "Urgent",        cls: "bg-rose-500/15 text-rose-300 border-rose-500/40",   icon: "🚨" },
  recommended: { label: "Recomandat",    cls: "bg-amber-500/15 text-amber-300 border-amber-500/40", icon: "⚠" },
  monitor:     { label: "Monitorizare",  cls: "bg-sky-500/15 text-sky-300 border-sky-500/40",      icon: "👁" },
};

export const CATEGORY_LABELS = {
  air: "Aer", thermal: "Termic", humidity: "Umiditate", electric: "Electric",
  radon: "Radon", structural: "Structural", docs: "Documentație", other: "Altele",
};

export const fmtDate = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleDateString("ro-RO", { day: "2-digit", month: "short", year: "numeric" }); }
  catch { return "—"; }
};
