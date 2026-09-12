// PropManage Business Design System — tokens semantice (unica sursă de adevăr)
// Culori SEMANTICE: verde=succes, cyan=info, portocaliu=atenție, roșu=critic, lime=AI/brand, gri=neutru
// Feb 2026 — Redesign unitar: lime brand peste tot, fără mov.

export const SEMANTIC = {
  success:  { text: "text-emerald-700 dark:text-emerald-300", bg: "bg-emerald-50 dark:bg-emerald-500/15", solid: "#10b981" },
  info:     { text: "text-cyan-700 dark:text-cyan-300",       bg: "bg-cyan-50 dark:bg-cyan-500/15",       solid: "#06b6d4" },
  warning:  { text: "text-amber-700 dark:text-amber-300",     bg: "bg-amber-50 dark:bg-amber-500/15",     solid: "#f59e0b" },
  critical: { text: "text-rose-700 dark:text-rose-300",       bg: "bg-rose-50 dark:bg-rose-500/15",       solid: "#f43f5e" },
  ai:       { text: "text-lime-700 dark:text-lime-300",       bg: "bg-lime-50 dark:bg-lime-500/15",       solid: "#84cc16" },
  neutral:  { text: "text-slate-500 dark:text-slate-400",     bg: "bg-slate-100 dark:bg-slate-700/50",    solid: "#64748b" },
};

// Ordinea standard a culorilor în grafice — lime brand primar, apoi semantice
export const CHART_COLORS = ["#84cc16", "#10b981", "#06b6d4", "#f59e0b", "#f43f5e", "#64748b"];
export const CHART = { strokeWidth: 2, gridDash: "3 3", gridOpacity: 0.2, tickFontSize: 10 };

// Spațiere standard: 24px secțiuni · 16px carduri · 12px în card · 8px label→valoare
export const SP = { section: "space-y-6", cards: "gap-4", inCard: "space-y-3", labelValue: "mt-2" };

// Grid unic: 12 col desktop/laptop · 6 tabletă · 1 mobil
export const GRID12 = "grid grid-cols-1 md:grid-cols-6 xl:grid-cols-12 gap-4";

// Card de bază — toate suprafețele Business folosesc exact acest stil
export const CARD = "rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111213]";

export const BADGE_STYLES = {
  NEW:     "bg-lime-50 text-lime-700 dark:bg-lime-500/15 dark:text-lime-300",
  AI:      "bg-lime-50 text-lime-700 dark:bg-lime-500/15 dark:text-lime-300",
  BETA:    "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  LIVE:    "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  ACTIVE:  "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  WARNING: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  ERROR:   "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
};

export const BUTTON_STYLES = {
  primary:   "bg-lime-400 hover:bg-lime-500 text-slate-900",
  secondary: "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700",
  ghost:     "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/50",
  danger:    "bg-rose-600 hover:bg-rose-700 text-white",
  success:   "bg-emerald-600 hover:bg-emerald-700 text-white",
};
