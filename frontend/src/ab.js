// PropManage A/B testing hook — stable per-browser variant assignment + tracking.
import { useEffect, useRef, useState } from "react";
import axios from "axios";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const getSessionId = () => {
  let sid = localStorage.getItem("pm_ab_session");
  if (!sid) {
    sid = `s_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem("pm_ab_session", sid);
  }
  return sid;
};

const getVariant = (experiment) => {
  const key = `pm_ab_${experiment}`;
  let v = localStorage.getItem(key);
  if (v !== "a" && v !== "b") {
    v = Math.random() < 0.5 ? "a" : "b";
    localStorage.setItem(key, v);
  }
  return v;
};

export const useABTest = (experiment) => {
  // Variant "a" until mounted (server render + hydration), then the stable per-browser variant.
  const [variant, setVariant] = useState("a");
  const fired = useRef(false);

  useEffect(() => {
    if (fired.current) return;
    fired.current = true;
    let v = "a";
    try { v = getVariant(experiment); } catch { /* storage blocked */ }
    setVariant(v);
    axios.post(`${API}/ab/track`, {
      experiment,
      variant: v,
      event: "impression",
      session_id: getSessionId(),
    }).catch(() => {});
  }, [experiment]);

  const trackClick = () => {
    axios.post(`${API}/ab/track`, {
      experiment,
      variant,
      event: "click",
      session_id: getSessionId(),
    }).catch(() => {});
  };

  return { variant, trackClick };
};
