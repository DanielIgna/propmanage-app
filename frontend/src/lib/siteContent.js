import { useEffect, useState } from "react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;

let _cache = null;
let _promise = null;

export const fetchSiteContent = () => {
  if (_cache) return Promise.resolve(_cache);
  if (!_promise) {
    _promise = axios.get(`${API}/api/public/site-content`)
      .then((r) => { _cache = r.data; return _cache; })
      .catch(() => ({ banner: {}, hero: {}, entries: [] }));
  }
  return _promise;
};

export const useSiteContent = () => {
  const [content, setContent] = useState(_cache);
  useEffect(() => { fetchSiteContent().then(setContent).catch(() => {}); }, []);
  return content;
};
