import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Inbox, Send } from "lucide-react";
import { CARD, EmptyState, TabBar } from "../../../design-system";
import { radaciniApi, asList, errMsg } from "../api";
import { useMeta } from "../hooks";
import { fmtArea, fmtDateTime, fmtPeriod, fmtRon, labelOf, PageHeader, PageSkeleton, StatusBadge } from "../shared";

const TABS = [
  ["sent", "Trimise", Send],
  ["received", "Primite", Inbox],
];

const EMPTY = {
  sent: { title: "Nu ai trimis nicio cerere", hint: "Găsește un teren în Terenuri și trimite o cerere de colaborare." },
  received: { title: "Nu ai primit cereri", hint: "Cererile pentru terenurile tale publicate apar aici." },
};

const priceLabel = (proposal = {}) => {
  if (proposal.price_ron_per_year != null) return fmtRon(proposal.price_ron_per_year);
  if (proposal.harvest_share_percent != null) return `${proposal.harvest_share_percent}% din recoltă`;
  return null;
};

function RequestCard({ item, modelLabel }) {
  const proposal = item.proposal || {};
  const price = priceLabel(proposal);
  return (
    <Link
      to={`/radacini/cereri/${item.id}`}
      className={`${CARD} block p-4 md:p-5 space-y-3 hover:border-emerald-300 dark:hover:border-emerald-500/40 transition-colors`}
      data-testid={`radacini-cerere-${item.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-bold text-slate-900 dark:text-white break-words">{item.parcel_title || "Teren"}</p>
          <p className="text-sm text-slate-500 dark:text-slate-400">{item.parcel_locality || "—"}</p>
        </div>
        <StatusBadge status={item.status} testid={`radacini-cerere-status-${item.id}`} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-sm text-slate-600 dark:text-slate-300">
        <p>Model: {modelLabel}</p>
        <p>Suprafață: {proposal.area_m2 != null ? fmtArea(proposal.area_m2) : "—"}</p>
        <p>Perioadă: {proposal.start_date ? fmtPeriod(proposal.start_date, proposal.end_date) : "—"}</p>
        {price && <p>Condiții: {price}</p>}
      </div>

      <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
        <span>Cu: {item.counterpart_name || "—"}</span>
        <span>Ultima activitate: {fmtDateTime(item.last_activity_at || item.updated_at)}</span>
      </div>
    </Link>
  );
}

export default function Cereri() {
  const { meta } = useMeta();
  const [tab, setTab] = useState("sent");
  // Starea reține ce tab a fost încărcat; până la potrivire afișăm skeleton.
  const [data, setData] = useState({ tab: null, items: [] });

  useEffect(() => {
    let alive = true;
    const load = tab === "sent" ? radaciniApi.requestsSent : radaciniApi.requestsReceived;
    load()
      .then((d) => alive && setData({ tab, items: asList(d) }))
      .catch((e) => {
        if (!alive) return;
        toast.error(errMsg(e, "Nu am putut încărca cererile"));
        setData({ tab, items: [] });
      });
    return () => {
      alive = false;
    };
  }, [tab]);

  const loading = data.tab !== tab;

  return (
    <div className="space-y-5 max-w-4xl" data-testid="radacini-cereri">
      <PageHeader title="Cereri de teren" subtitle="Cererile trimise de tine și cele primite pentru terenurile tale." />

      <TabBar tabs={TABS} active={tab} onChange={setTab} testidPrefix="radacini-cereri-tab" />

      {loading ? (
        <PageSkeleton />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={tab === "sent" ? Send : Inbox}
          title={EMPTY[tab].title}
          hint={EMPTY[tab].hint}
          action={
            tab === "sent" ? (
              <Link to="/radacini/terenuri" className="text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline">
                Caută terenuri
              </Link>
            ) : undefined
          }
          testid={`radacini-cereri-empty-${tab}`}
        />
      ) : (
        <div className="space-y-3" data-testid={`radacini-cereri-list-${tab}`}>
          {data.items.map((item) => (
            <RequestCard key={item.id} item={item} modelLabel={labelOf(meta?.offer_models, item.model)} />
          ))}
        </div>
      )}
    </div>
  );
}
