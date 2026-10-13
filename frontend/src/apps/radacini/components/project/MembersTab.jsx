import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { LogOut, Trash2, UserPlus, Users } from "lucide-react";
import { useConfirm } from "../ConfirmDialog";
import { CARD, DSButton } from "../../../../design-system";
import { Input } from "../../../../components/ui/input";
import { radaciniApi, errMsg } from "../../api";
import { Field, PROJECT_ROLE, RoleBadge, SelectField, fmtDate } from "../../shared";

const ROLE_OPTIONS = [
  { id: "coordinator", label: PROJECT_ROLE.coordinator.label },
  { id: "participant", label: PROJECT_ROLE.participant.label },
];

export default function MembersTab({ project, members, isMember, canCoord, me, reload }) {
  const [confirm, confirmDialog] = useConfirm();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);

  const invite = async (e) => {
    e.preventDefault();
    const value = email.trim();
    if (!value) return;
    setBusy(true);
    try {
      await radaciniApi.addProjectMember(project.id, value);
      toast.success("Membrul a fost adăugat ca participant");
      setEmail("");
      reload();
    } catch (err) {
      toast.error(errMsg(err, "Membrul nu a putut fi adăugat"));
    } finally {
      setBusy(false);
    }
  };

  const changeRole = async (m, role) => {
    if (role === m.role) return;
    setBusy(true);
    try {
      await radaciniApi.updateProjectMember(project.id, m.user_id, role);
      toast.success(`Rolul lui ${m.name || "membrului"} a fost schimbat`);
      reload();
    } catch (err) {
      toast.error(errMsg(err, "Rolul nu a putut fi schimbat"));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (m) => {
    const self = m.user_id === me;
    if (
      !(await confirm({
        title: self ? "Părăsești proiectul?" : "Elimini membrul din proiect?",
        description: self
          ? "Nu mai vei putea adăuga contribuții sau să te înscrii la activități în acest proiect."
          : `${m.name || "Membrul"} nu va mai avea acces la planul și activitățile proiectului.`,
        confirmLabel: self ? "Părăsește" : "Elimină",
        danger: true,
      }))
    )
      return;
    setBusy(true);
    try {
      await radaciniApi.removeProjectMember(project.id, m.user_id);
      toast.success(self ? "Ai părăsit proiectul" : "Membrul a fost eliminat");
      if (self) navigate("/radacini/proiecte");
      else reload();
    } catch (err) {
      toast.error(errMsg(err, "Membrul nu a putut fi eliminat"));
    } finally {
      setBusy(false);
    }
  };

  const sorted = [...members].sort((a, b) => {
    const order = { owner: 0, coordinator: 1, participant: 2 };
    return (order[a.role] ?? 9) - (order[b.role] ?? 9);
  });

  return (
    <div className="space-y-4" data-testid="radacini-membri">
      {confirmDialog}

      {canCoord && (
        <section className={`${CARD} p-4 md:p-5 space-y-3`} data-testid="radacini-membri-invita">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">Invită un membru</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Invitatul trebuie să aibă deja cont în PropManage. Intră ca participant; poate fi promovat ulterior.
          </p>
          <form onSubmit={invite} className="flex flex-col sm:flex-row gap-2">
            <div className="flex-1 min-w-0">
              <Field label="Email" htmlFor="invite-email">
                <Input
                  id="invite-email"
                  type="email"
                  autoComplete="off"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="nume@exemplu.ro"
                  data-testid="radacini-membri-email"
                />
              </Field>
            </div>
            <div className="sm:self-end">
              <DSButton
                type="submit"
                variant="primary"
                icon={UserPlus}
                disabled={busy || !email.trim()}
                className="w-full sm:w-auto justify-center"
                data-testid="radacini-membri-invita-btn"
              >
                Invită
              </DSButton>
            </div>
          </form>
        </section>
      )}

      <ul className="space-y-2" data-testid="radacini-membri-lista">
        {sorted.map((m) => {
          const self = m.user_id === me;
          const isOwner = m.role === "owner";
          const canChangeRole = canCoord && !isOwner;
          const canRemove = !isOwner && (canCoord || (isMember && self));
          return (
            <li
              key={m.user_id}
              className={`${CARD} p-4 flex flex-col sm:flex-row sm:items-center gap-3`}
              data-testid={`radacini-membru-${m.user_id}`}
            >
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-slate-900 dark:text-white break-words">
                  {m.name || "—"} {self && <span className="text-xs font-normal text-slate-500 dark:text-slate-400">(tu)</span>}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {m.joined_at ? `Membru din ${fmtDate(m.joined_at)}` : "Membru"}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                {canChangeRole ? (
                  <div className="w-44">
                    <SelectField
                      id={`role-${m.user_id}`}
                      value={m.role}
                      onValueChange={(role) => changeRole(m, role)}
                      options={ROLE_OPTIONS}
                      testid={`radacini-membru-rol-${m.user_id}`}
                    />
                  </div>
                ) : (
                  <RoleBadge role={m.role} testid={`radacini-membru-rol-badge-${m.user_id}`} />
                )}

                {canRemove && (
                  <DSButton
                    variant="danger"
                    icon={self && !canCoord ? LogOut : Trash2}
                    disabled={busy}
                    onClick={() => remove(m)}
                    data-testid={self && !canCoord ? "radacini-membru-paraseste" : `radacini-membru-elimina-${m.user_id}`}
                  >
                    {self && !canCoord ? "Părăsește" : "Elimină"}
                  </DSButton>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      {members.length === 0 && (
        <p className="text-sm text-slate-500 dark:text-slate-400 flex items-center gap-2">
          <Users className="w-4 h-4" /> Niciun membru.
        </p>
      )}
    </div>
  );
}
