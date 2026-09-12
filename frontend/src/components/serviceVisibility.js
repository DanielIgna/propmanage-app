// Vizibilitatea serviciilor (REGULA PLATFORMEI): un serviciu nu e accesibil public
// până când adminul îl marchează ACTIV + VIZIBIL în Service Manager (site_menu).
import { useEffect, useState } from "react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;
let _cache = null;
let _pending = null;

export function useServiceVisibility() {
  const [services, setServices] = useState(_cache);
  useEffect(() => {
    if (_cache) return;
    if (!_pending) {
      _pending = axios.get(`${API}/api/public/service-visibility`)
        .then((r) => { _cache = r.data?.services || {}; return _cache; })
        .catch(() => ({}));
    }
    let alive = true;
    _pending.then((s) => { if (alive) setServices(s); });
    return () => { alive = false; };
  }, []);
  return services; // null = loading
}

export const isServiceEnabled = (services, id) =>
  !!(services && services[id] && services[id].active && services[id].visible_site);
