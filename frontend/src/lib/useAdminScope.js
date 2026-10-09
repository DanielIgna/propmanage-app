// Hook + helpers for admin-scope aware UI (Milestone 2)
// Supports "Preview as" mode for super-admins via localStorage override.
import { useEffect, useState } from "react";
import axios from "axios";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;
const PREVIEW_KEY = "pm_admin_preview_scope";

// Visibility map: which nav items each scope can see (besides "general" who sees all).
// Keep in sync with backend middleware_scope.SCOPE_RULES so UI matches reality.
export const SCOPE_VISIBILITY = {
  general: "ALL",
  testing: new Set([
    "overview", "ai", "activity", "demo", "leads",
    "qa_copilot", "qa_playbook", "audit", "docs", "docs_train",
    "todo_board", "approvals",
  ]),
  frontend: new Set([
    "overview", "activity", "cms", "emails", "zones",
    "feature_configurator", "audit", "docs", "docs_train",
    "todo_board", "approvals",
  ]),
  backend: new Set([
    "overview", "activity", "settings", "settings_control", "architecture_board",
    "audit", "docs", "docs_train", "todo_board", "approvals",
    "bug_memory",
  ]),
  security: new Set([
    "overview", "activity", "ai_security", "gdpr", "impersonation", "kyc",
    "audit", "docs", "docs_train", "todo_board", "approvals",
    "trust", "ai_governance",
  ]),
  ai: new Set([
    "overview", "ai", "activity", "concierge", "ai_control",
    "ai_dev_team", "ai_docs", "ai_governance", "ai_pm",
    "audit", "docs", "docs_train", "todo_board", "approvals",
  ]),
  ops: new Set([
    "overview", "activity", "autonomy", "exec_briefing",
    "audit", "docs", "docs_train", "todo_board", "approvals",
    "verification", "disputes", "finance",
  ]),
};

export const ALL_SCOPES = ["general", "testing", "frontend", "backend", "security", "ai", "ops"];

// Cross-tab event for preview mode changes
const PREVIEW_EVENT = "pm:preview-scope-changed";

export function setPreviewScope(scope) {
  if (scope && scope !== "general") {
    localStorage.setItem(PREVIEW_KEY, scope);
  } else {
    localStorage.removeItem(PREVIEW_KEY);
  }
  window.dispatchEvent(new CustomEvent(PREVIEW_EVENT, { detail: { scope } }));
}

export function getPreviewScope() {
  return localStorage.getItem(PREVIEW_KEY) || null;
}

export function useAdminScope() {
  const [scope, setScope] = useState(null);
  const [preview, setPreview] = useState(() => getPreviewScope());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    axios
      .get(`${API}/admin/sub-admins/me/scope`)
      .then((r) => {
        if (!cancelled) setScope(r.data);
      })
      .catch(() => {
        if (!cancelled) setScope(null);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, []);

  // Sync across tabs / preview toggle
  useEffect(() => {
    const onChange = () => setPreview(getPreviewScope());
    window.addEventListener(PREVIEW_EVENT, onChange);
    window.addEventListener("storage", onChange);
    return () => {
      window.removeEventListener(PREVIEW_EVENT, onChange);
      window.removeEventListener("storage", onChange);
    };
  }, []);

  // If super-admin AND a preview scope is active, return an overridden scope
  // object so the rest of the UI behaves like that scope. Original `_real` kept
  // so the topbar can show "previewing as".
  const isSuper = (scope?.admin_scope || "").toLowerCase() === "general";
  if (scope && isSuper && preview && preview !== "general") {
    return {
      scope: {
        ...scope,
        admin_scope: preview,
        admin_seniority: "senior",  // assume senior for preview ergonomics
        is_super_admin: false,
        _preview_active: true,
        _real_scope: scope.admin_scope,
      },
      loading,
    };
  }
  return { scope, loading };
}

export function canSeeNavItem(scopeData, itemId) {
  if (!scopeData) return true; // unknown → show (fail-open until /me/scope loads)
  const s = (scopeData.admin_scope || "general").toLowerCase();
  if (s === "general") return true;
  const allowed = SCOPE_VISIBILITY[s];
  if (!allowed || allowed === "ALL") return true;
  return allowed.has(itemId);
}

export function filterNavSections(sections, scopeData) {
  if (!scopeData) return sections;
  const s = (scopeData.admin_scope || "general").toLowerCase();
  if (s === "general") return sections;
  return sections
    .map((sec) => ({
      ...sec,
      items: sec.items.filter((it) => canSeeNavItem(scopeData, it.id)),
    }))
    .filter((sec) => sec.items.length > 0);
}
