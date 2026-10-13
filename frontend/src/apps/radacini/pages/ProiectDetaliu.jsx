import React, { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Briefcase, CalendarDays, Users, Wallet, Sprout, Wheat } from "lucide-react";
import { useAuth } from "../../../auth";
import { EmptyState, TabBar } from "../../../design-system";
import { radaciniApi, errMsg } from "../api";
import { PROJECT_TABS, PageSkeleton, RoleBadge, StatusBadge, fmtPeriod, fmtArea } from "../shared";
import OverviewTab from "../components/project/Overview";
import CropsTab from "../components/project/CropsTab";
import CalendarTab from "../components/project/CalendarTab";
import ContributionsTab from "../components/project/ContributionsTab";
import MembersTab from "../components/project/MembersTab";
import HarvestTab from "../components/project/HarvestTab";

const TAB_ICONS = {
  prezentare: Briefcase,
  plan: Sprout,
  calendar: CalendarDays,
  contributii: Wallet,
  recolta: Wheat,
  membri: Users,
};

export default function ProiectDetaliu() {
  const { id } = useParams();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState({ loading: true, error: null, project: null });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    radaciniApi
      .project(id)
      .then((project) => alive && setData({ loading: false, error: null, project }))
      .catch((error) => alive && setData((s) => ({ ...s, loading: false, error })));
    return () => {
      alive = false;
    };
  }, [id, tick]);

  const reload = () => setTick((t) => t + 1);
  const { loading, error, project } = data;

  const back = (
    <Link to="/radacini/proiecte" className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline">
      <ArrowLeft className="w-4 h-4" /> Înapoi la proiecte
    </Link>
  );

  if (loading) return <PageSkeleton />;
  if (error || !project) {
    return (
      <div className="space-y-4">
        {back}
        <EmptyState
          icon={Briefcase}
          title="Proiectul nu există sau nu ai acces"
          hint={error ? errMsg(error) : undefined}
          testid="radacini-proiect-negasit"
        />
      </div>
    );
  }

  // access: "member" | "staff" (personalul vede doar, fără acțiuni). Proiectul finalizat e doar de citit.
  const members = project.members || [];
  const myMember = user ? members.find((m) => m.user_id === user.id) : null;
  const memberOf = project.access ? project.access === "member" : !!myMember;
  const myRole = project.role ?? myMember?.role ?? null;
  const readOnly = project.status === "completed";
  const canWrite = memberOf && !readOnly;
  const canCoord = canWrite && myRole === "coordinator";

  const tabParam = searchParams.get("tab");
  const active = PROJECT_TABS.some(([t]) => t === tabParam) ? tabParam : "prezentare";
  const setTab = (t) => setSearchParams(t === "prezentare" ? {} : { tab: t }, { replace: true });
  const tabs = PROJECT_TABS.map(([tid, label]) => [tid, label, TAB_ICONS[tid]]);

  // isMember în tab-uri înseamnă „poate scrie” (membru și proiect nefinalizat).
  const common = { project, members, isMember: canWrite, myRole, canCoord, me: user?.id, reload };

  return (
    <div className="space-y-5 max-w-5xl" data-testid="radacini-proiect-detaliu">
      {back}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white break-words" data-testid="radacini-proiect-titlu">
            {project.title || "Proiect agricol"}
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {project.locality || "—"} · {fmtArea(project.area_m2)}
            {project.start_date ? ` · ${fmtPeriod(project.start_date, project.end_date)}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {memberOf && myRole && <RoleBadge role={myRole} testid="radacini-proiect-rolul-meu" />}
          {readOnly ? (
            <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-bold whitespace-nowrap bg-slate-200 text-slate-700 dark:bg-white/15 dark:text-slate-200" data-testid="radacini-proiect-finalizat">
              Proiect finalizat
            </span>
          ) : (
            <StatusBadge status={project.status} testid="radacini-proiect-status" />
          )}
        </div>
      </div>

      {(!memberOf || readOnly) && (
        <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111213] p-4 text-sm text-slate-600 dark:text-slate-300" data-testid="radacini-proiect-readonly">
          {readOnly ? "Proiect finalizat. Este doar pentru consultare." : "Vizualizare fără calitate de membru. Nu poți modifica proiectul."}
        </div>
      )}

      <TabBar tabs={tabs} active={active} onChange={setTab} testidPrefix="radacini-proiect-tab" />

      <div data-testid={`radacini-proiect-panel-${active}`}>
        {active === "prezentare" && <OverviewTab {...common} />}
        {active === "plan" && <CropsTab {...common} />}
        {active === "calendar" && <CalendarTab {...common} />}
        {active === "contributii" && <ContributionsTab {...common} />}
        {active === "recolta" && <HarvestTab {...common} />}
        {active === "membri" && <MembersTab {...common} />}
      </div>
    </div>
  );
}
