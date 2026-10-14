import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Landmark } from "lucide-react";
import { CARD } from "../../../../design-system";
import { alertsMine } from "../../api_s9";

// Cardul „Composesoratele mele” pentru Panou: alerte (convocări neconfirmate, prescrieri, petiții).
export default function AssocAlertsCard() {
  const [items, setItems] = useState(null);
  useEffect(() => {
    let live = true;
    alertsMine()
      .then((d) => live && setItems(Array.isArray(d) ? d : d?.items || []))
      .catch(() => live && setItems([]));
    return () => {
      live = false;
    };
  }, []);
  if (!items) return null;
  return (
    <div className={`${CARD} p-4 space-y-3`} data-testid="assoc-alerts-card">
      <div className="flex items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
          <Landmark className="w-4 h-4" /> Composesoratele mele
        </h3>
        <Link to="/radacini/composesorate" className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 underline">
          Deschide
        </Link>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Nicio alertă. Totul este la zi.</p>
      ) : (
        <ul className="space-y-2">
          {items.slice(0, 5).map((a, i) => (
            <li key={a.id || i} className="text-sm">
              <Link
                to={`/radacini/composesorate/${a.association_id}${a.tab ? `?tab=${a.tab}` : ""}`}
                className="flex items-start gap-2 text-slate-700 dark:text-slate-200 hover:underline"
              >
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-600" />
                <span>{a.message || a.title || a.kind}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
