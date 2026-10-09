// House Health — Score section.
import React from "react";
import { fmtDate } from "./constants";

export const ScoreSection = ({ data }) => {
  if (!data) return <div className="text-stone-400 text-sm">Se încarcă...</div>;
  const score = data.score_overall;
  const cls = data.classification;
  return (
    <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-6">
      <h2 className="text-lg font-bold mb-4">Scor general proprietate</h2>
      <div className="flex items-end gap-4 mb-6">
        <div className="text-6xl font-extrabold text-emerald-300 tabular-nums">{score ?? "—"}</div>
        <div className="text-stone-500 mb-2">/100</div>
        <div className={`mb-2 ml-3 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
          cls === "Excellent" ? "bg-emerald-500/15 text-emerald-300" :
          cls === "Good" ? "bg-sky-500/15 text-sky-300" :
          cls === "Fair" ? "bg-amber-500/15 text-amber-300" :
          "bg-rose-500/15 text-rose-300"
        }`}>{cls || "Pending"}</div>
      </div>
      <div className="text-xs text-stone-400 space-y-1">
        <div>📊 Calculat din: Calitatea aerului · Performanță termică · Umiditate · Electric · Documentație · Mentenanță · Radon</div>
        <div>📅 Ultima evaluare: <strong className="text-stone-200">{fmtDate(data.last_evaluation_date)}</strong></div>
        <div>🔔 Următoarea recomandată: <strong className="text-stone-200">{fmtDate(data.next_evaluation_date)}</strong></div>
        <div className="mt-3 p-3 bg-stone-800/40 rounded-lg text-[11px]">
          ⚙ Clasificare: <strong>90-100 Excellent · 75-89 Good · 50-74 Fair · 0-49 Needs Attention</strong>.
          Formula scor e configurabilă din Admin panel.
        </div>
      </div>
    </div>
  );
};
