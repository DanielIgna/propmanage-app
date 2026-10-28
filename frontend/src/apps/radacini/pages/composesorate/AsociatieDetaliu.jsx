import React, { Suspense, lazy, useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Landmark } from "lucide-react";
import { EmptyState, TabBar } from "../../../../design-system";
import { errMsg } from "../../api";
import { ASSOC_TYPE, assocGet, assocMe, canSeeRegistry } from "../../api_s9";
import { PageSkeleton } from "../../shared";
import TransparencyBadge from "../../components/assoc/TransparencyBadge";
import OverviewTab from "../../components/assoc/OverviewTab";
import MyShareTab from "../../components/assoc/MyShareTab";
import RegistryTab from "../../components/assoc/RegistryTab";

const DocumentsTab = lazy(() => import("../../components/assoc/DocumentsTab"));
const MeetingsTab = lazy(() => import("../../components/assoc/MeetingsTab"));
const PetitionsTab = lazy(() => import("../../components/assoc/PetitionsTab"));
const RequestsTab = lazy(() => import("../../components/assoc/RequestsTab"));
const CalendarTab = lazy(() => import("../../components/assoc/CalendarTab"));
const FinanceTab = lazy(() => import("../../components/assoc/FinanceTab"));
const AuditTab = lazy(() => import("../../components/assoc/AuditTab"));

const TABS = [
  ["prezentare", "Prezentare"], ["cota", "Cota mea"], ["registru", "Registru"], ["documente", "Documente"],
  ["sedinte", "Ședințe"], ["petitii", "Petiții"], ["cereri", "Cereri"], ["calendar", "Calendar"],
  ["finante", "Finanțe"], ["jurnal", "Jurnal"],
];
const PANELS = {
  prezentare: OverviewTab, cota: MyShareTab, registru: RegistryTab, documente: DocumentsTab, sedinte: MeetingsTab,
  petitii: PetitionsTab, cereri: RequestsTab, calendar: CalendarTab, finante: FinanceTab, jurnal: AuditTab,
};

export default function AsociatieDetaliu() {
  const { id } = useParams();
  const [sp, setSp] = useSearchParams();
  const [state, setState] = useState({ loading: true, assoc: null, access: null, error: null });

  const reload = useCallback(() => {
    Promise.all([assocGet(id), assocMe(id).catch(() => null)])
      .then(([a, me]) => setState({ loading: false, assoc: a?.association ?? a, access: me, error: null }))
      .catch((error) => setState({ loading: false, assoc: null, access: null, error }));
  }, [id]);
  useEffect(() => {
    setState((s) => ({ ...s, loading: true }));
    reload();
  }, [reload]);

  const { loading, assoc, access, error } = state;
  const back = (
    <Link to="/radacini/composesorate" className="inline-flex items-center gap-1 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:underline">
      <ArrowLeft className="w-4 h-4" /> Composesorate
    </Link>
  );
  if (loading) return <PageSkeleton />;
  if (error || !assoc) return <div className="space-y-4">{back}<EmptyState icon={Landmark} title="Asociația nu există sau nu ai acces" hint={error ? errMsg(error) : undefined} /></div>;

  const tabs = TABS.filter(([t]) => t !== "registru" || canSeeRegistry(access));
  const tp = sp.get("tab");
  const active = tabs.some(([t]) => t === tp) ? tp : "prezentare";
  const setTab = (t) => setSp(t === "prezentare" ? {} : { tab: t }, { replace: true });
  const Panel = PANELS[active];

  return (
    <div className="space-y-5 max-w-5xl" data-testid="asociatie-detaliu">
      {back}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white break-words" data-testid="assoc-name">{assoc.name}</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">{ASSOC_TYPE[assoc.type] || assoc.type} · {(assoc.localities || []).join(", ")}</p>
        </div>
        {assoc.score_visible === false ? (
          <span className="text-xs text-slate-500 dark:text-slate-400" data-testid="transparency-members-only">Scor vizibil doar membrilor</span>
        ) : (
          <TransparencyBadge assocId={assoc.id} score={assoc.transparency_score ?? undefined} />
        )}
      </div>
      <TabBar tabs={tabs} active={active} onChange={setTab} testidPrefix="assoc-tab" />
      <div data-testid={`assoc-panel-${active}`}>
        <Suspense fallback={<PageSkeleton />}>
          <Panel assoc={assoc} access={access} reload={reload} />
        </Suspense>
      </div>
    </div>
  );
}
