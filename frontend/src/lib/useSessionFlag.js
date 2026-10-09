import { useEffect, useState } from "react";

// A "1"/unset flag in sessionStorage, read after mount so server and first client render match.
export function useSessionFlag(key) {
  const [on, setOn] = useState(false);
  useEffect(() => {
    try { setOn(sessionStorage.getItem(key) === "1"); } catch { /* storage blocked */ }
  }, [key]);
  const set = () => {
    try { sessionStorage.setItem(key, "1"); } catch { /* storage blocked */ }
    setOn(true);
  };
  return [on, set];
}
