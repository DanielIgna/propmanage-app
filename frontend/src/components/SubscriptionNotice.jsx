/**
 * SubscriptionNotice — banner subtil care apare când user-ul are un abonament
 * anulat (dar în perioada de grație) sau expirat.
 *
 * Sursă: /api/me/entitlements → câmpul `notice` (populat de backend).
 * Reutilizează hook-ul useEntitlements existent (Task 1). NU creează un al doilea
 * sistem de subscription-status UI.
 */
import React from "react";
import { AlertCircle, ArrowRight, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useEntitlements } from "../hooks/useEntitlements";

const NOTICE_STYLES = {
  subscription_expired: {
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-900",
    iconColor: "text-amber-600",
  },
  subscription_cancelled: {
    bg: "bg-sky-50",
    border: "border-sky-200",
    text: "text-sky-900",
    iconColor: "text-sky-600",
  },
};

export const SubscriptionNotice = ({ compact = false, dismissible = true, testid }) => {
  const { entitlements, loading } = useEntitlements();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = React.useState(() => {
    try { return sessionStorage.getItem("pm_notice_dismissed") === "1"; } catch { return false; }
  });

  if (loading || dismissed || !entitlements?.notice) return null;

  const notice = entitlements.notice;
  const style = NOTICE_STYLES[notice.kind] || NOTICE_STYLES.subscription_expired;

  const goCta = () => {
    try { navigate(notice.cta_href || "/pricing"); }
    catch { window.location.href = notice.cta_href || "/pricing"; }
  };

  const dismiss = () => {
    setDismissed(true);
    try { sessionStorage.setItem("pm_notice_dismissed", "1"); } catch { /* silent */ }
  };

  return (
    <div data-testid={testid || `subscription-notice-${notice.kind}`}
      className={`rounded-2xl border ${style.border} ${style.bg} ${style.text} ${compact ? "px-3 py-2" : "px-4 py-3"} flex items-start gap-2.5`}>
      <AlertCircle className={`${style.iconColor} w-4 h-4 mt-0.5 shrink-0`} />
      <div className="flex-1 min-w-0">
        <div className={`${compact ? "text-[11px]" : "text-[12px]"} font-bold leading-snug`}>
          {notice.message}
        </div>
        <button onClick={goCta} data-testid="subscription-notice-cta"
          className="mt-1 inline-flex items-center gap-1 text-[11px] font-black underline">
          {notice.cta_label || "Reactivează"} <ArrowRight className="w-3 h-3" />
        </button>
      </div>
      {dismissible && (
        <button onClick={dismiss} data-testid="subscription-notice-dismiss"
          className={`${style.iconColor} hover:opacity-70 shrink-0`}>
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};

export default SubscriptionNotice;
