import { useCallback, useEffect, useState } from "react";
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

// user: null = se încarcă · false = neautentificat · obiect = autentificat
export function useStaffMe() {
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
  return { staff: state.staff, loading: user === null || (!!user && state.loading) };
}

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
