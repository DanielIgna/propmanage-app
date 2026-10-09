// House Health — History timeline section.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { API } from "../DashShared";
import { fmtDate } from "./constants";

export const HistorySection = ({ twinId }) => {
  const [events, setEvents] = useState([]);
  useEffect(() => {
    if (!twinId) return;
    axios.get(`${API}/house-health/history/${twinId}`).then((r) => setEvents(r.data?.items || [])).catch(() => {});
  }, [twinId]);

  if (events.length === 0) return (
    <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-5" data-testid="hh-history-empty">
      <h2 className="text-lg font-bold mb-2">Istoric verificări</h2>
      <p className="text-sm text-stone-400">Niciun eveniment înregistrat încă. Evaluările aprobate vor apărea aici cronologic.</p>
    </div>
  );

  return (
    <div className="bg-stone-900/40 border border-stone-800 rounded-2xl p-5" data-testid="hh-history-section">
      <h2 className="text-lg font-bold mb-4">Istoric verificări</h2>
      <ol className="relative border-l-2 border-stone-700 ml-3 space-y-4">
        {events.map((e, i) => (
          <li key={i} className="ml-5 relative" data-testid={`hh-history-${i}`}>
            <span className="absolute -left-[34px] top-1 w-4 h-4 rounded-full bg-emerald-500 ring-4 ring-stone-950"></span>
            <div className="text-[11px] text-stone-500">{fmtDate(e.date)}</div>
            <div className="text-sm font-semibold text-stone-100">{e.title}</div>
            <div className="text-xs text-stone-400">{e.kind === "evaluation" ? `Tip: ${e.evaluation_kind}` : "Raport"}</div>
          </li>
        ))}
      </ol>
    </div>
  );
};
