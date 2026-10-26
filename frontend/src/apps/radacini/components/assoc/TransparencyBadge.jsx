import React, { useEffect, useState } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "../../../../components/ui/popover";
import { s9Api } from "../../api_s9";

const COMP_LABEL = {
  obligations: ["Obligații statutare", "Câte din termenele statutului au fost respectate."],
  documents: ["Documente obligatorii", "Bilanț, buget, procese-verbale și rapoarte de cenzori publicate."],
  requests: ["Cereri în termen", "Cererile de informații rezolvate în termenul din statut."],
  participation: ["Participare", "Cât din cote aparține membrilor activi, confirmați."],
};

export const scoreTone = (s) =>
  s >= 75
    ? "bg-emerald-100 text-emerald-800 border-emerald-300"
    : s >= 50
    ? "bg-amber-100 text-amber-800 border-amber-300"
    : "bg-red-100 text-red-800 border-red-300";

const compEntries = (components) => {
  if (!components) return [];
  const arr = Array.isArray(components)
    ? components
    : Object.entries(components).map(([k, v]) => (typeof v === "object" && v ? { key: k, ...v } : { key: k, score: v }));
  return arr.map((c) => {
    const key = c.key || c.id || c.name;
    const [label, expl] = COMP_LABEL[key] || [c.label || key, c.explanation || ""];
    return { key, label: c.label || label, expl: c.explanation || c.detail || expl, score: c.score ?? (c.value != null ? c.value * 100 : null) };
  });
};

export default function TransparencyBadge({ assocId, score: scoreProp, components: compProp }) {
  const [data, setData] = useState(scoreProp != null ? { score: scoreProp, components: compProp } : null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    if (scoreProp != null) {
      setData({ score: scoreProp, components: compProp });
      return;
    }
    if (!assocId) return;
    let live = true;
    s9Api
      .transparency(assocId)
      .then((d) => live && setData(d))
      .catch(() => live && setErr(true));
    return () => {
      live = false;
    };
  }, [assocId, scoreProp, compProp]);

  if (err) return <span className="text-xs text-slate-500" data-testid="transparency-badge-error">Scor indisponibil</span>;
  if (!data) return <span className="inline-block h-6 w-24 animate-pulse rounded-full bg-slate-200" data-testid="transparency-badge-loading" />;

  const score = Math.round(Number(data.score ?? 0));
  const comps = compEntries(data.components);
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold ${scoreTone(score)}`}
          data-testid="transparency-badge"
          aria-label={`Scor de transparență ${score} din 100`}
        >
          Transparență {score}/100
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80 max-w-[90vw] text-sm" data-testid="transparency-popover">
        <p className="mb-2 font-semibold">Cum se calculează scorul</p>
        {comps.length === 0 ? (
          <p className="text-slate-600">Detaliile nu sunt disponibile.</p>
        ) : (
          <ul className="space-y-2">
            {comps.map((c) => (
              <li key={c.key} data-testid={`transparency-comp-${c.key}`}>
                <div className="flex justify-between gap-2 font-medium">
                  <span>{c.label}</span>
                  {c.score != null && <span>{Math.round(c.score)}%</span>}
                </div>
                {c.expl && <p className="text-xs text-slate-600">{c.expl}</p>}
              </li>
            ))}
          </ul>
        )}
      </PopoverContent>
    </Popover>
  );
}
