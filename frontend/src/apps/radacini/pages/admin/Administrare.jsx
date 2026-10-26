import React, { Suspense, lazy } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Activity, Flag, FlaskConical, Gavel, HeartPulse, LayoutDashboard, ScrollText, ShieldAlert, ShieldOff, Users, UsersRound } from "lucide-react";
import { useAuth } from "../../../../auth";
import { EmptyState, TabBar } from "../../../../design-system";
import { canSee } from "../../config";
import { useStaffMe } from "../../hooks";
import { linkBtnCls, PageHeader, PageSkeleton } from "../../shared";

const Prezentare = lazy(() => import("./Prezentare"));
const Activitate = lazy(() => import("./Activitate"));
const Membri = lazy(() => import("./Membri"));
const Moderare = lazy(() => import("./Moderare"));
const CereriGdpr = lazy(() => import("./CereriGdpr"));
const Jurnal = lazy(() => import("./Jurnal"));
const Sistem = lazy(() => import("./Sistem"));
const StaffReportsQueue = lazy(() => import("../Raportari").then((m) => ({ default: m.StaffReportsQueue })));

const TABS = [
  ["prezentare", "Prezentare", LayoutDashboard],
  ["activitate", "Activitate", Activity],
  ["membri", "Membri", UsersRound],
  ["moderare", "Moderare", Gavel],
  ["raportari", "Raportări", Flag],
  ["gdpr", "Cereri GDPR", ShieldAlert],
  ["jurnal", "Jurnal", ScrollText],
  ["sistem", "Stare sistem", HeartPulse],
];
const TAB_IDS = TABS.map(([id]) => id);
const DEFAULT_TAB = "prezentare";

export default function Administrare() {
  const { user } = useAuth();
  const { staff, loading: staffLoading } = useStaffMe();
  const [searchParams, setSearchParams] = useSearchParams();
  const param = searchParams.get("tab");
  const tab = TAB_IDS.includes(param) ? param : DEFAULT_TAB;
  const setTab = (t) => setSearchParams(t === DEFAULT_TAB ? {} : { tab: t }, { replace: true });

  if (staffLoading) return <PageSkeleton />;
  if (staff?.role !== "manager") {
    return (
      <EmptyState
        icon={ShieldOff}
        title="Doar managerii pot administra Rădăcini"
        hint="Cere unui manager să îți acorde rolul."
        testid="radacini-admin-noaccess"
      />
    );
  }

  const showTestAccounts = canSee({ requires: "superadmin" }, staff, user);

  return (
    <div className="space-y-5" data-testid="radacini-admin">
      <PageHeader
        title="Administrare Rădăcini"
        subtitle="Indicatori, activitate, membri, moderare, raportări, cereri GDPR și starea sistemului."
        actions={
          <>
            <Link to="/radacini/personal" className={linkBtnCls("secondary")} data-testid="radacini-admin-link-personal">
              <Users className="w-3.5 h-3.5" /> Personal
            </Link>
            {showTestAccounts && (
              <Link to="/radacini/conturi-test" className={linkBtnCls("secondary")} data-testid="radacini-admin-link-conturi-test">
                <FlaskConical className="w-3.5 h-3.5" /> Conturi de test
              </Link>
            )}
          </>
        }
      />

      <TabBar tabs={TABS} active={tab} onChange={setTab} testidPrefix="radacini-admin-tab" />

      <Suspense fallback={<PageSkeleton />}>
        {tab === "prezentare" && <Prezentare onTab={setTab} />}
        {tab === "activitate" && <Activitate />}
        {tab === "membri" && <Membri />}
        {tab === "moderare" && <Moderare />}
        {tab === "gdpr" && <CereriGdpr />}
        {tab === "jurnal" && <Jurnal />}
        {tab === "raportari" && <StaffReportsQueue />}
        {tab === "sistem" && <Sistem />}
      </Suspense>
    </div>
  );
}
