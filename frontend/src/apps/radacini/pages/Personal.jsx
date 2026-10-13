import React, { useCallback, useEffect, useState } from "react";
import { useConfirm } from "../components/ConfirmDialog";
import { toast } from "sonner";
import { AlertTriangle, ShieldOff, Trash2, UserPlus, Users } from "lucide-react";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Input } from "../../../components/ui/input";
import { radaciniApi, asList, errMsg } from "../api";
import { useMeta, useStaffMe } from "../hooks";
import { CheckGroup, Chips, Field, labelOf, PageHeader, PageSkeleton, ROLES, SelectField, toOpts } from "../shared";

const EMPTY_FORM = { email: "", role: "operator", areas: [] };

export default function Personal() {
  const [confirm, confirmDialog] = useConfirm();
  const { staff, loading: staffLoading } = useStaffMe();
  const { meta } = useMeta();
  const isManager = staff?.role === "manager";
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const fetchStaff = useCallback(async () => asList(await radaciniApi.staffList()), []);

  useEffect(() => {
    if (staffLoading) return undefined;
    if (!isManager) {
      setLoading(false);
      return undefined;
    }
    let alive = true;
    fetchStaff()
      .then((list) => alive && setItems(list))
      .catch((e) => alive && setError(e))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [staffLoading, isManager, fetchStaff]);

  if (staffLoading || loading) return <PageSkeleton />;
  if (!isManager) {
    return <EmptyState icon={ShieldOff} title="Doar managerii pot gestiona personalul" testid="radacini-personal-noaccess" />;
  }

  const add = async (e) => {
    e.preventDefault();
    if (!form.email.trim()) return toast.error("Introdu emailul utilizatorului.");
    setSaving(true);
    try {
      await radaciniApi.addStaff({ email: form.email.trim(), role: form.role, areas: form.areas });
      toast.success("Membru adăugat");
      setForm(EMPTY_FORM);
      setItems(await fetchStaff());
    } catch (err) {
      toast.error(errMsg(err, "Nu am putut adăuga membrul"));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (m) => {
    if (!(await confirm({ title: "Ștergi accesul?", description: `${m.name || m.email} nu va mai avea acces de personal Rădăcini.`, confirmLabel: "Șterge accesul", danger: true }))) return;
    try {
      await radaciniApi.removeStaff(m.user_id);
      toast.success("Acces eliminat");
      setItems((list) => list.filter((x) => x.user_id !== m.user_id));
    } catch (err) {
      toast.error(errMsg(err, "Nu am putut elimina accesul"));
    }
  };

  const localityOpts = toOpts(meta?.localities || []);

  return (
    <div className="space-y-6" data-testid="radacini-personal">
      {confirmDialog}
      <PageHeader title="Personal Rădăcini" subtitle="Operatorii verifică terenurile. Managerii gestionează accesul." />

      <form onSubmit={add} className={`${CARD} p-5 md:p-6 space-y-5`} data-testid="radacini-personal-form">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white">Adaugă membru</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Email" htmlFor="personal-email" hint="Utilizatorul trebuie să aibă deja cont în PropManage.">
            <Input
              id="personal-email"
              type="email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              placeholder="nume@exemplu.ro"
              data-testid="radacini-personal-email"
            />
          </Field>
          <Field label="Rol" htmlFor="personal-rol">
            <SelectField
              id="personal-rol"
              value={form.role}
              onValueChange={(v) => setForm((f) => ({ ...f, role: v }))}
              options={ROLES}
              testid="radacini-personal-rol"
            />
          </Field>
        </div>
        <Field label="Localități" hint="Lasă goală pentru toate localitățile.">
          <CheckGroup
            name="personal-areas"
            options={localityOpts}
            value={form.areas}
            onChange={(v) => setForm((f) => ({ ...f, areas: v }))}
            testid="radacini-personal-areas"
            columns="sm:grid-cols-3"
          />
        </Field>
        <div className="flex justify-end">
          <DSButton type="submit" disabled={saving} icon={UserPlus} data-testid="radacini-personal-adauga">
            {saving ? "Se adaugă…" : "Adaugă membru"}
          </DSButton>
        </div>
      </form>

      {error ? (
        <EmptyState icon={AlertTriangle} title="Nu am putut încărca personalul" hint={errMsg(error)} testid="radacini-personal-error" />
      ) : items.length === 0 ? (
        <EmptyState icon={Users} title="Niciun membru al personalului" testid="radacini-personal-empty" />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {items.map((m) => (
            <div key={m.user_id} className={`${CARD} p-4 flex items-start justify-between gap-3`} data-testid={`radacini-staff-${m.user_id}`}>
              <div className="min-w-0 space-y-2">
                <div>
                  <p className="font-bold text-slate-900 dark:text-white break-words">{m.name || m.email}</p>
                  <p className="text-sm text-slate-500 dark:text-slate-400 break-all">{m.email}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-md bg-emerald-50 dark:bg-emerald-500/10 px-2 py-0.5 text-[11px] font-bold text-emerald-700 dark:text-emerald-300">
                    {labelOf(ROLES, m.role)}
                  </span>
                  {m.areas?.length ? <Chips items={m.areas} /> : <span className="text-xs text-slate-500 dark:text-slate-400">Toate localitățile</span>}
                </div>
              </div>
              <DSButton variant="ghost" icon={Trash2} onClick={() => remove(m)} data-testid={`radacini-staff-delete-${m.user_id}`}>
                Șterge
              </DSButton>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
