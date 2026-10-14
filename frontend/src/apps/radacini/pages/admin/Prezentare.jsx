import React from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Briefcase, ClipboardCheck, FileSignature, MapPin, RefreshCw, ShieldAlert, Store, Users, Wheat } from "lucide-react";
import { CARD, ChartCard, DSButton, EmptyState, KpiCard, SEMANTIC } from "../../../../design-system";
import { radaciniApi } from "../../api";
import { useMeta } from "../../hooks";
import { fmtDateTime, fmtKg, labelOf, linkBtnCls, RESERVATION_STATUS, STATUS, StatusPill } from "../../shared";
import { ErrorBox, nf, orderedEntries, TabSkeleton, useFetch } from "./adminShared";

const PARCEL_ORDER = ["pending_verification", "published", "draft", "paused", "rejected"];
const REQUEST_ORDER = ["sent", "viewed", "negotiating", "accepted", "declined", "withdrawn", "expired"];
const RESERVATION_ORDER = ["requested", "confirmed", "picked_up", "cancelled", "declined", "no_show"];

const PARCEL_COLOR = {
  pending_verification: SEMANTIC.warning.solid,
  published: SEMANTIC.success.solid,
  draft: SEMANTIC.neutral.solid,
  paused: SEMANTIC.info.solid,
  rejected: SEMANTIC.critical.solid,
};

// Listă „stare → număr” într-un card.
const Breakdown = ({ title, entries, map = STATUS, testid, footer }) => {
  const total = entries.reduce((s, [, n]) => s + n, 0);
  return (
    <div className={`${CARD} p-4 flex flex-col`} data-testid={testid}>
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="font-bold text-slate-800 dark:text-slate-100">{title}</h3>
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{nf(total)} în total</span>
      </div>
      <ul className="mt-3 space-y-2 flex-1">
        {entries.map(([key, n]) => (
          <li key={key} className="flex items-center justify-between gap-2" data-testid={`${testid}-${key}`}>
            <StatusPill def={map[key] || STATUS[key] || { label: key, cls: "bg-slate-100 text-slate-600" }} />
            <span className="text-sm font-bold text-slate-900 dark:text-white tabular-nums">{nf(n)}</span>
          </li>
        ))}
      </ul>
      {footer}
    </div>
  );
};

export default function Prezentare({ onTab }) {
  const { meta } = useMeta();
  const { data: k, loading, error, reload } = useFetch(() => radaciniApi.adminKpis(), []);

  if (loading && !k) return <TabSkeleton />;
  if (error) return <ErrorBox title="Nu am putut încărca indicatorii" error={error} onRetry={reload} testid="radacini-admin-kpis-error" />;

  const parcels = orderedEntries(k?.parcels_by_status, PARCEL_ORDER);
  const requests = orderedEntries(k?.requests_by_status, REQUEST_ORDER);
  const reservations = orderedEntries(k?.reservations_by_status, RESERVATION_ORDER);
  const interests = Object.entries(k?.members_by_interest || {}).sort((a, b) => b[1] - a[1]);
  const chartData = parcels.map(([key, value]) => ({ key, value, label: STATUS[key]?.label || key }));
  const parcelTotal = chartData.reduce((s, d) => s + d.value, 0);
  const pending = Number(k?.pending_verification) || 0;
  const openGdpr = Number(k?.open_deletion_requests) || 0;

  return (
    <div className="space-y-6" data-testid="radacini-admin-prezentare">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-500 dark:text-slate-400" data-testid="radacini-admin-generated">
          {k?.generated_at ? `Actualizat ${fmtDateTime(k.generated_at)} · cifrele se reînnoiesc la cel mult 5 minute` : "Cifre calculate la cerere"}
          {k?.harvest_kg_capped ? " · recolta confirmată este calculată parțial (limită de interogare)" : ""}
        </p>
        <DSButton variant="secondary" icon={RefreshCw} disabled={loading} onClick={reload} data-testid="radacini-admin-reload">
          {loading ? "Se reîncarcă…" : "Reîncarcă"}
        </DSButton>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
        <KpiCard icon={Users} label="Membri" value={nf(k?.members)} accent="info" testid="radacini-kpi-members" />
        <KpiCard icon={FileSignature} label="Acorduri semnate" value={nf(k?.agreements_signed)} accent="success" testid="radacini-kpi-agreements" />
        <KpiCard icon={Briefcase} label="Proiecte active" value={nf(k?.projects_active)} accent="ai" testid="radacini-kpi-projects" />
        <KpiCard icon={Wheat} label="Recoltă confirmată" value={fmtKg(k?.harvest_kg_confirmed)} accent="success" testid="radacini-kpi-harvest" />
        <KpiCard icon={Store} label="Anunțuri active" value={nf(k?.listings_active)} accent="info" testid="radacini-kpi-listings" />
        <KpiCard
          icon={ClipboardCheck}
          label="Terenuri în verificare"
          value={nf(pending)}
          accent={pending > 0 ? "warning" : "neutral"}
          onClick={() => onTab("moderare")}
          testid="radacini-kpi-pending"
        />
        <KpiCard
          icon={ShieldAlert}
          label="Cereri GDPR deschise"
          value={nf(openGdpr)}
          accent={openGdpr > 0 ? "critical" : "neutral"}
          onClick={() => onTab("gdpr")}
          testid="radacini-kpi-gdpr"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Terenuri pe stări" subtitle={`${nf(parcelTotal)} terenuri`} testid="radacini-admin-chart-parcels">
          {parcelTotal === 0 ? (
            <EmptyState icon={MapPin} title="Niciun teren încă" testid="radacini-admin-chart-empty" />
          ) : (
            <div className="h-56" role="img" aria-label="Număr de terenuri pe stări">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.2} horizontal={false} />
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="label" width={104} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => [nf(v), "Terenuri"]} />
                  <Bar dataKey="value" radius={[0, 8, 8, 0]} barSize={18}>
                    {chartData.map((d) => (
                      <Cell key={d.key} fill={PARCEL_COLOR[d.key] || SEMANTIC.neutral.solid} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </ChartCard>

        <Breakdown
          title="Cereri de teren pe stări"
          entries={requests}
          testid="radacini-admin-requests"
        />

        <Breakdown
          title="Rezervări pe stări"
          entries={reservations}
          map={RESERVATION_STATUS}
          testid="radacini-admin-reservations"
        />

        <div className={`${CARD} p-4`} data-testid="radacini-admin-interests">
          <h3 className="font-bold text-slate-800 dark:text-slate-100">Membri pe interese</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Un membru poate avea mai multe interese.</p>
          {interests.length === 0 ? (
            <EmptyState icon={Users} title="Niciun membru încă" testid="radacini-admin-interests-empty" />
          ) : (
            <ul className="mt-3 space-y-2">
              {interests.map(([id, n]) => (
                <li key={id} className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-slate-700 dark:text-slate-200">{labelOf(meta?.interests, id)}</span>
                  <span className="font-bold text-slate-900 dark:text-white tabular-nums">{nf(n)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {pending > 0 && (
        <div className={`${CARD} p-4 flex flex-wrap items-center justify-between gap-3`} data-testid="radacini-admin-pending-cta">
          <p className="text-sm text-slate-700 dark:text-slate-200">
            {nf(pending)} {pending === 1 ? "teren așteaptă" : "terenuri așteaptă"} verificarea operatorului.
          </p>
          <Link to="/radacini/operator" className={linkBtnCls("primary")} data-testid="radacini-admin-open-queue">
            <ClipboardCheck className="w-3.5 h-3.5" /> Deschide coada operatorului
          </Link>
        </div>
      )}
    </div>
  );
}
