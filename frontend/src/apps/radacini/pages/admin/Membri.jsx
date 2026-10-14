import React, { useEffect, useState } from "react";
import { AlertTriangle, Search, Users } from "lucide-react";
import { DataTable, DSButton } from "../../../../design-system";
import { Input } from "../../../../components/ui/input";
import { radaciniApi } from "../../api";
import { useMeta } from "../../hooks";
import { Chips, fmtDate, labelOf, SelectField, toOpts } from "../../shared";
import { clean, ErrorBox, pickCount, TabSkeleton, usePaged } from "./adminShared";

const PAGE = 50;

const normalize = (m) => ({
  ...m,
  name: m.name || "—",
  parcels: pickCount(m, "parcels"),
  projects: pickCount(m, "projects"),
  listings: pickCount(m, "listings"),
});

export default function Membri() {
  const { meta } = useMeta();
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [interest, setInterest] = useState("all");
  const [locality, setLocality] = useState("all");

  useEffect(() => {
    const t = setTimeout(() => setDq(q.trim()), 350);
    return () => clearTimeout(t);
  }, [q]);

  const { rows: raw, total, meta: resp, loading, loadingMore, error, moreError, hasMore, loadMore, reload } = usePaged(
    (skip) => radaciniApi.adminMembers(clean({ q: dq, interest, locality, skip: skip || "", limit: PAGE })),
    [dq, interest, locality],
    { pageSize: PAGE }
  );
  const rows = raw.map(normalize);
  const filtered = dq !== "" || interest !== "all" || locality !== "all";

  const columns = [
    { key: "name", label: "Nume", render: (r) => <span className="font-semibold text-slate-900 dark:text-white">{r.name}</span> },
    { key: "locality", label: "Localitate", render: (r) => r.locality || "—" },
    {
      key: "interests",
      label: "Interese",
      sortable: false,
      render: (r) => (r.interests?.length ? <Chips items={r.interests.map((i) => labelOf(meta?.interests, i))} /> : "—"),
    },
    { key: "parcels", label: "Terenuri" },
    { key: "projects", label: "Proiecte" },
    { key: "listings", label: "Anunțuri active" },
    { key: "created_at", label: "Înscris", render: (r) => fmtDate(r.created_at) },
  ];

  return (
    <div className="space-y-4" data-testid="radacini-admin-membri">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Caută după nume"
            aria-label="Caută membri după nume"
            className="pl-9"
            data-testid="radacini-admin-members-q"
          />
        </div>
        <SelectField
          value={interest}
          onValueChange={setInterest}
          options={[{ id: "all", label: "Toate interesele" }, ...toOpts(meta?.interests || [])]}
          testid="radacini-admin-members-interest"
        />
        <SelectField
          value={locality}
          onValueChange={setLocality}
          options={[{ id: "all", label: "Toate localitățile" }, ...toOpts(meta?.localities || [])]}
          testid="radacini-admin-members-locality"
        />
      </div>

      {resp?.scan_truncated && (
        <p className="flex items-start gap-2 rounded-xl bg-amber-50 dark:bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200" role="status" data-testid="radacini-admin-members-truncated">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" aria-hidden="true" />
          Căutarea după nume a acoperit doar o parte dintre membri. Adaugă un filtru de interes sau de localitate pentru rezultate complete.
        </p>
      )}

      {loading && rows.length === 0 && !error ? (
        <TabSkeleton />
      ) : error ? (
        <ErrorBox title="Nu am putut încărca membrii" error={error} onRetry={reload} testid="radacini-admin-members-error" />
      ) : (
        <>
          <DataTable
            title={`Membri (${(total ?? rows.length).toLocaleString("ro-RO")})`}
            columns={columns}
            rows={rows}
            exportName="radacini-membri"
            emptyTitle={filtered ? "Niciun membru pentru aceste filtre" : "Niciun membru încă"}
            emptyHint={filtered ? "Schimbă sau șterge filtrele." : "Membrii apar după ce își completează profilul Rădăcini."}
            maxHeight="36rem"
            testid="radacini-admin-members-table"
          />
          {moreError && (
            <p className="text-sm text-rose-600 dark:text-rose-400" role="alert" data-testid="radacini-admin-members-more-error">
              Nu am putut încărca următorii membri.
            </p>
          )}
          {hasMore && (
            <div className="flex justify-center">
              <DSButton variant="secondary" icon={Users} disabled={loadingMore} onClick={loadMore} data-testid="radacini-admin-members-more">
                {loadingMore ? "Se încarcă…" : "Încarcă mai mulți"}
              </DSButton>
            </div>
          )}
        </>
      )}
    </div>
  );
}
