// ST-001 · StorageUsageCard — widget de stocare pentru utilizator (folosit/disponibil/%,
// avertizări la 80%/95%, CTA upgrade House Health, bucket Digital Twin separat).
import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { HardDrive, AlertTriangle, Box } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const barColor = (pct) => (pct >= 95 ? "#ef4444" : pct >= 80 ? "#f59e0b" : "#34C759");

export const StorageUsageCard = () => {
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  const load = useCallback(() => {
    axios.get(`${API}/api/storage/usage`).then((r) => setData(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    window.addEventListener("propmanage:doc-uploaded", load);
    return () => window.removeEventListener("propmanage:doc-uploaded", load);
  }, [load]);

  if (!data) return null;
  const p = data.personal;
  const dt = data.digital_twin;

  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-3" data-testid="storage-usage-card">
      <div className="flex items-center gap-2">
        <HardDrive className="w-4 h-4 text-slate-400" />
        <span className="flex-1 text-xs font-black text-slate-700">Spațiu de stocare</span>
        <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-500" data-testid="storage-tier-label">
          {p.tier_label}
        </span>
      </div>

      <div className="mt-2 h-2 rounded-full bg-slate-100 overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" data-testid="storage-usage-bar"
          style={{ width: `${Math.min(100, p.pct)}%`, background: barColor(p.pct) }} />
      </div>
      <div className="mt-1.5 text-[11px] text-slate-500" data-testid="storage-usage-text">
        <b className="text-slate-700">{p.used_human}</b> din {p.quota_human} · {p.pct}% · {p.files_count} fișiere
      </div>

      {p.warning && (
        <div
          className={`mt-2 flex items-start gap-2 p-2.5 rounded-xl text-[11px] font-bold ${p.warning === "critical" ? "bg-red-50 text-red-700 border border-red-100" : "bg-amber-50 text-amber-700 border border-amber-100"}`}
          data-testid={p.warning === "critical" ? "storage-warning-critical" : "storage-warning"}>
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>
            {p.warning === "critical"
              ? "Spațiul este aproape plin — în curând nu vei mai putea încărca documente noi."
              : `Ai depășit ${data.thresholds?.[0] || 80}% din spațiul disponibil.`}
          </span>
        </div>
      )}

      {p.warning && data.upgrade_available && (
        <button onClick={() => navigate("/house-health/upgrade")} data-testid="storage-upgrade-cta"
          className="mt-2 w-full py-2.5 rounded-full text-xs font-black text-black active:scale-[0.98] transition-transform"
          style={{ background: "#d4ff3a" }}>
          Treci la House Health · 5 GB stocare
        </button>
      )}

      {dt && (
        <div className="mt-3 pt-2.5 border-t border-slate-100" data-testid="storage-dt-section">
          <div className="flex items-center gap-2">
            <Box className="w-3.5 h-3.5 text-slate-400" />
            <span className="flex-1 text-[11px] font-bold text-slate-600">Digital Twin</span>
            <span className="text-[10px] text-slate-400">{dt.used_human} din {dt.quota_human}</span>
          </div>
          <div className="mt-1.5 h-1.5 rounded-full bg-slate-100 overflow-hidden">
            <div className="h-full rounded-full" data-testid="storage-dt-bar"
              style={{ width: `${Math.min(100, dt.pct)}%`, background: barColor(dt.pct) }} />
          </div>
          <div className="mt-1 text-[10px] text-slate-400">Cotă separată — nu consumă spațiul tău personal.</div>
        </div>
      )}
    </div>
  );
};

export default StorageUsageCard;
