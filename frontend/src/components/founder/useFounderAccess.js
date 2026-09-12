import { useEffect, useState } from "react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;
let cached = null;
let pending = null;

export function useFounderAccess() {
  const [isFounder, setIsFounder] = useState(cached === true);
  useEffect(() => {
    if (cached !== null) { setIsFounder(cached); return; }
    if (!pending) {
      pending = axios.get(`${API}/api/founder/knowledge/access`, { withCredentials: true })
        .then(r => { cached = !!r.data.is_founder; return cached; })
        .catch(() => { cached = false; return false; });
    }
    let alive = true;
    pending.then(v => { if (alive) setIsFounder(v); });
    return () => { alive = false; };
  }, []);
  return isFounder;
}
