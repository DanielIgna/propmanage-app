// Theme context — 2 teme: dark (default) și light, comutabile de utilizator.
// Sincronizează: data-theme (tokens pm-* + override-uri landing), data-admin-theme (consolă admin),
// clasa Tailwind `dark` (variantele dark: din Design System).
import React, { createContext, useContext, useEffect, useState } from "react";

const ThemeContext = createContext(null);

const normalize = (v) => (v === "light" ? "light" : "dark");

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    try {
      const stored = localStorage.getItem("propmanage_theme");
      if (stored === "light" || stored === "warm-linen") return "light";
      return "dark";
    } catch (_e) { return "dark"; }
  });

  useEffect(() => {
    const t = normalize(theme);
    const root = document.documentElement;
    if (t === "light") root.setAttribute("data-theme", "light");
    else root.removeAttribute("data-theme");
    root.setAttribute("data-admin-theme", t);
    root.classList.toggle("dark", t === "dark");
    try {
      localStorage.setItem("propmanage_theme", t);
      localStorage.setItem("pm_admin_theme", t);
    } catch (_e) { /* ignore */ }
  }, [theme]);

  const toggleTheme = () => {
    try { localStorage.setItem("pm_theme_source", "user"); } catch (_e) { /* ignore */ }
    setTheme((t) => (t === "light" ? "dark" : "light"));
  };

  // Theme Manager (XOS): aplică tema implicită a rolului DOAR dacă userul nu a ales manual
  const applyRoleTheme = (t) => {
    try { if (localStorage.getItem("pm_theme_source") === "user") return; } catch (_e) { /* ignore */ }
    if (t === "light" || t === "dark") setTheme(t);
  };

  return (
    <ThemeContext.Provider value={{ theme: normalize(theme), setTheme, toggleTheme, applyRoleTheme, isDark: normalize(theme) === "dark" }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be inside ThemeProvider");
  return ctx;
};
