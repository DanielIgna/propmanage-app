// Theme toggle — un singur click comută alb/negru. Plasat sus-dreapta pe toate paginile.
import React from "react";
import { Sun, Moon } from "lucide-react";
import { useTheme } from "../contexts/ThemeContext";

export const ThemeSwitcher = ({ compact = true }) => {
  const { isDark, toggleTheme } = useTheme();
  const Icon = isDark ? Sun : Moon;
  return (
    <button
      onClick={toggleTheme}
      data-testid="theme-switcher"
      title={isDark ? "Comută pe tema deschisă" : "Comută pe tema închisă"}
      aria-label="Schimbă tema"
      className="inline-flex items-center justify-center gap-1.5 w-9 h-9 rounded-full border transition-colors"
      style={{
        borderColor: "var(--pm-outline-strong)",
        color: "var(--pm-text-variant)",
        background: "var(--pm-surface)",
      }}
    >
      <Icon className="w-4 h-4" />
      {!compact && <span className="text-xs">{isDark ? "Light" : "Dark"}</span>}
    </button>
  );
};
