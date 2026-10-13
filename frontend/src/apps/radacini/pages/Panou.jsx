import React, { useEffect, useState } from "react";
import { Layers } from "lucide-react";
import { api, apiErr } from "../../../lib/api";
import { CARD, EmptyState } from "../../../design-system";

export default function Panou() {
  const [status, setStatus] = useState("checking"); // checking | ok | down
  const [me, setMe] = useState(null);

  useEffect(() => {
    Promise.allSettled([api.get("/radacini/me"), api.get("/radacini/health")]).then(([meRes, healthRes]) => {
      if (meRes.status === "fulfilled") setMe(meRes.value.data);
      setStatus(healthRes.status === "fulfilled" ? "ok" : "down");
    });
  }, []);

  const badge =
    status === "ok"
      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300"
      : status === "down"
      ? "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300"
      : "bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-300";
  const label = status === "ok" ? "API conectat" : status === "down" ? "API indisponibil" : "Se verifică…";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Bun venit în Rădăcini</h2>
          {me?.email && <p className="text-sm text-slate-500 dark:text-slate-400">Conectat ca {me.email}</p>}
        </div>
        <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${badge}`} data-testid="radacini-api-status">
          {label}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {["Modul 1", "Modul 2", "Modul 3"].map((name) => (
          <div key={name} className={`${CARD} p-4`}>
            <p className="text-sm font-bold text-slate-800 dark:text-slate-100">{name}</p>
            <EmptyState icon={Layers} title="Gol deocamdată" hint="Funcționalitate de stabilit" testid={`radacini-${name.replace(" ", "-").toLowerCase()}`} />
          </div>
        ))}
      </div>
    </div>
  );
}
