// DesignTokensProvider — fetches the active design tokens from the backend and
// injects them as CSS variables on <html>. Any component that consumes --pm-*
// vars will instantly reflect changes. Refetches when a "pm:tokens-updated"
// event fires (dispatched by DesignStudioPage on save/preset apply).
import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;
const TokensContext = createContext(null);
export const TOKENS_UPDATED_EVENT = "pm:tokens-updated";

const applyToRoot = (tokens) => {
  if (!tokens || typeof tokens !== "object") return;
  const root = document.documentElement;
  const set = (k, v) => v && root.style.setProperty(k, v);

  const c = tokens.colors || {};
  set("--pm-primary", c.primary);
  set("--pm-primary-dim", c.primary_dim);
  set("--pm-on-primary", c.on_primary);
  set("--pm-accent-ink", c.accent_ink);
  set("--pm-bg", c.bg_dark || c.bg);
  set("--pm-surface", c.surface_dark || c.surface);
  set("--pm-surface-high", c.surface_high_dark || c.surface_high);
  set("--pm-text", c.text_dark || c.text);
  set("--pm-text-variant", c.text_muted_dark || c.text_muted);
  set("--pm-error", c.danger);
  set("--pm-warning", c.warning);
  set("--pm-success", c.success);
  set("--pm-info", c.info);
  // duplicate as brand tokens for convenience
  set("--brand-primary", c.primary);
  set("--brand-on-primary", c.on_primary);

  const r = tokens.radii || {};
  set("--pm-radius-sm", r.sm);
  set("--pm-radius-md", r.md);
  set("--pm-radius-lg", r.lg);
  set("--pm-radius-xl", r.xl);
  set("--pm-radius-pill", r.pill);

  const s = tokens.shadows || {};
  set("--pm-shadow-sm", s.sm);
  set("--pm-shadow-md", s.md);
  set("--pm-shadow-lg", s.lg);
  set("--pm-glow-primary", s.glow_primary);

  const t = tokens.typography || {};
  if (t.sans) root.style.setProperty("--pm-font-sans", t.sans);
  if (t.serif) root.style.setProperty("--pm-font-serif", t.serif);
  if (t.mono) root.style.setProperty("--pm-font-mono", t.mono);
};

export const DesignTokensProvider = ({ children }) => {
  const [tokens, setTokens] = useState(null);
  const [presetId, setPresetId] = useState(null);

  const load = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/api/admin/design-studio/tokens`, { withCredentials: true });
      if (r.data?.tokens) {
        setTokens(r.data.tokens);
        setPresetId(r.data.preset_id);
        applyToRoot(r.data.tokens);
      }
    } catch (_e) {
      // silent — page will render with default tokens
    }
  }, []);

  useEffect(() => {
    load();
    const handler = () => load();
    window.addEventListener(TOKENS_UPDATED_EVENT, handler);
    return () => window.removeEventListener(TOKENS_UPDATED_EVENT, handler);
  }, [load]);

  return (
    <TokensContext.Provider value={{ tokens, presetId, reload: load }}>
      {children}
    </TokensContext.Provider>
  );
};

export const useDesignTokens = () => {
  const ctx = useContext(TokensContext);
  return ctx || { tokens: null, presetId: null, reload: () => {} };
};

export const dispatchTokensUpdated = () => {
  window.dispatchEvent(new CustomEvent(TOKENS_UPDATED_EVENT));
};

export { applyToRoot };
