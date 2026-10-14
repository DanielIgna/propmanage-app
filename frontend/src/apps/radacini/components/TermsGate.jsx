import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api } from "../../../lib/api";
import { DSButton } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { errMsg } from "../api";
import { s8Api, isTermsRequired, setTermsAsker, askTerms } from "../api_s8";

const TermsContext = createContext({ ensureTerms: () => Promise.resolve(true) });
// ensureTerms() → true dacă termenii sunt acceptați (deschide dialogul dacă nu).
export const useTerms = () => useContext(TermsContext);

export function TermsGateProvider({ children }) {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState({ loading: false, docs: [], required: [] });
  const [checked, setChecked] = useState(false);
  const [saving, setSaving] = useState(false);
  const pending = useRef(null); // {promise, resolve}

  const finish = useCallback((ok) => {
    pending.current?.resolve(ok);
    pending.current = null;
    setOpen(false);
    setChecked(false);
  }, []);

  const ask = useCallback(() => {
    if (pending.current) return pending.current.promise;
    let resolve;
    const promise = new Promise((r) => {
      resolve = r;
    });
    pending.current = { promise, resolve };
    setOpen(true);
    setState({ loading: true, docs: [], required: [] });
    Promise.all([s8Api.legalDocuments().catch(() => ({ items: [] })), s8Api.legalMe().catch(() => ({ required: [] }))]).then(
      ([d, me]) => {
        if (me?.ok && !me?.required?.length) return finish(true);
        setState({ loading: false, docs: d?.items || [], required: me?.required || [] });
      }
    );
    return promise;
  }, [finish]);

  useEffect(() => {
    setTermsAsker(ask);
    const id = api.interceptors.response.use(
      (r) => r,
      async (error) => {
        const cfg = error?.config;
        const url = cfg?.url || "";
        if (cfg && !cfg._termsRetried && url.startsWith("/radacini/") && isTermsRequired(error)) {
          if (await ask()) {
            cfg._termsRetried = true;
            return api.request(cfg);
          }
        }
        return Promise.reject(error);
      }
    );
    return () => {
      api.interceptors.response.eject(id);
      setTermsAsker(null);
    };
  }, [ask]);

  const accept = async () => {
    setSaving(true);
    try {
      for (const r of state.required) await s8Api.acceptLegal(r.type, r.version);
      toast.success("Termenii au fost acceptați");
      finish(true);
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut salva acceptarea"));
    } finally {
      setSaving(false);
    }
  };

  const ctx = useMemo(() => ({ ensureTerms: ask }), [ask]);
  const summaries = state.required.map((r) => ({ ...r, doc: state.docs.find((d) => d.type === r.type && d.version === r.version) || state.docs.find((d) => d.type === r.type) }));

  return (
    <TermsContext.Provider value={ctx}>
      {children}
      <Dialog open={open} onOpenChange={(o) => !o && finish(false)}>
        <DialogContent data-testid="radacini-terms-dialog">
          <DialogHeader>
            <DialogTitle>Acceptă termenii Rădăcini</DialogTitle>
            <DialogDescription>Ca să continui, trebuie să accepți termenii curenți. Versiune pilot — în revizuire juridică.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 max-h-[50vh] overflow-y-auto text-sm text-slate-700 dark:text-slate-300">
            {state.loading && <p>Se încarcă…</p>}
            {summaries.map((s) => (
              <div key={s.type}>
                <p className="font-semibold">{s.doc?.title || s.type} <span className="text-xs font-normal text-slate-500">({s.version})</span></p>
                {s.doc?.summary && <p>{s.doc.summary}</p>}
              </div>
            ))}
            <Link to="/radacini/termeni" target="_blank" className="text-emerald-700 underline" data-testid="radacini-terms-link">
              Citește textul complet
            </Link>
          </div>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-1 h-5 w-5" checked={checked} onChange={(e) => setChecked(e.target.checked)} data-testid="radacini-terms-check" />
            <span>Am citit și accept termenii și politica de confidențialitate Rădăcini.</span>
          </label>
          <DialogFooter>
            <DSButton variant="secondary" onClick={() => finish(false)}>Mai târziu</DSButton>
            <DSButton disabled={!checked || saving || state.loading || !state.required.length} onClick={accept} data-testid="radacini-terms-accept">
              {saving ? "Se salvează…" : "Accept"}
            </DSButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </TermsContext.Provider>
  );
}

export { askTerms };
