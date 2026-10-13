import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Pause, Pencil, Play, Plus, Send, Sprout, Trash2, AlertTriangle } from "lucide-react";
import { radaciniApi, asList, errMsg } from "../api";
import { useMeta } from "../hooks";
import { Chips, COUNTY, fmtArea, labelOf, linkBtnCls, PageHeader, PageSkeleton, StatusBadge } from "../shared";

const EDITABLE = ["draft", "rejected", "paused"];
const SUBMITTABLE = ["draft", "rejected"];

export default function TerenurileMele() {
  const { meta } = useMeta();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null);

  const fetchMine = useCallback(async () => asList(await radaciniApi.myParcels()), []);

  useEffect(() => {
    let alive = true;
    fetchMine()
      .then((list) => alive && setItems(list))
      .catch((e) => alive && setError(e))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [fetchMine]);

  const run = async (p, action, okMsg) => {
    setBusy(p.id);
    try {
      await action();
      toast.success(okMsg);
      setItems(await fetchMine());
    } catch (e) {
      toast.error(errMsg(e, "Acțiunea nu a reușit"));
    } finally {
      setBusy(null);
    }
  };

  const remove = (p) => {
    if (!window.confirm(`Ștergi terenul „${p.title}”? Nu mai apare în listă.`)) return;
    run(p, () => radaciniApi.deleteParcel(p.id), "Terenul a fost șters");
  };

  const renderActions = (p) => {
    const disabled = busy === p.id;
    if (p.status === "pending_verification") {
      return <p className="text-xs text-slate-500 dark:text-slate-400">Terenul așteaptă verificarea operatorului. Nu mai poate fi editat până atunci.</p>;
    }
    return (
      <div className="flex flex-wrap gap-2">
        {EDITABLE.includes(p.status) && (
          <Link to={`/radacini/terenurile-mele/${p.id}/editare`} className={linkBtnCls("secondary")} data-testid={`radacini-edit-${p.id}`}>
            <Pencil className="w-3.5 h-3.5" /> Editează
          </Link>
        )}
        {SUBMITTABLE.includes(p.status) && (
          <DSButton
            icon={Send}
            disabled={disabled}
            onClick={() => run(p, () => radaciniApi.submitParcel(p.id), "Trimis spre verificare")}
            data-testid={`radacini-submit-${p.id}`}
          >
            Trimite spre verificare
          </DSButton>
        )}
        {p.status === "published" && (
          <DSButton
            variant="secondary"
            icon={Pause}
            disabled={disabled}
            onClick={() => run(p, () => radaciniApi.pauseParcel(p.id), "Terenul este pus pe pauză")}
            data-testid={`radacini-pause-${p.id}`}
          >
            Pauză
          </DSButton>
        )}
        {p.status === "paused" && (
          <DSButton
            variant="secondary"
            icon={Play}
            disabled={disabled}
            onClick={() => run(p, () => radaciniApi.resumeParcel(p.id), "Terenul este publicat din nou")}
            data-testid={`radacini-resume-${p.id}`}
          >
            Reia
          </DSButton>
        )}
        <DSButton          variant="ghost"
          icon={Trash2}
          disabled={disabled}
          onClick={() => remove(p)}
          data-testid={`radacini-delete-${p.id}`}
        >
          Șterge
        </DSButton>
      </div>
    );
  };

  return (
    <div className="space-y-5" data-testid="radacini-terenurile-mele">
      <PageHeader
        title="Terenurile mele"
        subtitle={`Terenurile tale din ${COUNTY}. Un teren ajunge public după verificarea operatorului.`}
        actions={
          <Link to="/radacini/terenurile-mele/nou" className={linkBtnCls()} data-testid="radacini-btn-teren-nou">
            <Plus className="w-3.5 h-3.5" /> Adaugă teren
          </Link>
        }
      />

      {loading ? (
        <PageSkeleton />
      ) : error ? (
        <EmptyState icon={AlertTriangle} title="Nu am putut încărca terenurile" hint={errMsg(error)} testid="radacini-mele-error" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Sprout}
          title="Nu ai adăugat niciun teren"
          hint="Adaugă primul teren ca să apară în listă după verificare."
          action={
            <Link to="/radacini/terenurile-mele/nou" className={linkBtnCls()} data-testid="radacini-mele-empty-add">
              Adaugă teren
            </Link>
          }
          testid="radacini-mele-empty"
        />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {items.map((p) => (
            <div key={p.id} className={`${CARD} p-4 md:p-5 space-y-3`} data-testid={`radacini-mine-${p.id}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-bold text-slate-900 dark:text-white break-words">{p.title}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {p.locality} · {fmtArea(p.area_m2)}
                  </p>
                </div>
                <StatusBadge status={p.status} testid={`radacini-status-${p.id}`} />
              </div>
              <Chips items={(p.offer?.models || []).map((m) => labelOf(meta?.offer_models, m))} />
              {p.status === "rejected" && p.verification?.note && (
                <p className="rounded-xl bg-rose-50 dark:bg-rose-500/10 px-3 py-2 text-sm text-rose-700 dark:text-rose-300">
                  Motiv: {p.verification.note}
                </p>
              )}
              {renderActions(p)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
