// Sursa unică de adevăr pentru ecosistem — conținutul canonic din /interior-design/content.
// Cache la nivel de modul: o singură cerere per sesiune, indiferent câte pagini îl folosesc.
import { useEffect, useState } from "react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;
let _cache = null;
let _pending = null;

export function useEcosystemContent() {
  const [content, setContent] = useState(_cache);
  useEffect(() => {
    if (_cache) return;
    if (!_pending) {
      _pending = axios.get(`${API}/api/interior-design/content`)
        .then((r) => { _cache = r.data; return _cache; })
        .catch(() => null);
    }
    let alive = true;
    _pending.then((c) => { if (alive && c) setContent(c); });
    return () => { alive = false; };
  }, []);
  return content;
}
