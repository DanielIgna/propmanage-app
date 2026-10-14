import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { FileSignature } from "lucide-react";
import { useConfirm } from "../ConfirmDialog";
import DecisionsPanel from "../DecisionsPanel";
import { CARD, DSButton } from "../../../../design-system";
import { radaciniApi, asList, errMsg } from "../../api";
import { useMeta } from "../../hooks";
import { ACTIVITY_TYPES, CONTRIBUTION_KINDS, PageSkeleton, fmtDate, labelOf, optsOr, todayIso, linkBtnCls } from "../../shared";

export default function Overview({ project, members, canCoord, isProjectMember, reload }) {
  const [confirm, confirmDialog] = useConfirm();
  const { meta } = useMeta();
  const types = optsOr(meta?.activity_types, ACTIVITY_TYPES);
  const kinds = optsOr(meta?.contribution_kinds, CONTRIBUTION_KINDS);
  const [state, setState] = useState({ loading: true, activities: [], totals: [] });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    const today = todayIso();
    Promise.all([
      radaciniApi.projectActivities(project.id, { from: today }).catch(() => ({ items: [] })),
      radaciniApi.projectContributions(project.id).catch(() => ({ totals: [] })),
    ]).then(([acts, contribs]) => {
      if (!alive) return;
      const upcoming = asList(acts)
        .filter((a) => a.status === "scheduled" && a.date >= today)
        .sort((a, b) => (a.date + (a.start_time || "")).localeCompare(b.date + (b.start_time || "")))
        .slice(0, 5);
      setState({ loading: false, activities: upcoming, totals: contribs?.totals || [] });
    });
    return () => {
      alive = false;
    };
  }, [project.id, project.updated_at]);

  const memberName = (uid) => members.find((m) => m.user_id === uid)?.name || "—";

  const complete = async () => {
    if (
      !(await confirm({
        title: "Marchezi proiectul ca finalizat?",
        description: "Proiectul devine doar de consultat. Nu mai poți adăuga activități sau contribuții noi.",
        confirmLabel: "Finalizează",
      }))
    )
      return;
    setBusy(true);
    try {
      await radaciniApi.completeProject(project.id);
      toast.success("Proiectul a fost finalizat");
      reload();
    } catch (e) {
      toast.error(errMsg(e, "Proiectul nu a putut fi finalizat"));
    } finally {
      setBusy(false);
    }
  };

  if (state.loading) return <PageSkeleton />;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" data-testid="radacini-proiect-prezentare">
      {confirmDialog}

      <div className="lg:col-span-2 space-y-4">
        <section className={`${CARD} p-5 space-y-3`}>
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">Următoarele activități</h3>
          {state.activities.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400" data-testid="radacini-prezentare-fara-activitati">
              Nicio activitate programată.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-white/5" data-testid="radacini-prezentare-activitati">
              {state.activities.map((a) => (
                <li key={a.id} className="py-2.5 flex flex-wrap items-center justify-between gap-2 text-sm">
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-800 dark:text-slate-100 break-words">{a.title}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {labelOf(types, a.type)} · {fmtDate(a.date)}
                      {a.start_time ? ` · ${a.start_time}` : ""}
                    </p>
                  </div>
                  <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                    {(a.participant_names || []).length} participanți
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className={`${CARD} p-5 space-y-3`}>
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">Totaluri contribuții confirmate</h3>
          {state.totals.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Nicio contribuție înregistrată.</p>
          ) : (
            <ul className="space-y-1.5 text-sm" data-testid="radacini-prezentare-totaluri">
              {state.totals.map((t) => (
                <li key={`${t.member_user_id}-${t.kind}`} className="flex flex-wrap justify-between gap-2">
                  <span className="text-slate-700 dark:text-slate-200">
                    {t.member_name || memberName(t.member_user_id)} · {labelOf(kinds, t.kind)}
                  </span>
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {Number(t.confirmed || 0).toLocaleString("ro-RO")} {t.unit}
                    {t.pending ? (
                      <span className="ml-2 text-xs font-normal text-amber-700 dark:text-amber-300">
                        (+{Number(t.pending).toLocaleString("ro-RO")} în așteptare)
                      </span>
                    ) : null}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <DecisionsPanel scope="project" scopeId={project.id} canVote={!!isProjectMember} canCreate={!!canCoord} />
      </div>

      <div className="space-y-4">
        <section className={`${CARD} p-5 space-y-3`}>
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">Detalii</h3>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-xs font-semibold text-slate-500 dark:text-slate-400">Perioadă</dt>
              <dd className="text-slate-800 dark:text-slate-200">
                {fmtDate(project.start_date)} – {fmtDate(project.end_date)}
              </dd>
            </div>
          </dl>
          {project.agreement_id && (
            <Link
              to={`/radacini/acorduri/${project.agreement_id}`}
              className={linkBtnCls("secondary")}
              data-testid="radacini-proiect-link-acord"
            >
              <FileSignature className="w-3.5 h-3.5" /> Vezi acordul
            </Link>
          )}
        </section>

        {canCoord && project.status === "active" && (
          <section className={`${CARD} p-5 space-y-3`}>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Acțiuni coordonator</h3>
            <DSButton
              variant="secondary"
              disabled={busy}
              onClick={complete}
              className="justify-center w-full"
              data-testid="radacini-proiect-btn-finalizeaza"
            >
              Marchează proiectul finalizat
            </DSButton>
          </section>
        )}
      </div>
    </div>
  );
}
