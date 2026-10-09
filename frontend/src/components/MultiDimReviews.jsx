// Sprint B — Multi-dim reviews display + pending review widget.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Star, EyeOff, Bell, ChevronRight, MessageCircle } from "lucide-react";
import { ReviewFormV2Modal } from "./ReviewFormV2";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;

const DIM_LABELS_C2S = {
  timeliness: "Termene", quality: "Calitate", offer_adherence: "Respectare ofertă", communication: "Comunicare",
  professionalism: "Profesionalism", cleanliness: "Curățenie", documentation: "Documentație", recommendation: "Recomandă",
};
const DIM_LABELS_S2C = {
  seriousness: "Seriozitate", responsiveness: "Răspuns", commitment: "Înțelegeri", punctuality: "Punctualitate", collaboration: "Colaborare",
};


export const MultiDimReviewsPanel = ({ userId, isSpecialist = true, limit = 5 }) => {
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!userId) return;
    const path = isSpecialist ? "specialist" : "client";
    axios.get(`${API}/api/reviews/${path}/${userId}?limit=${limit}`).then(r => setData(r.data)).catch(() => setData({ items: [], aggregate: {}, overall: 0 }));
  }, [userId, isSpecialist, limit]);

  if (!data) return null;
  const labels = isSpecialist ? DIM_LABELS_C2S : DIM_LABELS_S2C;
  const dims = Object.entries(data.aggregate || {});

  return (
    <div className="glass rounded-2xl p-5" data-testid={`reviews-panel-${userId}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-lg">Recenzii detaliate</h3>
        {data.overall > 0 && (
          <div className="flex items-center gap-1.5 text-[#d4ff3a]">
            <Star className="w-4 h-4 fill-[#d4ff3a]" />
            <span className="font-semibold tabular-nums">{data.overall.toFixed(2)}</span>
            <span className="text-xs text-stone-500">({data.total})</span>
          </div>
        )}
      </div>

      {dims.length > 0 && (
        <div className="space-y-1.5 mb-5" data-testid="reviews-aggregate">
          {dims.map(([key, val]) => {
            if (!val) return null;
            const pct = (val / 5) * 100;
            return (
              <div key={key} className="flex items-center gap-3" data-testid={`dim-${key}`}>
                <div className="text-xs text-stone-400 w-32 shrink-0">{labels[key] || key}</div>
                <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-[#d4ff3a] to-[#a8e028] rounded-full" style={{ width: `${pct}%` }} />
                </div>
                <div className="text-xs text-stone-300 w-10 text-right tabular-nums">{val.toFixed(1)}</div>
              </div>
            );
          })}
        </div>
      )}

      <div className="space-y-3" data-testid="reviews-list">
        {(data.items || []).map(r => (
          <div key={r.id} className="border-t border-white/5 pt-3" data-testid={`review-item-${r.id}`}>
            {r.hidden ? (
              <div className="flex items-center gap-2 text-xs text-stone-500 italic">
                <EyeOff className="w-3.5 h-3.5" />
                Recenzie ascunsă (double-blind window — revelare automată după {new Date(r.hidden_until).toLocaleDateString("ro-RO")})
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 mb-1">
                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                  <span className="text-sm font-semibold tabular-nums">{r.dimension_avg?.toFixed(1) || r.rating}</span>
                  <span className="text-[10px] text-stone-500">{new Date(r.created_at).toLocaleDateString("ro-RO")}</span>
                  {r.revealed_via === "mutual" && <span className="text-[9px] bg-emerald-500/10 text-emerald-300 px-1.5 py-0.5 rounded-full uppercase">mutual reveal</span>}
                </div>
                {r.comment && <p className="text-xs text-stone-300 leading-relaxed">{r.comment}</p>}
              </>
            )}
          </div>
        ))}
        {(data.items || []).length === 0 && (
          <div className="text-xs text-stone-500 italic text-center py-4">Nicio recenzie încă.</div>
        )}
      </div>
    </div>
  );
};


export const PendingReviewsWidget = () => {
  const [data, setData] = useState({ items: [], direction: null });
  const [active, setActive] = useState(null);

  const load = () => axios.get(`${API}/api/reviews/pending-for-me`).then(r => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  if (!data.items || data.items.length === 0) return null;

  return (
    <div className="glass rounded-2xl p-4 border border-[#d4ff3a]/30 bg-[#d4ff3a]/5" data-testid="pending-reviews-widget">
      <div className="flex items-center gap-2 mb-3">
        <MessageCircle className="w-4 h-4 text-[#d4ff3a]" />
        <h4 className="font-semibold text-sm text-[#d4ff3a]">Recenzii de trimis</h4>
        <span className="ml-auto text-xs bg-[#d4ff3a]/15 text-[#d4ff3a] px-2 py-0.5 rounded-full">{data.items.length}</span>
      </div>
      <div className="space-y-1.5">
        {data.items.slice(0, 3).map(r => (
          <button key={r.request_id} onClick={() => setActive(r.request_id)}
            className="w-full flex items-center justify-between gap-2 text-left px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 transition group"
            data-testid={`pending-review-${r.request_id}`}>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium truncate">{r.title || "Cerere finalizată"}</div>
              <div className="text-[10px] text-stone-500">{new Date(r.completed_at).toLocaleDateString("ro-RO")}</div>
            </div>
            <ChevronRight className="w-3.5 h-3.5 text-stone-500 group-hover:text-[#d4ff3a]" />
          </button>
        ))}
        {data.items.length > 3 && <div className="text-[10px] text-stone-500 text-center">+{data.items.length - 3} alte cereri</div>}
      </div>
      {active && (
        <ReviewFormV2Modal requestId={active} direction={data.direction}
          onClose={() => setActive(null)}
          onSubmit={() => { setActive(null); load(); }} />
      )}
    </div>
  );
};

export default PendingReviewsWidget;
