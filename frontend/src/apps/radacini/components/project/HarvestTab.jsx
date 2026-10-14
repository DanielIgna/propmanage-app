import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Plus, ShoppingBasket, Trash2, Wheat } from "lucide-react";
import { useConfirm } from "../ConfirmDialog";
import { CARD, DSButton, EmptyState } from "../../../../design-system";
import { Input } from "../../../../components/ui/input";
import { radaciniApi, asList, errMsg } from "../../api";
import {
  BasisBadge,
  Field,
  PageHeader,
  PageSkeleton,
  SelectField,
  StatusBadge,
  fmtDate,
  fmtKg,
} from "../../shared";
import RecordHarvestDialog from "./RecordHarvestDialog";
import PhotoGallery from "../PhotoGallery";

// Panoul de alocări al unei recolte confirmate: bară alocat/rămas, listă, adăugare (coordonator).
function AllocationsPanel({ harvest, projectId, members, isMember, canCoord, me }) {
  const navigate = useNavigate();
  const [confirm, confirmDialog] = useConfirm();
  const [state, setState] = useState({ loaded: false, items: [], allocated_kg: 0, remaining_kg: Number(harvest.quantity_kg) });
  const [tick, setTick] = useState(0);
  const [form, setForm] = useState({ member: "", kg: "" });
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    let alive = true;
    radaciniApi
      .harvestAllocations(harvest.id)
      .then(
        (d) =>
          alive &&
          setState({
            loaded: true,
            items: asList(d),
            allocated_kg: Number(d?.allocated_kg || 0),
            remaining_kg: Number(d?.remaining_kg ?? harvest.quantity_kg),
          })
      )
      .catch((e) => {
        if (!alive) return;
        toast.error(errMsg(e, "Nu am putut încărca alocările"));
        setState((s) => ({ ...s, loaded: true }));
      });
    return () => {
      alive = false;
    };
  }, [harvest.id, harvest.quantity_kg, tick]);

  const refresh = () => setTick((t) => t + 1);
  const total = Number(harvest.quantity_kg || 0);
  const pct = total > 0 ? Math.min(100, Math.round((state.allocated_kg / total) * 100)) : 0;
  const kg = Number(form.kg);
  const canAdd = isMember && canCoord && state.remaining_kg > 0;
  // Ștergerea alocărilor manuale nu depinde de cantitatea rămasă (ex. recolta e alocată integral).
  const canDelete = isMember && canCoord;
  const addValid = !!form.member && kg > 0 && kg <= state.remaining_kg;
  const memberOpts = members.map((m) => ({ id: m.user_id, label: m.name }));

  const add = async () => {
    if (!addValid) return;
    setSaving(true);
    try {
      await radaciniApi.createAllocation(harvest.id, { member_user_id: form.member, quantity_kg: kg });
      toast.success("Alocarea a fost adăugată");
      setForm({ member: "", kg: "" });
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Alocarea nu a putut fi adăugată"));
    } finally {
      setSaving(false);
    }
  };

  const received = async (a) => {
    setBusy(a.id);
    try {
      await radaciniApi.allocationReceived(a.id);
      toast.success("Primirea a fost consemnată");
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut consemna primirea"));
    } finally {
      setBusy(null);
    }
  };

  const remove = async (a) => {
    if (
      !(await confirm({
        title: "Ștergi alocarea?",
        description: `${a.member_name} · ${fmtKg(a.quantity_kg)} va fi eliberată din recoltă.`,
        confirmLabel: "Șterge",
        danger: true,
      }))
    )
      return;
    setBusy(a.id);
    try {
      await radaciniApi.deleteAllocation(a.id);
      toast.success("Alocarea a fost ștearsă");
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Alocarea nu a putut fi ștearsă"));
    } finally {
      setBusy(null);
    }
  };

  // Alocarea mea → formularul de anunț, pre-completat din recoltă.
  const sell = (a) =>
    navigate(
      `/radacini/piata/nou?${new URLSearchParams({ product: harvest.crop, qty: String(a.quantity_kg), unit: "kg", project_id: projectId })}`
    );

  if (!state.loaded) return <PageSkeleton />;

  return (
    <div className="space-y-3 rounded-xl bg-slate-50 dark:bg-white/5 p-3 md:p-4" data-testid={`radacini-alocari-${harvest.id}`}>
      <div className="space-y-1.5">
        <div className="flex flex-wrap justify-between gap-2 text-xs font-semibold text-slate-600 dark:text-slate-300">
          <span data-testid={`radacini-alocari-alocat-${harvest.id}`}>Alocat: {fmtKg(state.allocated_kg)} din {fmtKg(total)}</span>
          <span data-testid={`radacini-alocari-ramas-${harvest.id}`}>Rămas: {fmtKg(state.remaining_kg)}</span>
        </div>
        <div className="h-2 w-full rounded-full bg-slate-200 dark:bg-white/10 overflow-hidden">
          <div className="h-full bg-emerald-500 transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>

      {canAdd && (
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_9rem_auto] gap-2 items-end" data-testid={`radacini-alocare-form-${harvest.id}`}>
          <Field label="Membru" htmlFor={`alloc-member-${harvest.id}`}>
            <SelectField
              id={`alloc-member-${harvest.id}`}
              value={form.member}
              onValueChange={(v) => setForm((f) => ({ ...f, member: v }))}
              options={memberOpts}
              placeholder="Alege membrul"
              testid={`radacini-alocare-membru-${harvest.id}`}
            />
          </Field>
          <Field label="Cantitate (kg)" htmlFor={`alloc-kg-${harvest.id}`}>
            <Input
              id={`alloc-kg-${harvest.id}`}
              type="number"
              min="0"
              step="any"
              max={state.remaining_kg}
              value={form.kg}
              onChange={(e) => setForm((f) => ({ ...f, kg: e.target.value }))}
              data-testid={`radacini-alocare-kg-${harvest.id}`}
            />
          </Field>
          <DSButton variant="primary" disabled={!addValid || saving} onClick={add} data-testid={`radacini-alocare-adauga-${harvest.id}`}>
            {saving ? "Se adaugă…" : "Adaugă"}
          </DSButton>
        </div>
      )}

      {state.items.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400" data-testid={`radacini-alocari-gol-${harvest.id}`}>
          Nicio alocare încă.
        </p>
      ) : (
        <ul className="divide-y divide-slate-200 dark:divide-white/10" data-testid={`radacini-alocari-lista-${harvest.id}`}>
          {state.items.map((a) => {
            const mine = !!me && a.member_user_id === me;
            return (
              <li key={a.id} className="py-2.5 flex flex-wrap items-center justify-between gap-2" data-testid={`radacini-alocare-${a.id}`}>
                <div className="min-w-0 space-y-1">
                  <p className="text-sm font-semibold text-slate-900 dark:text-white break-words">
                    {a.member_name} · {fmtKg(a.quantity_kg)}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    <BasisBadge basis={a.basis} testid={`radacini-alocare-basis-${a.id}`} />
                    <StatusBadge status={a.status} testid={`radacini-alocare-status-${a.id}`} />
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {mine && isMember && a.status === "allocated" && (
                    <DSButton variant="success" disabled={busy === a.id} onClick={() => received(a)} data-testid={`radacini-alocare-primit-${a.id}`}>
                      Am primit
                    </DSButton>
                  )}
                  {mine && (
                    <DSButton variant="secondary" icon={ShoppingBasket} onClick={() => sell(a)} data-testid={`radacini-alocare-piata-${a.id}`}>
                      Pune în piață
                    </DSButton>
                  )}
                  {canDelete && a.basis === "manual" && a.status === "allocated" && (
                    <DSButton variant="danger" icon={Trash2} disabled={busy === a.id} onClick={() => remove(a)} data-testid={`radacini-alocare-sterge-${a.id}`}>
                      Șterge
                    </DSButton>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
      {confirmDialog}
    </div>
  );
}

// isMember = poate scrie (membru, proiect activ) · isProjectMember = membru al proiectului (și la proiecte finalizate).
// Personalul (doar citire) primește 403 la alocări, deci nu vede butonul „Alocări”.
export default function HarvestTab({ project, members = [], isMember, isProjectMember = isMember, canCoord, me }) {
  const [confirm, confirmDialog] = useConfirm();
  const [data, setData] = useState({ loaded: false, items: [], totals: [] });
  const [tick, setTick] = useState(0);
  const [recordOpen, setRecordOpen] = useState(false);
  const [openId, setOpenId] = useState(null);
  const [confirmingId, setConfirmingId] = useState(null);

  useEffect(() => {
    let alive = true;
    radaciniApi
      .projectHarvests(project.id)
      .then((d) => alive && setData({ loaded: true, items: asList(d), totals: d?.totals || [] }))
      .catch((e) => {
        if (!alive) return;
        toast.error(errMsg(e, "Nu am putut încărca recoltele"));
        setData({ loaded: true, items: [], totals: [] });
      });
    return () => {
      alive = false;
    };
  }, [project.id, tick]);

  const refresh = () => setTick((t) => t + 1);
  const isOwner = !!me && members.some((m) => m.user_id === me && m.role === "owner");

  const confirmHarvest = async (h) => {
    if (
      !(await confirm({
        title: "Confirmi recolta?",
        description: `${h.crop} · ${fmtKg(h.quantity_kg)}. După confirmare se pot face alocările pe membri.`,
        confirmLabel: "Confirmă",
      }))
    )
      return;
    setConfirmingId(h.id);
    try {
      await radaciniApi.confirmHarvest(h.id);
      toast.success("Recolta a fost confirmată");
      setOpenId(h.id);
      refresh();
    } catch (e) {
      toast.error(errMsg(e, "Recolta nu a putut fi confirmată"));
    } finally {
      setConfirmingId(null);
    }
  };

  if (!data.loaded) return <PageSkeleton />;

  return (
    <div className="space-y-5" data-testid="radacini-recolta">
      <PageHeader
        title="Recoltă"
        subtitle="Recolta înregistrată de coordonatori și confirmată de proprietar. Alocările urmează acordul."
        actions={
          canCoord && (
            <DSButton variant="primary" icon={Plus} onClick={() => setRecordOpen(true)} data-testid="radacini-recolta-btn-inregistreaza">
              Înregistrează recolta
            </DSButton>
          )
        }
      />

      {data.totals.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2" data-testid="radacini-recolta-totaluri">
          {data.totals.map((t) => (
            <div key={t.crop} className={`${CARD} px-3 py-2.5`}>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{t.crop}</p>
              <p className="text-base font-bold text-slate-900 dark:text-white">{fmtKg(t.quantity_kg)}</p>
            </div>
          ))}
        </div>
      )}

      {data.items.length === 0 ? (
        <EmptyState
          icon={Wheat}
          title="Nicio recoltă înregistrată"
          hint="Recolta o înregistrează un coordonator și o confirmă proprietarul."
          testid="radacini-recolta-empty"
        />
      ) : (
        <ul className="space-y-3" data-testid="radacini-recolta-lista">
          {data.items.map((h) => {
            const open = openId === h.id && h.status === "confirmed";
            return (
              <li key={h.id} className={`${CARD} p-4 space-y-3`} data-testid={`radacini-recolta-${h.id}`}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-bold text-slate-900 dark:text-white break-words">{h.crop}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      {fmtKg(h.quantity_kg)} · {fmtDate(h.date)}
                    </p>
                  </div>
                  <StatusBadge status={h.status} testid={`radacini-recolta-status-${h.id}`} />
                </div>
                {h.note && <p className="text-sm text-slate-600 dark:text-slate-300">{h.note}</p>}

                <PhotoGallery targetType="harvest" targetId={h.id} canUpload={!!(isMember && canCoord)} title="Fotografii recoltă" />

                <div className="flex flex-wrap gap-2">
                  {isMember && isOwner && h.status === "recorded" && (
                    <DSButton variant="success" disabled={confirmingId === h.id} onClick={() => confirmHarvest(h)} data-testid={`radacini-recolta-confirma-${h.id}`}>
                      {confirmingId === h.id ? "Se confirmă…" : "Confirmă recolta"}
                    </DSButton>
                  )}
                  {h.status === "confirmed" && isProjectMember && (
                    <DSButton variant="secondary" onClick={() => setOpenId(open ? null : h.id)} data-testid={`radacini-recolta-alocari-${h.id}`}>
                      {open ? "Ascunde alocările" : "Alocări"}
                    </DSButton>
                  )}
                </div>

                {h.status === "recorded" && (
                  <p className="text-xs text-slate-500 dark:text-slate-400">Alocările se fac după confirmarea recoltei.</p>
                )}

                {open && isProjectMember && (
                  <AllocationsPanel
                    harvest={h}
                    projectId={project.id}
                    members={members}
                    isMember={isMember}
                    canCoord={canCoord}
                    me={me}
                  />
                )}
              </li>
            );
          })}
        </ul>
      )}

      <RecordHarvestDialog open={recordOpen} onOpenChange={setRecordOpen} projectId={project.id} onSaved={refresh} />
      {confirmDialog}
    </div>
  );
}
