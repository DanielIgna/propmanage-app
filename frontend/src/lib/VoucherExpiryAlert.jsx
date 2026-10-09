// VoucherExpiryAlert — small badge in navbar/header that pulses red when
// the user has active vouchers expiring in < 7 days.
//
// Mount once in DashShared header (or directly in dashboards). Auto-fetches,
// auto-hides when no urgent vouchers. Self-contained.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Gift, X, Clock } from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

const URGENT_DAYS_THRESHOLD = 7;

export const VoucherExpiryAlert = () => {
  const [urgentVouchers, setUrgentVouchers] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await ax.get("/api/me/vouchers");
        if (cancelled) return;
        const now = Date.now();
        const cutoff = now + URGENT_DAYS_THRESHOLD * 86400000;
        const urgent = (data.items || []).filter(v => {
          if (v.status !== "active") return false;
          if (!v.expires_at) return false;
          const exp = new Date(v.expires_at).getTime();
          return exp > now && exp <= cutoff;
        }).map(v => {
          const exp = new Date(v.expires_at).getTime();
          const days_left = Math.max(0, Math.ceil((exp - now) / 86400000));
          return { ...v, days_left };
        }).sort((a, b) => a.days_left - b.days_left);
        setUrgentVouchers(urgent);
      } catch { /* silent */ }
    })();
    return () => { cancelled = true; };
  }, []);

  const copy = (code, e) => {
    e?.stopPropagation();
    navigator.clipboard.writeText(code);
  };

  if (urgentVouchers.length === 0) return null;
  const first = urgentVouchers[0];

  return (
    <div className="relative" data-testid="voucher-expiry-alert">
      <button
        onClick={() => setOpen(v => !v)}
        className="relative inline-flex items-center gap-1.5 px-2 py-1 rounded-lg bg-red-500/15 border border-red-500/40 text-red-200 hover:bg-red-500/25 text-[11px]"
        title={`${urgentVouchers.length} voucher(e) expiră curând`}
        data-testid="voucher-expiry-toggle"
      >
        <Gift className="w-3.5 h-3.5 animate-pulse" />
        <span className="hidden sm:inline">{first.days_left}z</span>
        {urgentVouchers.length > 1 && (
          <span className="text-[9px] bg-red-500/30 px-1 rounded">{urgentVouchers.length}</span>
        )}
        <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full animate-ping"></span>
        <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full"></span>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-2 z-50 w-80 bg-[#0e0e10] border border-red-500/30 rounded-xl shadow-2xl p-3" data-testid="voucher-expiry-dropdown">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5 text-red-300 text-xs font-semibold">
                <Clock className="w-3.5 h-3.5" /> Vouchere expiră curând
              </div>
              <button onClick={() => setOpen(false)} className="text-stone-500 hover:text-white" data-testid="voucher-expiry-close">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="space-y-1.5">
              {urgentVouchers.map(v => (
                <div
                  key={v.id}
                  onClick={(e) => copy(v.code, e)}
                  className="bg-black/30 hover:bg-black/50 border border-white/5 rounded-lg p-2 cursor-pointer transition-colors"
                  title="Click pentru a copia codul"
                  data-testid={`voucher-expiry-item-${v.id}`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-emerald-300 font-mono font-semibold text-sm">{v.percent}%</span>
                    <code className="text-amber-200 font-mono text-xs flex-1 truncate">{v.code}</code>
                    <span className={`text-[10px] font-semibold ${v.days_left <= 2 ? "text-red-300" : v.days_left <= 5 ? "text-amber-300" : "text-stone-400"}`}>
                      {v.days_left === 0 ? "expiră azi!" : `${v.days_left}z rămase`}
                    </span>
                  </div>
                  <div className="text-[10px] text-stone-500 mt-0.5 italic truncate">{v.reason}</div>
                </div>
              ))}
            </div>

            <div className="text-[10px] text-stone-500 italic mt-2 pt-2 border-t border-white/5 text-center">
              Click pentru a copia codul. Folosește la următoarea comandă.
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default VoucherExpiryAlert;
