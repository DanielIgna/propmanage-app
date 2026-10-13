import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { FileSignature } from "lucide-react";
import { useAuth } from "../../../auth";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { radaciniApi, asList, errMsg } from "../api";
import { useMeta } from "../hooks";
import {
  fmtPeriod,
  labelOf,
  PageHeader,
  PageSkeleton,
  signedCount,
  StatusBadge,
} from "../shared";

export default function Acorduri() {
  const { user } = useAuth();
  const { meta } = useMeta();
  // loaded=false până la răspuns: afișăm skeleton.
  const [data, setData] = useState({ loaded: false, items: [] });

  useEffect(() => {
    let alive = true;
    radaciniApi
      .agreements()
      .then((d) => alive && setData({ loaded: true, items: asList(d) }))
      .catch((e) => {
        if (!alive) return;
        toast.error(errMsg(e, "Nu am putut încărca acordurile"));
        setData({ loaded: true, items: [] });
      });
    return () => {
      alive = false;
    };
  }, []);

  if (!data.loaded) return <PageSkeleton />;

  return (
    <div className="space-y-5 max-w-4xl" data-testid="radacini-acorduri">
      <PageHeader title="Acorduri" subtitle="Termenii colaborărilor, versiunile și semnăturile." />

      {data.items.length === 0 ? (
        <EmptyState
          icon={FileSignature}
          title="Nu ai niciun acord"
          hint="Acordul se creează automat când o cerere de teren este acceptată."
          action={
            <Link to="/radacini/cereri">
              <DSButton variant="secondary">Vezi cererile</DSButton>
            </Link>
          }
          testid="radacini-acorduri-empty"
        />
      ) : (
        <div className="space-y-3" data-testid="radacini-acorduri-list">
          {data.items.map((a) => {
            const snap = a.terms?.parcel_snapshot || {};
            const counterpart = (a.parties || []).find((p) => p.user_id !== user?.id);
            const total = (a.parties || []).length;
            return (
              <Link
                key={a.id}
                to={`/radacini/acorduri/${a.id}`}
                className={`${CARD} block p-4 md:p-5 space-y-3 hover:border-emerald-300 dark:hover:border-emerald-500/40 transition-colors`}
                data-testid={`radacini-acord-${a.id}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-bold text-slate-900 dark:text-white break-words">{snap.title || "Acord de colaborare"}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      {snap.locality || "—"} · {labelOf(meta?.offer_models, a.model)}
                    </p>
                  </div>
                  <StatusBadge status={a.status} testid={`radacini-acord-status-${a.id}`} />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-sm text-slate-600 dark:text-slate-300">
                  <p>Perioadă: {a.terms?.start_date ? fmtPeriod(a.terms.start_date, a.terms.end_date) : "—"}</p>
                  <p>Versiunea {a.version}</p>
                  <p>Cu: {counterpart?.name || "—"}</p>
                  <p>
                    Semnături: {signedCount(a)}/{total}
                  </p>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
