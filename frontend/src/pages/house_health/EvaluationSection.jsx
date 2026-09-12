// House Health — Evaluation section (reused for air/thermal/humidity/electric/radon).
import React, { useEffect, useState } from "react";
import axios from "axios";
import { API } from "../DashShared";
import { EVAL_META, STATUS_COLORS, fmtDate } from "./constants";

export const EvaluationSection = ({ twinId, kind }) => {
  const meta = EVAL_META[kind];
  const [items, setItems] = useState([]);
  const [equipment, setEquipment] = useState([]);

  useEffect(() => {
    if (!twinId) return;
    axios.get(`${API}/house-health/evaluations`, { params: { twin_project_id: twinId } })
      .then((r) => setItems((r.data?.items || []).filter((e) => e.kind === kind)))
      .catch(() => {});
    axios.get(`${API}/house-health/equipment-catalog`)
      .then((r) => setEquipment(r.data?.equipment?.[kind] || []))
      .catch(() => {});
  }, [twinId, kind]);

  const Icon = meta.icon;

  return (
    <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-5" data-testid={`hh-eval-${kind}`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-5 h-5 text-emerald-400" />
        <h2 className="text-lg font-bold">{meta.title}</h2>
      </div>

      <div className="p-3 bg-stone-800/40 rounded-lg text-xs mb-4">
        <div className="text-stone-400">📦 Echipamente acceptate:</div>
        <div className="text-stone-200 font-medium mt-1">{equipment.length > 0 ? equipment.join(" · ") : "—"}</div>
        <div className="text-stone-500 mt-2 text-[11px]">
          Specialistul folosește aparatura proprie și încarcă rapoartele aici (PDF, imagini, măsurători).
          Toate evaluările trec prin aprobare admin.
        </div>
      </div>

      <div className="text-xs uppercase tracking-wider text-stone-500 font-bold mb-2">Evaluări existente</div>
      {items.length === 0 ? (
        <div className="text-xs text-stone-500 italic" data-testid={`hh-eval-empty-${kind}`}>
          Nicio evaluare {meta.title.toLowerCase()} încă. Cere specialistului să creeze una.
        </div>
      ) : (
        <ul className="space-y-1.5">
          {items.map((e, i) => (
            <li key={e.id} className="flex items-center gap-3 text-sm px-3 py-2 rounded-lg bg-stone-800/40 border border-stone-700/40" data-testid={`hh-eval-item-${i}`}>
              <div className="flex-1">
                <div className="text-stone-100 font-medium">{fmtDate(e.date)} · {e.specialist_email || "specialist"}</div>
                <div className="text-[10px] text-stone-500 truncate">{e.observations || "fără observații"}</div>
              </div>
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase ${STATUS_COLORS[e.status] || ""}`}>
                {e.status?.replace(/_/g, " ")}
              </span>
              <span className="text-[10px] text-stone-500">{(e.attachments || []).length} fișiere</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
