import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Gavel } from "lucide-react";
import { CARD, EmptyState, TabBar } from "../../../design-system";
import { asList, errMsg } from "../api";
import { DISPUTE_SCOPE, DISPUTE_STATUS, s6aApi } from "../api_s6a";
import { useStaffMe } from "../hooks";
import { PageHeader, PageSkeleton, StatusPill, fmtDateTime } from "../shared";

export const DisputeBadge = ({ status, testid }) => (
  <StatusPill def={DISPUTE_STATUS[status] || { label: status || "—", cls: "bg-slate-100 text-slate-600" }} testid={testid} />
);

function List({ fetcher, emptyTitle }) {
  const [state, setState] = useState({ loading: true, items: [], error: null });
  useEffect(() => {
    let alive = true;
    fetcher()
      .then((d) => alive && setState({ loading: false, items: asList(d), error: null }))
      .catch((error) => alive && setState({ loading: false, items: [], error }));
    return () => {
      alive = false;
    };
  }, [fetcher]);
  if (state.loading) return <PageSkeleton />;
  if (state.error) return <EmptyState icon={Gavel} title="Nu am putut încărca disputele" hint={errMsg(state.error)} />;
  if (!state.items.length) return <EmptyState icon={Gavel} title={emptyTitle} testid="radacini-dispute-gol" />;
  return (
    <ul className="space-y-3" data-testid="radacini-dispute-lista">
      {state.items.map((d) => (
        <li key={d.id}>
          <Link to={`/radacini/dispute/${d.id}`} className={`${CARD} p-4 block space-y-1.5 hover:bg-slate-50 dark:hover:bg-white/5`} data-testid={`radacini-disputa-${d.id}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-bold text-slate-900 dark:text-white">{DISPUTE_SCOPE[d.scope_type] || d.scope_type}</p>
              <DisputeBadge status={d.status} />
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-300 line-clamp-2 break-words">{d.reason}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {d.locality ? `${d.locality} · ` : ""}
              {fmtDateTime(d.created_at)}
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}

const mine = () => s6aApi.myDisputes();
const queue = () => s6aApi.staffDisputes();

export default function Dispute() {
  const { staff } = useStaffMe();
  const [sp, setSp] = useSearchParams();
  const tab = staff?.is_staff && sp.get("tab") === "coada" ? "coada" : "mele";
  return (
    <div className="space-y-5" data-testid="radacini-dispute">
      <PageHeader title="Dispute" subtitle="Contestații și medieri între părți." />
      {staff?.is_staff && (
        <TabBar tabs={[["mele", "Ale mele"], ["coada", "Coada de mediere"]]} active={tab} onChange={(t) => setSp(t === "mele" ? {} : { tab: t }, { replace: true })} testidPrefix="radacini-dispute-tab" />
      )}
      {tab === "coada" ? <List fetcher={queue} emptyTitle="Nicio dispută în coada ta" /> : <List fetcher={mine} emptyTitle="Nu ai nicio dispută" />}
    </div>
  );
}
