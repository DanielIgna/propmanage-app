// BUGFIX-001 — Floating Manager: dashboards cu dock mobil setează --pm-dock-h,
// iar elementele plutitoare (.pm-float-*) se stivuiesc deasupra fără suprapuneri.
import { useEffect } from "react";

export const useMobileDock = (height = 64) => {
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const apply = () => document.documentElement.style.setProperty("--pm-dock-h", mq.matches ? "0px" : `${height}px`);
    apply();
    mq.addEventListener("change", apply);
    return () => {
      mq.removeEventListener("change", apply);
      document.documentElement.style.setProperty("--pm-dock-h", "0px");
    };
  }, [height]);
};
