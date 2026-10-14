import React from "react";
import { DataTable, DSButton } from "../../../../design-system";
import { radaciniApi } from "../../api";
import { fmtDateTime } from "../../shared";
import { auditLabel, auditTarget, ErrorBox, firstName, TabSkeleton, usePaged } from "./adminShared";

const PAGE = 100;

// Motivul / nota din detaliile acțiunii (închiderea anunțului, rezolvarea cererii GDPR, respingerea terenului).
const detailOf = (r) => r.details?.reason || r.details?.note || r.note || "";

export default function Jurnal() {
  const { rows: raw, loading, loadingMore, error, moreError, hasMore, loadMore, reload } = usePaged(
    (before) => radaciniApi.adminAudit({ limit: PAGE, before }),
    [],
    { cursor: true, pageSize: PAGE }
  );

  if (loading && raw.length === 0 && !error) return <TabSkeleton />;
  if (error) return <ErrorBox title="Nu am putut încărca jurnalul" error={error} onRetry={reload} testid="radacini-admin-audit-error" />;

  const rows = raw.map((r) => ({
    ...r,
    actor: firstName(r.actor_name),
    label: auditLabel(r.action),
    target: auditTarget(r.target_type, r.target_id),
    detail: detailOf(r),
  }));

  const columns = [
    { key: "created_at", label: "Când", render: (r) => fmtDateTime(r.created_at) },
    { key: "actor", label: "Cine" },
    { key: "label", label: "Acțiune", render: (r) => <span className="font-semibold text-slate-900 dark:text-white">{r.label}</span> },
    { key: "target", label: "Țintă" },
    { key: "detail", label: "Motiv / notă", render: (r) => <span className="inline-block max-w-xs truncate align-bottom" title={r.detail}>{r.detail || "—"}</span> },
  ];

  return (
    <div className="space-y-4" data-testid="radacini-admin-jurnal">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Acțiunile de administrare Rădăcini (verificări, personal, moderare, cereri GDPR, conturi de test), cele mai noi primele.
      </p>
      <DataTable
        title={`Jurnal de audit (${rows.length}${hasMore ? "+" : ""})`}
        columns={columns}
        rows={rows}
        searchKeys={["actor", "label", "target", "detail"]}
        exportName="radacini-audit"
        emptyTitle="Nicio acțiune în jurnal"
        emptyHint="Acțiunile personalului și ale administratorilor apar aici."
        maxHeight="36rem"
        testid="radacini-admin-audit-table"
      />
      {moreError && (
        <p className="text-sm text-rose-600 dark:text-rose-400" role="alert" data-testid="radacini-admin-audit-more-error">
          Nu am putut încărca intrările mai vechi.
        </p>
      )}
      {hasMore && (
        <div className="flex justify-center">
          <DSButton variant="secondary" disabled={loadingMore} onClick={loadMore} data-testid="radacini-admin-audit-more">
            {loadingMore ? "Se încarcă…" : "Mai vechi"}
          </DSButton>
        </div>
      )}
    </div>
  );
}
