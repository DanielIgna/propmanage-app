import React from "react";
import { Link, Navigate } from "react-router-dom";
import { CheckCircle2, CircleDashed, Clock } from "lucide-react";
import { CARD } from "../../../design-system";
import { PageHeader, linkBtnCls } from "../shared";

// Pagină de dezvoltare: nu se randează în producție.
const SPRINTS = [
  {
    id: "S1",
    title: "Fundație, membri, terenuri, personal și coadă de verificare",
    status: "done",
    links: [
      { to: "/radacini/profil", label: "Profil" },
      { to: "/radacini/terenurile-mele/nou", label: "Adaugă teren" },
      { to: "/radacini/terenuri", label: "Terenuri" },
      { to: "/radacini/operator", label: "Operator" },
    ],
  },
  {
    id: "S2",
    title: "Cereri de teren, negociere și acorduri cu versiune",
    status: "done",
    links: [
      { to: "/radacini/cereri", label: "Cereri" },
      { to: "/radacini/acorduri", label: "Acorduri" },
    ],
  },
  {
    id: "S3",
    title: "Proiect agricol: membri, plan culturi, activități, contribuții",
    status: "done",
    links: [{ to: "/radacini/proiecte", label: "Proiecte" }],
  },
  {
    id: "S4",
    title: "Recoltă, alocare și piață locală (listări, rezervări, schimb)",
    status: "progress",
    links: [],
  },
  {
    id: "S5",
    title: "Admin: comutator Produs, secțiune Rădăcini, KPI, noduri Knowledge Center",
    status: "todo",
    links: [],
  },
];

const STATUS_UI = {
  done: { label: "Gata", Icon: CheckCircle2, cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  progress: { label: "În lucru", Icon: Clock, cls: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  todo: { label: "Urmează", Icon: CircleDashed, cls: "bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300" },
};

// Conturi demo: doar emailurile. Parolele sunt în backend/seed.py.
const DEMO_ACCOUNTS = [
  { email: "client@propmanage.io", role: "Proprietar" },
  { email: "specialist@propmanage.io", role: "Cultivator + operator Florești" },
  { email: "admin@propmanage.io", role: "Manager" },
];

export default function Progres() {
  if (process.env.NODE_ENV === "production") return <Navigate to="/radacini" replace />;

  return (
    <div className="space-y-6 max-w-4xl" data-testid="radacini-progres">
      <PageHeader title="Progres (dev)" subtitle="Stadiul sprinturilor Rădăcini și ce poți încerca în fiecare." />

      <section className="space-y-3" data-testid="radacini-progres-sprinturi">
        {SPRINTS.map((s) => {
          const ui = STATUS_UI[s.status];
          const Icon = ui.Icon;
          return (
            <div key={s.id} className={`${CARD} p-4 md:p-5 space-y-3`} data-testid={`radacini-sprint-${s.id}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-bold text-slate-900 dark:text-white">
                    {s.id} · <span className="font-semibold">{s.title}</span>
                  </p>
                </div>
                <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-bold whitespace-nowrap ${ui.cls}`}>
                  <Icon className="w-3.5 h-3.5" /> {ui.label}
                </span>
              </div>
              {s.links.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {s.links.map((l) => (
                    <Link key={l.to} to={l.to} className={linkBtnCls("secondary")} data-testid={`radacini-progres-link-${s.id}-${l.label}`}>
                      {l.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </section>

      <section className={`${CARD} p-4 md:p-5 space-y-3`} data-testid="radacini-progres-conturi">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white">Conturi demo</h3>
        <ul className="space-y-2 text-sm">
          {DEMO_ACCOUNTS.map((a) => (
            <li key={a.email} className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-slate-800 dark:text-slate-100 break-all">{a.email}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400">{a.role}</span>
            </li>
          ))}
        </ul>
        <p className="text-xs text-slate-500 dark:text-slate-400">Parolele sunt în backend/seed.py.</p>
      </section>
    </div>
  );
}
