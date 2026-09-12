/**
 * useEntitlements — hook central pentru gating UI.
 *
 * Sursă unică: /api/me/entitlements. Cache-uit per sesiune (o singură cerere).
 * Expune:
 *   - entitlements: { tier, tier_label, features, subscription, is_admin_bypass }
 *   - hasFeature(name): bool
 *   - loading, error
 *   - refresh(): forțează refetch (după activare abonament etc.)
 */
import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { API } from "../pages/DashShared";

let _cache = null; // simplu module-level cache pentru sesiune
let _cachePromise = null;

const fetchEntitlements = async (force = false) => {
  if (_cache && !force) return _cache;
  if (_cachePromise && !force) return _cachePromise;
  _cachePromise = axios
    .get(`${API}/me/entitlements`)
    .then((r) => {
      _cache = r.data;
      _cachePromise = null;
      return _cache;
    })
    .catch((e) => {
      _cachePromise = null;
      throw e;
    });
  return _cachePromise;
};

export const clearEntitlementCache = () => {
  _cache = null;
  _cachePromise = null;
};

export const useEntitlements = () => {
  const [entitlements, setEntitlements] = useState(_cache);
  const [loading, setLoading] = useState(!_cache);
  const [error, setError] = useState(null);

  const load = useCallback(async (force = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEntitlements(force);
      setEntitlements(data);
    } catch (e) {
      setError(e);
      setEntitlements(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!_cache) load(false);
  }, [load]);

  const hasFeature = useCallback(
    (name) => Boolean(entitlements?.features?.includes(name)),
    [entitlements]
  );

  const refresh = useCallback(() => load(true), [load]);

  return { entitlements, loading, error, hasFeature, refresh };
};

export default useEntitlements;
