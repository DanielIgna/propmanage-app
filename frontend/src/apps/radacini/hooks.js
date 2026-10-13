import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useAuth } from "../../auth";
import { radaciniApi } from "./api";

// Meta sunt enumerări statice: o singură cerere per sesiune de browser.
let metaCache = null;
let metaPromise = null;
const loadMeta = () => {
  if (metaCache) return Promise.resolve(metaCache);
  if (!metaPromise) {
    metaPromise = radaciniApi
      .meta()
      .then((m) => {
        metaCache = m;
        return m;
      })
      .catch((e) => {
        metaPromise = null;
        throw e;
      });
  }
  return metaPromise;
};

export function useMeta() {
  const [state, setState] = useState({ meta: metaCache, loading: !metaCache, error: null });
  useEffect(() => {
    if (metaCache) return undefined;
    let alive = true;
    loadMeta()
      .then((meta) => alive && setState({ meta, loading: false, error: null }))
      .catch((error) => alive && setState({ meta: null, loading: false, error }));
    return () => {
      alive = false;
    };
  }, []);
  return state;
}

const NO_STAFF = { is_staff: false, role: null, areas: [] };

// Cererea /staff/me se face o singură dată, în RadaciniLayout (useStaffLoader); restul paginilor citesc contextul.
// user: null = se încarcă · false = neautentificat · obiect = autentificat
export function useStaffLoader() {
  const { user } = useAuth();
  const [state, setState] = useState({ loading: true, staff: NO_STAFF });
  useEffect(() => {
    if (!user) return undefined;
    let alive = true;
    radaciniApi
      .staffMe()
      .then((staff) => alive && setState({ loading: false, staff: staff || NO_STAFF }))
      .catch(() => alive && setState({ loading: false, staff: NO_STAFF }));
    return () => {
      alive = false;
    };
  }, [user]);
  const loading = user === null || (!!user && state.loading);
  return useMemo(() => ({ staff: state.staff, loading }), [state.staff, loading]);
}

export const StaffContext = createContext({ staff: NO_STAFF, loading: false });

// Informațiile despre personal vin din contextul oferit de RadaciniLayout (fără cerere proprie).
export const useStaffMe = () => useContext(StaffContext);

export function useMember() {
  const { user } = useAuth();
  const [state, setState] = useState({ loading: true, exists: false, member: null, error: null });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!user) return undefined;
    let alive = true;
    radaciniApi
      .memberMe()
      .then((d) => alive && setState({ loading: false, exists: !!d?.exists, member: d?.member || null, error: null }))
      .catch((error) => alive && setState({ loading: false, exists: false, member: null, error }));
    return () => {
      alive = false;
    };
  }, [user, tick]);
  const refresh = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, loading: user === null || (!!user && state.loading), refresh };
}
