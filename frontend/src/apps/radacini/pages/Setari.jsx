import React from "react";
import { useAuth } from "../../../auth";
import { CARD } from "../../../design-system";

export default function Setari() {
  const { user } = useAuth();
  return (
    <div className="space-y-6 max-w-2xl">
      <div className={`${CARD} p-5 space-y-2`}>
        <h2 className="text-base font-bold text-slate-900 dark:text-white">Cont</h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">Nume: {user?.full_name || user?.name || "—"}</p>
        <p className="text-sm text-slate-600 dark:text-slate-300">Email: {user?.email || "—"}</p>
      </div>
      <p className="text-sm text-slate-500 dark:text-slate-400">Setările vor veni aici.</p>
    </div>
  );
}
