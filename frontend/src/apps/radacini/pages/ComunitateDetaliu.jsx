import React, { useCallback, useEffect, useState } from "react";
import ReportButton from "../components/ReportButton";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Check, Megaphone, Pin, Trash2, Users, Vote, X } from "lucide-react";
import { useAuth } from "../../../auth";
import { CARD, DSButton, EmptyState, TabBar } from "../../../design-system";
import { Textarea } from "../../../components/ui/textarea";
import { useConfirm } from "../components/ConfirmDialog";
import DecisionsPanel from "../components/DecisionsPanel";
import { asList, errMsg } from "../api";
import { s6aApi } from "../api_s6a";
import { PageSkeleton, RoleBadge, fmtDateTime } from "../shared";

const TABS = [
  ["anunturi", "Anunțuri", Megaphone],
  ["membri", "Membri", Users],
  ["decizii", "Decizii", Vote],
];

function Posts({ id, isActive, isCoord, me }) {
  const [confirm, confirmDialog] = useConfirm();
  const [state, setState] = useState({ loading: true, items: [], error: null });
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [pinned, setPinned] = useState(false);
  const load = useCallback(() => {
    s6aApi
      .posts(id)
      .then((d) => setState({ loading: false, items: asList(d), error: null }))
      .catch((error) => setState({ loading: false, items: [], error }));
  }, [id]);
  useEffect(load, [load]);

  const publish = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    try {
      await s6aApi.createPost(id, isCoord && pinned ? { text: text.trim(), pinned: true } : { text: text.trim() });
      setText("");
      load();
    } catch (err) {
      toast.error(errMsg(err, "Nu am putut publica anunțul"));
    } finally {
      setBusy(false);
    }
  };
  const remove = async (p) => {
    if (!(await confirm({ title: "Ștergi anunțul?", confirmLabel: "Șterge", danger: true }))) return;
    try {
      await s6aApi.deletePost(p.id);
      load();
    } catch (err) {
      toast.error(errMsg(err, "Nu am putut șterge anunțul"));
    }
  };

  if (state.loading) return <PageSkeleton />;
  if (state.error) return <EmptyState icon={Megaphone} title="Anunțurile sunt vizibile doar membrilor activi" hint={errMsg(state.error)} />;
  return (
    <div className="space-y-4" data-testid="radacini-comunitate-anunturi">
      {confirmDialog}
      {isActive && (
        <form onSubmit={publish} className={`${CARD} p-4 space-y-3`}>
          <Textarea rows={3} maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} placeholder="Scrie un anunț pentru comunitate" data-testid="radacini-anunt-text" />
          <div className="flex flex-wrap items-center justify-between gap-2">
            {isCoord ? (
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                <input type="checkbox" checked={pinned} onChange={(e) => setPinned(e.target.checked)} /> Fixează sus
              </label>
            ) : (
              <span />
            )}
            <DSButton type="submit" disabled={busy || !text.trim()} data-testid="radacini-anunt-publica">
              Publică
            </DSButton>
          </div>
        </form>
      )}
      {state.items.length === 0 ? (
        <EmptyState icon={Megaphone} title="Niciun anunț încă" />
      ) : (
        <ul className="space-y-3">
          {state.items.map((p) => (
            <li key={p.id} className={`${CARD} p-4 space-y-1.5`} data-testid={`radacini-post-${p.id}`}>
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span className="font-semibold text-slate-700 dark:text-slate-200 inline-flex items-center gap-1">
                  {p.pinned && <Pin className="w-3.5 h-3.5 text-emerald-600" />}
                  {p.author_name || p.name || "Membru"}
                </span>
                <span>{fmtDateTime(p.created_at)}</span>
              </div>
              <p className="text-sm text-slate-800 dark:text-slate-100 whitespace-pre-line break-words">{p.text}</p>
              {(isCoord || p.author_user_id === me || p.user_id === me) && (
                <div className="flex justify-end">
                  <DSButton variant="ghost" icon={Trash2} onClick={() => remove(p)}>
                    Șterge
                  </DSButton>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function ComunitateDetaliu() {
  const { id } = useParams();
  const { user } = useAuth();
  const [confirm, confirmDialog] = useConfirm();
  const [sp, setSp] = useSearchParams();
  const [data, setData] = useState({ loading: true, error: null, community: null, members: [] });
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    s6aApi
      .community(id)
      .then((d) => {
        const community = d?.community ?? d;
        setData({ loading: false, error: null, community, members: d?.members || community?.members || [] });
      })
      .catch((error) => setData((s) => ({ ...s, loading: false, error })));
  }, [id]);
  useEffect(load, [load]);

  const back = (
    <Link to="/radacini/comunitati" className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline">
      <ArrowLeft className="w-4 h-4" /> Înapoi la comunități
    </Link>
  );
  if (data.loading) return <PageSkeleton />;
  if (data.error || !data.community) {
    return (
      <div className="space-y-4">
        {back}
        <EmptyState icon={Users} title="Comunitatea nu există" hint={data.error ? errMsg(data.error) : undefined} />
      </div>
    );
  }
  const { community: c, members } = data;
  const myRole = c.my_role ?? members.find((m) => m.user_id === user?.id)?.role ?? null;
  const myStatus = c.my_status ?? (myRole ? members.find((m) => m.user_id === user?.id)?.status ?? "active" : null);
  const isActive = !!myRole && myStatus !== "pending";
  const isCoord = isActive && myRole === "coordinator";
  const tabParam = sp.get("tab");
  const active = TABS.some(([t]) => t === tabParam) ? tabParam : "anunturi";

  const act = async (fn, okMsg, errFallback) => {
    setBusy(true);
    try {
      await fn();
      if (okMsg) toast.success(okMsg);
      load();
    } catch (e) {
      toast.error(errMsg(e, errFallback));
    } finally {
      setBusy(false);
    }
  };
  const leave = async () => {
    if (!(await confirm({ title: "Părăsești comunitatea?", confirmLabel: "Părăsesc", danger: true }))) return;
    act(() => s6aApi.leaveCommunity(id), "Ai părăsit comunitatea", "Nu am putut părăsi comunitatea");
  };

  const pending = members.filter((m) => m.status === "pending");
  const activeMembers = members.filter((m) => m.status !== "pending");

  return (
    <div className="space-y-5 max-w-4xl" data-testid="radacini-comunitate-detaliu">
      {back}
      {confirmDialog}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white break-words">{c.name}</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {c.locality} · {c.members_count ?? activeMembers.length} membri · {c.visibility === "closed" ? "Închisă" : "Deschisă"}
          </p>
          {c.description && <p className="text-sm text-slate-700 dark:text-slate-200 mt-2 whitespace-pre-line break-words">{c.description}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {myRole && isActive && <RoleBadge role={myRole} />}
          {myRole !== "coordinator" && <ReportButton targetType="community" targetId={id} />}
          {myStatus === "pending" && <span className="text-xs font-bold rounded-full bg-amber-50 text-amber-700 px-2.5 py-0.5">Cerere în așteptare</span>}
          {!myRole && (
            <DSButton disabled={busy} onClick={() => act(() => s6aApi.joinCommunity(id), c.visibility === "closed" ? "Cererea a fost trimisă" : "Ai intrat în comunitate", "Nu am putut intra")} data-testid="radacini-comunitate-intra">
              {c.visibility === "closed" ? "Cere acces" : "Intră în comunitate"}
            </DSButton>
          )}
          {myRole && (
            <DSButton variant="secondary" disabled={busy} onClick={leave} data-testid="radacini-comunitate-paraseste">
              Părăsește
            </DSButton>
          )}
        </div>
      </div>

      {isActive ? (
        <>
          <TabBar tabs={TABS} active={active} onChange={(t) => setSp(t === "anunturi" ? {} : { tab: t }, { replace: true })} testidPrefix="radacini-comunitate-tab" />
          {active === "anunturi" && <Posts id={id} isActive={isActive} isCoord={isCoord} me={user?.id} />}
          {active === "membri" && (
            <div className="space-y-4" data-testid="radacini-comunitate-membri">
              {isCoord && pending.length > 0 && (
                <section className={`${CARD} p-4 space-y-2`}>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">Cereri de aderare</h3>
                  {pending.map((m) => (
                    <div key={m.user_id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                      <span className="font-semibold text-slate-800 dark:text-slate-100">{m.name || "Membru"}</span>
                      <span className="flex gap-2">
                        <DSButton variant="success" icon={Check} disabled={busy} onClick={() => act(() => s6aApi.memberAction(id, m.user_id, "approve"), "Aprobat", "Nu am putut aproba")}>
                          Aprobă
                        </DSButton>
                        <DSButton variant="danger" icon={X} disabled={busy} onClick={() => act(() => s6aApi.memberAction(id, m.user_id, "reject"), "Respins", "Nu am putut respinge")}>
                          Respinge
                        </DSButton>
                      </span>
                    </div>
                  ))}
                </section>
              )}
              <ul className="space-y-2">
                {activeMembers.map((m) => (
                  <li key={m.user_id} className={`${CARD} p-3 flex flex-wrap items-center justify-between gap-2`}>
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">{m.name || "Membru"}</span>
                    <span className="flex items-center gap-2">
                      <RoleBadge role={m.role === "coordinator" ? "coordinator" : "participant"} />
                      {isCoord && m.role !== "coordinator" && (
                        <DSButton variant="ghost" disabled={busy} onClick={() => act(() => s6aApi.memberAction(id, m.user_id, "promote"), "Promovat coordonator", "Nu am putut promova")}>
                          Fă coordonator
                        </DSButton>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {active === "decizii" && <DecisionsPanel scope="community" scopeId={id} canVote={isActive} canCreate={isCoord} />}
        </>
      ) : (
        <EmptyState icon={Users} title={myStatus === "pending" ? "Cererea ta așteaptă aprobarea coordonatorului" : "Intră în comunitate pentru a vedea anunțurile, membrii și deciziile"} />
      )}
    </div>
  );
}
