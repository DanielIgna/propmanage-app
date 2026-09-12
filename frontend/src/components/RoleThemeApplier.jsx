// Theme Manager (XOS): la login aplică tema implicită a rolului din experience_profiles,
// fără să calce peste alegerea manuală a userului (pm_theme_source=user).
import { useEffect } from "react";
import axios from "axios";
import { useAuth } from "../auth";
import { useTheme } from "../contexts/ThemeContext";

const API = process.env.REACT_APP_BACKEND_URL;

export const RoleThemeApplier = () => {
  const { user } = useAuth();
  const { applyRoleTheme } = useTheme();
  useEffect(() => {
    if (!user?.role) return;
    axios.get(`${API}/api/experience/profile/${user.role}`)
      .then((r) => {
        const t = r.data?.default_theme;
        if (t && t !== "system") applyRoleTheme(t);
      })
      .catch(() => {});
  }, [user?.role]);
  return null;
};
