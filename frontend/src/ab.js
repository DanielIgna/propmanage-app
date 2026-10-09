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
  const [variant] = useState(() => getVariant(experiment));
  const fired = useRef(false);

  useEffect(() => {
    if (fired.current) return;
    fired.current = true;
    axios.post(`${API}/ab/track`, {
      experiment,
      variant,
      event: "impression",
      session_id: getSessionId(),
    }).catch(() => {});
  }, [experiment, variant]);

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
