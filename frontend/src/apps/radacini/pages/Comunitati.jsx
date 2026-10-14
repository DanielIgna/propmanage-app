import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Plus, Users } from "lucide-react";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import { asList, errMsg } from "../api";
import { s6aApi } from "../api_s6a";
import { useMeta } from "../hooks";
import { Field, PageHeader, PageSkeleton, SelectField, toOpts } from "../shared";

const ALL = "__all__";
const VIS = [
  { id: "open", label: "Deschisă (oricine intră)" },
  { id: "closed", label: "Închisă (cu aprobare)" },
];

export default function Comunitati() {
  const nav = useNavigate();
  const { meta } = useMeta();
  const localities = toOpts(meta?.localities || []);
  const [filters, setFilters] = useState({ locality: ALL, q: "" });
  const [state, setState] = useState({ loading: true, items: [], error: null });
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    const params = {};
    if (filters.locality !== ALL) params.locality = filters.locality;
    if (filters.q.trim()) params.q = filters.q.trim();
    s6aApi
      .communities(params)
      .then((d) => setState({ loading: false, items: asList(d), error: null }))
      .catch((error) => setState({ loading: false, items: [], error }));
  }, [filters]);
  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  const create = async (e) => {
    e.preventDefault();
    if (form.name.trim().length < 3) return toast.error("Numele are minim 3 caractere.");
    if (!form.locality) return toast.error("Alege localitatea.");
    setBusy(true);
    try {
      const d = await s6aApi.createCommunity({ ...form, name: form.name.trim(), description: form.description.trim() });
      toast.success("Comunitate creată");
      const id = d?.community?.id;
      if (id) nav(`/radacini/comunitati/${id}`);
      else {
        setForm(null);
        load();
      }
    } catch (err) {
      toast.error(errMsg(err, "Nu am putut crea comunitatea"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5" data-testid="radacini-comunitati">
      <PageHeader
        title="Comunități"
        subtitle="Grupuri locale de cultivatori și vecini."
        actions={
          !form && (
            <DSButton icon={Plus} onClick={() => setForm({ name: "", locality: "", description: "", visibility: "open" })} data-testid="radacini-comunitate-noua">
              Comunitate nouă
            </DSButton>
          )
        }
      />

      {form && (
        <form onSubmit={create} className={`${CARD} p-5 space-y-4`} data-testid="radacini-comunitate-form">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Nume" htmlFor="com-nume">
              <Input id="com-nume" value={form.name} maxLength={80} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
            </Field>
            <Field label="Localitate" htmlFor="com-loc">
              <SelectField id="com-loc" value={form.locality} onValueChange={(v) => setForm((f) => ({ ...f, locality: v }))} options={localities} placeholder="Alege" testid="radacini-comunitate-loc" />
            </Field>
          </div>
          <Field label="Acces" htmlFor="com-vis">
            <SelectField id="com-vis" value={form.visibility} onValueChange={(v) => setForm((f) => ({ ...f, visibility: v }))} options={VIS} />
          </Field>
          <Field label="Descriere" htmlFor="com-desc">
            <Textarea id="com-desc" rows={3} maxLength={1000} value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
          </Field>
          <div className="flex justify-end gap-2">
            <DSButton type="button" variant="secondary" onClick={() => setForm(null)}>
              Renunță
            </DSButton>
            <DSButton type="submit" disabled={busy} data-testid="radacini-comunitate-salveaza">
              {busy ? "Se creează…" : "Creează"}
            </DSButton>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <SelectField value={filters.locality} onValueChange={(v) => setFilters((f) => ({ ...f, locality: v }))} options={[{ id: ALL, label: "Toate localitățile" }, ...localities]} testid="radacini-comunitati-filtru-loc" />
        <Input placeholder="Caută după nume" value={filters.q} onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))} data-testid="radacini-comunitati-cauta" />
      </div>

      {state.loading ? (
        <PageSkeleton />
      ) : state.error ? (
        <EmptyState icon={Users} title="Nu am putut încărca comunitățile" hint={errMsg(state.error)} />
      ) : state.items.length === 0 ? (
        <EmptyState icon={Users} title="Nicio comunitate găsită" testid="radacini-comunitati-gol" />
      ) : (
        <ul className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {state.items.map((c) => (
            <li key={c.id}>
              <Link to={`/radacini/comunitati/${c.id}`} className={`${CARD} p-4 block space-y-1 hover:bg-slate-50 dark:hover:bg-white/5`} data-testid={`radacini-comunitate-${c.id}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-bold text-slate-900 dark:text-white break-words">{c.name}</p>
                  <span className="text-[11px] font-bold rounded-full bg-slate-100 dark:bg-white/10 px-2.5 py-0.5 text-slate-600 dark:text-slate-300">
                    {c.visibility === "closed" ? "Închisă" : "Deschisă"}
                  </span>
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {c.locality} · {c.members_count ?? 0} membri
                  {(c.my_role || c.role) ? " · ești membru" : ""}
                </p>
                {c.description && <p className="text-sm text-slate-600 dark:text-slate-300 line-clamp-2 break-words">{c.description}</p>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
