import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Landmark } from "lucide-react";
import { CARD, EmptyState } from "../../../../design-system";
import { Input } from "../../../../components/ui/input";
import { asList } from "../../api";
import { ASSOC_TYPE, assocList, fmtShare } from "../../api_s9";
import { PageHeader, PageSkeleton, linkBtnCls } from "../../shared";
import TransparencyBadge from "../../components/assoc/TransparencyBadge";

function Card({ a }) {
  return (
    <Link to={`/radacini/composesorate/${a.id}`} className={`${CARD} p-4 block hover:shadow-md transition-shadow`} data-testid={`assoc-card-${a.id}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-bold text-slate-900 dark:text-white break-words">{a.name}</h3>
          <p className="text-xs text-slate-500">{ASSOC_TYPE[a.type] || a.type} · {(a.localities || []).join(", ")}</p>
        </div>
        {a.transparency_score != null && <TransparencyBadge assocId={a.id} score={a.transparency_score} />}
      </div>
      <p className="mt-2 text-xs text-slate-600 dark:text-slate-300">{fmtShare(a.total_area_ha)} ha · {a.members_count ?? "—"} membri</p>
    </Link>
  );
}

export default function Composesorate() {
  const [q, setQ] = useState("");
  const [state, setState] = useState({ loading: true, items: [] });
  useEffect(() => {
    const t = setTimeout(() => {
      assocList(q.trim() ? { q: q.trim() } : undefined)
        .then((d) => setState({ loading: false, items: asList(d) }))
        .catch(() => setState({ loading: false, items: [] }));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  if (state.loading) return <PageSkeleton />;
  const mine = state.items.filter((a) => a.mine || a.my_role);
  const others = state.items.filter((a) => !(a.mine || a.my_role));
  return (
    <div className="space-y-5 max-w-5xl" data-testid="composesorate-page">
      <PageHeader
        title="Composesorate"
        subtitle="Asociații de composesori, obști și asociații pastorale: transparent și la vedere."
        actions={
          <>
            <Link to="/radacini/composesorate/revendica" className={linkBtnCls("primary")} data-testid="assoc-revendica-link">Revendică / Sunt moștenitor</Link>
            <Link to="/radacini/composesorate/ghid" className={linkBtnCls("secondary")}>Ghid pentru membri</Link>
          </>
        }
      />
      {mine.length > 0 && (
        <section className="space-y-2">
          <h3 className="font-bold text-slate-900 dark:text-white">Asociațiile mele</h3>
          <div className="grid gap-3 sm:grid-cols-2">{mine.map((a) => <Card key={a.id} a={a} />)}</div>
        </section>
      )}
      <section className="space-y-2">
        <h3 className="font-bold text-slate-900 dark:text-white">Caută asociații</h3>
        <Input placeholder="Nume sau localitate" value={q} onChange={(e) => setQ(e.target.value)} data-testid="assoc-search" />
        {others.length === 0 ? (
          <EmptyState icon={Landmark} title="Nicio asociație găsită." />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">{others.map((a) => <Card key={a.id} a={a} />)}</div>
        )}
      </section>
    </div>
  );
}
