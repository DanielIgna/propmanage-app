import React, { useState } from "react";
import { Activity, RefreshCw } from "lucide-react";
import { CARD, DSButton, EmptyState } from "../../../../design-system";
import { radaciniApi } from "../../api";
import { fmtDateTime, SelectField } from "../../shared";
import { ErrorBox, EVENT_GROUPS, eventInGroup, eventLabel, firstName, TabSkeleton, usePaged } from "./adminShared";

const PAGE = 50;

export default function Activitate() {
  const [group, setGroup] = useState("all");
  const { rows, loading, loadingMore, error, moreError, hasMore, loadMore, reload } = usePaged(
    (before) => radaciniApi.adminActivity({ limit: PAGE, before }),
    [],
    { cursor: true, pageSize: PAGE }
  );

  if (loading && rows.length === 0 && !error) return <TabSkeleton />;
  if (error) return <ErrorBox title="Nu am putut încărca activitatea" error={error} onRetry={reload} testid="radacini-admin-activity-error" />;

  const shown = rows.filter((e) => eventInGroup(e.type, group));

  return (
    <div className="space-y-4" data-testid="radacini-admin-activitate">
      <div className="flex flex-wrap items-center gap-3">
        <div className="w-full sm:w-64">
          <SelectField value={group} onValueChange={setGroup} options={EVENT_GROUPS} testid="radacini-admin-activity-filter" />
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 flex-1 min-w-[12rem]">Filtrul se aplică evenimentelor încărcate ({rows.length}).</p>
        <DSButton variant="secondary" icon={RefreshCw} disabled={loading} onClick={reload} data-testid="radacini-admin-activity-reload">
          Reîncarcă
        </DSButton>
      </div>

      {shown.length === 0 ? (
        <div className={CARD}>
          <EmptyState
            icon={Activity}
            title={rows.length === 0 ? "Nicio activitate încă" : "Niciun eveniment pentru acest filtru"}
            hint={rows.length === 0 ? "Evenimentele apar pe măsură ce membrii folosesc Rădăcini." : "Încarcă evenimente mai vechi sau schimbă filtrul."}
            testid="radacini-admin-activity-empty"
          />
        </div>
      ) : (
        <ul className={`${CARD} divide-y divide-slate-100 dark:divide-white/5`} data-testid="radacini-admin-activity-list">
          {shown.map((e) => (
            <li key={e.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 px-4 py-3" data-testid="radacini-admin-activity-item">
              <span className="w-36 shrink-0 text-xs text-slate-500 dark:text-slate-400 tabular-nums">{fmtDateTime(e.created_at)}</span>
              <span className="font-semibold text-sm text-slate-900 dark:text-white">{eventLabel(e.type)}</span>
              <span className="text-sm text-slate-500 dark:text-slate-400">· {firstName(e.actor_name)}</span>
            </li>
          ))}
        </ul>
      )}

      {moreError && (
        <p className="text-sm text-rose-600 dark:text-rose-400" role="alert" data-testid="radacini-admin-activity-more-error">
          Nu am putut încărca evenimentele mai vechi.
        </p>
      )}
      {hasMore && (
        <div className="flex justify-center">
          <DSButton variant="secondary" disabled={loadingMore} onClick={loadMore} data-testid="radacini-admin-activity-older">
            {loadingMore ? "Se încarcă…" : "Mai vechi"}
          </DSButton>
        </div>
      )}
    </div>
  );
}
