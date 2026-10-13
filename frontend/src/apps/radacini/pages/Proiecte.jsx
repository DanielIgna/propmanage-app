import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { AlertTriangle, Briefcase } from "lucide-react";
import { CARD, EmptyState } from "../../../design-system";
import { radaciniApi, asList, errMsg } from "../api";
import { counterOf, fmtArea, fmtPeriod, linkBtnCls, PageHeader, PageSkeleton, RoleBadge, StatusBadge } from "../shared";

function ProjectCard({ p }) {
  return (
    <Link
      to={`/radacini/proiecte/${p.id}`}
      className={`${CARD} block p-4 md:p-5 space-y-3 hover:border-emerald-300 dark:hover:border-emerald-500/40 transition-colors`}
      data-testid={`radacini-proiect-${p.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-bold text-slate-900 dark:text-white break-words">{p.title || "Proiect agricol"}</p>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {p.locality || "—"} · {fmtArea(p.area_m2)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <RoleBadge role={p.role} testid={`radacini-proiect-rol-${p.id}`} />
          <StatusBadge status={p.status} testid={`radacini-proiect-status-${p.id}`} />
        </div>
      </div>

      <p className="text-sm text-slate-600 dark:text-slate-300">
        Perioadă: {p.start_date ? fmtPeriod(p.start_date, p.end_date) : "—"}
      </p>

      <div className="grid grid-cols-3 gap-2 text-center" data-testid={`radacini-proiect-contoare-${p.id}`}>
        <div className="rounded-xl bg-slate-50 dark:bg-white/5 px-2 py-2">
          <p className="text-lg font-bold text-slate-900 dark:text-white">{counterOf(p, "crop_plans")}</p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">Culturi</p>
        </div>
        <div className="rounded-xl bg-slate-50 dark:bg-white/5 px-2 py-2">
          <p className="text-lg font-bold text-slate-900 dark:text-white">{counterOf(p, "upcoming_activities")}</p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">Activități viitoare</p>
        </div>
        <div className="rounded-xl bg-slate-50 dark:bg-white/5 px-2 py-2">
          <p className="text-lg font-bold text-slate-900 dark:text-white">{counterOf(p, "pending_contributions")}</p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">Contribuții în așteptare</p>
        </div>
      </div>
    </Link>
  );
}

export default function Proiecte() {
  // loaded=false până la răspuns: afișăm skeleton.
  const [data, setData] = useState({ loaded: false, items: [], error: null });

  useEffect(() => {
    let alive = true;
    radaciniApi
      .projects()
      .then((d) => alive && setData({ loaded: true, items: asList(d), error: null }))
      .catch((e) => {
        if (!alive) return;
        toast.error(errMsg(e, "Nu am putut încărca proiectele"));
        setData({ loaded: true, items: [], error: e });
      });
    return () => {
      alive = false;
    };
  }, []);

  if (!data.loaded) return <PageSkeleton />;

  return (
    <div className="space-y-5 max-w-4xl" data-testid="radacini-proiecte">
      <PageHeader title="Proiecte" subtitle="Proiectele agricole la care participi: plan de culturi, calendar și contribuții." />

      {data.error ? (
        <EmptyState icon={AlertTriangle} title="Nu am putut încărca proiectele" hint={errMsg(data.error)} testid="radacini-proiecte-error" />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="Nu ai niciun proiect"
          hint="Proiectul se creează automat când un acord este semnat de ambele părți."
          action={
            <Link to="/radacini/acorduri" className={linkBtnCls("secondary")} data-testid="radacini-proiecte-btn-acorduri">
              Vezi acordurile
            </Link>
          }
          testid="radacini-proiecte-empty"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="radacini-proiecte-list">
          {data.items.map((p) => (
            <ProjectCard key={p.id} p={p} />
          ))}
        </div>
      )}
    </div>
  );
}
