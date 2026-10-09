// PropManage - Interior Design module (concept ordering + phase quotes)
import React, { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import {
  Palette, Lock, Sparkles, Coins, X, ArrowRight, Square, Bed, ChefHat, Bath,
  Layers, Check, AlertTriangle, Wallet, Clock, CheckCircle2,
} from "lucide-react";
import { formatApiError } from "../auth";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const ROOM_ICONS = {
  living: Square,
  bedroom: Bed,
  kitchen: ChefHat,
  bathroom: Bath,
  hallway: ArrowRight,
  office: Square,
  balcony: Square,
  storage: Layers,
  other: Square,
};

const STYLES = [
  { id: "modern", label: "Modern", emoji: "🏙" },
  { id: "scandinavian", label: "Scandinavian", emoji: "🌲" },
  { id: "minimalist", label: "Minimalist", emoji: "⚪" },
  { id: "industrial", label: "Industrial", emoji: "⚙" },
  { id: "boho", label: "Boho", emoji: "🌿" },
  { id: "classic", label: "Clasic", emoji: "🏛" },
  { id: "rustic", label: "Rustic", emoji: "🪵" },
  { id: "japandi", label: "Japandi", emoji: "🎋" },
];

// ============= CARD (entry point on client dashboard) =============
export const InteriorDesignCard = ({ user, onOpen }) => {
  const [elig, setElig] = useState(null);

  useEffect(() => {
    axios.get(`${API}/design/eligibility`).then(r => setElig(r.data)).catch(() => setElig({ eligible: false }));
  }, [user]);

  if (!elig) return null;

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      className="relative glass-strong rounded-3xl p-6 overflow-hidden" data-testid="design-card">
      <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-purple-500 opacity-15 blur-3xl" />
      <div className="relative">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 bg-purple-500/15 text-purple-300 border border-purple-500/30 rounded-full">PREMIUM</span>
          <span className="text-[10px] uppercase tracking-wider text-stone-500">Disponibil cu Digital Twin</span>
        </div>
        <div className="flex items-start gap-3 mb-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-500/30 to-pink-500/20 border border-purple-500/30 flex items-center justify-center shrink-0">
            <Palette className="w-5 h-5 text-purple-300" />
          </div>
          <div>
            <h3 className="font-serif text-xl">Design Interior</h3>
            <p className="text-xs text-stone-400 mt-0.5">Concept profesional · 2200 RON/cameră · folosește tokeni pentru reducere</p>
          </div>
        </div>

        {elig.eligible ? (
          <>
            <div className="grid grid-cols-3 gap-2 mb-4 text-center">
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl py-2">
                <div className="text-[10px] uppercase tracking-wider text-emerald-300/80">Twin</div>
                <div className="text-sm font-medium text-emerald-300">{elig.properties.length} {elig.properties.length === 1 ? "prop." : "prop."}</div>
              </div>
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl py-2">
                <div className="text-[10px] uppercase tracking-wider text-amber-300/80">Tokeni</div>
                <div className="text-sm font-medium text-amber-300">{elig.available_tokens}</div>
              </div>
              <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl py-2">
                <div className="text-[10px] uppercase tracking-wider text-purple-300/80">Discount max</div>
                <div className="text-sm font-medium text-purple-300">{elig.max_token_discount_pct}%</div>
              </div>
            </div>
            <button onClick={onOpen} className="w-full btn-accent py-3 rounded-xl text-sm font-medium flex items-center justify-center gap-2" data-testid="design-open">
              <Sparkles className="w-4 h-4" />Solicită concept de design
            </button>
          </>
        ) : (
          <>
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl px-3 py-3 text-xs text-amber-300 mb-3 flex items-start gap-2">
              <Lock className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              <div>
                <div className="font-medium mb-1">Digital Twin necesar</div>
                <div className="opacity-90">Pentru a accesa serviciul de Design Interior trebuie să ai cel puțin o proprietate cu Digital Twin aprobat. Solicită activarea twin-ului din pagina proprietății.</div>
              </div>
            </div>
            <button disabled className="w-full bg-white/5 py-3 rounded-xl text-sm font-medium text-stone-500 flex items-center justify-center gap-2 cursor-not-allowed" data-testid="design-locked">
              <Lock className="w-4 h-4" />Necesită Twin activat
            </button>
          </>
        )}
      </div>
    </motion.div>
  );
};

// ============= ORDERING MODAL =============
export const InteriorDesignModal = ({ onClose, onCreated }) => {
  const [elig, setElig] = useState(null);
  const [propIdx, setPropIdx] = useState(0);
  const [selectedRooms, setSelectedRooms] = useState([]);
  const [tokensToUse, setTokensToUse] = useState(0);
  const [style, setStyle] = useState("modern");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    axios.get(`${API}/design/eligibility`).then(r => {
      setElig(r.data);
      // Auto-select first room
      const firstRoom = r.data?.properties?.[0]?.rooms?.[0];
      if (firstRoom) setSelectedRooms([firstRoom.id]);
    }).catch(() => {});
  }, []);

  const prop = elig?.properties?.[propIdx];
  const pricePerRoom = elig?.concept_price_per_room || 2200;
  const fullPrice = pricePerRoom * selectedRooms.length;
  const maxTokens = Math.min(elig?.available_tokens || 0, Math.floor(fullPrice * (elig?.max_token_discount_pct || 50) / 100));
  const effectiveTokens = Math.min(tokensToUse, maxTokens);
  const finalPrice = Math.max(0, fullPrice - effectiveTokens);

  const toggleRoom = (rid) => {
    setSelectedRooms(selectedRooms.includes(rid)
      ? selectedRooms.filter(x => x !== rid)
      : [...selectedRooms, rid]);
  };

  // Clamp tokens when room selection or property changes
  useEffect(() => {
    if (tokensToUse > maxTokens) setTokensToUse(maxTokens);
  }, [maxTokens]); // eslint-disable-line

  const submit = async () => {
    if (selectedRooms.length === 0) return alert("Selectează cel puțin o cameră");
    if (!prop) return;
    setSubmitting(true);
    try {
      const { data } = await axios.post(`${API}/design/concept-request`, {
        property_id: prop.id,
        room_ids: selectedRooms,
        tokens_to_use: effectiveTokens,
        style_preference: style,
        notes: notes || null,
      });
      onCreated?.(data);
      alert(`Cerere creată! Preț final concept: ${data.budget_estimate} RON. Specialiștii eligibili au fost notificați.`);
      onClose();
    } catch (e) { alert(formatApiError(e)); }
    finally { setSubmitting(false); }
  };

  if (!elig) return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="text-stone-400">Se încarcă...</div>
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-3" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl max-w-3xl w-full max-h-[95vh] overflow-y-auto" onClick={e => e.stopPropagation()}
        data-testid="design-modal">
        <div className="sticky top-0 z-10 bg-[#0a0a0b]/80 backdrop-blur-xl border-b border-white/10 p-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Palette className="w-5 h-5 text-purple-400" />
            <div>
              <h2 className="font-serif text-2xl">Concept Design Interior</h2>
              <p className="text-xs text-stone-400">Faza 1 din proiect · 2200 RON/cameră (1 zi lucrătoare)</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg" data-testid="design-close"><X className="w-4 h-4 text-stone-400" /></button>
        </div>

        <div className="p-6 space-y-5">
          {/* Property selection */}
          {elig.properties.length > 1 && (
            <div>
              <label className="text-xs uppercase tracking-wider text-stone-400 mb-2 block">Proprietate</label>
              <div className="grid sm:grid-cols-2 gap-2">
                {elig.properties.map((p, i) => (
                  <button key={p.id} onClick={() => { setPropIdx(i); setSelectedRooms([]); }}
                    className={`text-left p-3 rounded-xl border ${i === propIdx ? "border-purple-500/50 bg-purple-500/10" : "border-white/10 bg-white/5"}`}
                    data-testid={`design-prop-${p.id}`}>
                    <div className="font-medium text-sm">{p.name}</div>
                    <div className="text-[10px] text-stone-400">{p.address}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Rooms */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs uppercase tracking-wider text-stone-400">Camere de proiectat ({selectedRooms.length})</label>
              <button onClick={() => setSelectedRooms(prop?.rooms?.map(r => r.id) || [])} className="text-[11px] text-purple-400 hover:underline" data-testid="select-all-rooms">Selectează toate</button>
            </div>
            {(!prop?.rooms || prop.rooms.length === 0) ? (
              <div className="bg-white/5 rounded-xl p-4 text-xs text-stone-400 text-center">
                Twin-ul nu are camere mapate. Cere operatorului să adauge camerele.
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {prop.rooms.map(r => {
                  const sel = selectedRooms.includes(r.id);
                  const Icon = ROOM_ICONS[r.type] || Square;
                  return (
                    <button key={r.id} onClick={() => toggleRoom(r.id)}
                      className={`text-left p-3 rounded-xl border transition ${sel ? "border-purple-500/60 bg-purple-500/15" : "border-white/10 bg-white/5 hover:bg-white/10"}`}
                      data-testid={`design-room-${r.id}`}>
                      <div className="flex items-start justify-between mb-2">
                        <Icon className={`w-4 h-4 ${sel ? "text-purple-300" : "text-stone-400"}`} />
                        {sel && <Check className="w-4 h-4 text-purple-300" />}
                      </div>
                      <div className="text-sm font-medium">{r.name}</div>
                      <div className="text-[10px] text-stone-400">{r.area} m²</div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Style */}
          <div>
            <label className="text-xs uppercase tracking-wider text-stone-400 mb-2 block">Stil preferat</label>
            <div className="flex flex-wrap gap-2">
              {STYLES.map(s => (
                <button key={s.id} onClick={() => setStyle(s.id)}
                  className={`px-3 py-2 rounded-full text-xs flex items-center gap-1.5 border transition ${style === s.id ? "border-purple-500/60 bg-purple-500/15 text-purple-200" : "border-white/10 bg-white/5 text-stone-300 hover:bg-white/10"}`}
                  data-testid={`design-style-${s.id}`}>
                  <span>{s.emoji}</span>{s.label}
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="text-xs uppercase tracking-wider text-stone-400 mb-2 block">Note suplimentare (opțional)</label>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2}
              placeholder="Buget orientativ pe fazele ulterioare, preferințe specifice, restricții..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-purple-500/50 resize-none"
              data-testid="design-notes" />
          </div>

          {/* Pricing summary */}
          <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/5 border border-purple-500/30 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm font-medium">Calcul preț concept</div>
              <Sparkles className="w-4 h-4 text-purple-300" />
            </div>

            <div className="space-y-2 text-sm mb-4">
              <PriceRow label={`Preț standard concept (${pricePerRoom} RON × ${selectedRooms.length})`} value={`${fullPrice} RON`} />
              {effectiveTokens > 0 && <PriceRow label="Discount tokeni" value={`-${effectiveTokens} RON`} highlight="emerald" />}
              <div className="border-t border-white/10 pt-2 flex items-center justify-between">
                <div className="text-sm font-medium">Plătești acum</div>
                <div className="font-serif text-2xl text-purple-200">{finalPrice} RON</div>
              </div>
            </div>

            {/* Token slider */}
            <div className="bg-black/30 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs flex items-center gap-1.5 text-amber-300"><Coins className="w-3.5 h-3.5" />Folosește tokeni (1 token = 1 RON)</label>
                <span className="text-xs text-stone-400">{effectiveTokens} / max {maxTokens}</span>
              </div>
              <input type="range" min={0} max={maxTokens} step={50} value={effectiveTokens}
                onChange={e => setTokensToUse(parseInt(e.target.value))}
                disabled={maxTokens === 0}
                className="w-full accent-purple-500"
                data-testid="design-token-slider" />
              <div className="flex justify-between text-[10px] text-stone-500 mt-1">
                <span>0</span>
                <span>{maxTokens}</span>
              </div>
              <div className="text-[10px] text-stone-500 mt-2">
                Ai {elig.available_tokens} tokeni · Max discount: {elig.max_token_discount_pct}% din preț · Tokenii rămași: {elig.available_tokens - effectiveTokens}
              </div>
            </div>
          </div>

          {/* Info box */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-xs text-stone-400">
            <div className="flex items-start gap-2">
              <Clock className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <div>
                <div className="text-stone-200 font-medium mb-1">Ce primești în faza concept</div>
                Schiță 2D/3D inițială pentru fiecare cameră selectată, paletă de culori și materiale, listă orientativă de mobilier și obiecte decor. Specialistul îți va trimite pe chat oferte separate pentru proiectul tehnic, execuție și achiziții — fiecare ofertă o accepți sau o refuzi individual.
              </div>
            </div>
          </div>
        </div>

        <div className="sticky bottom-0 bg-[#0a0a0b]/80 backdrop-blur-xl border-t border-white/10 p-4 flex gap-2">
          <button onClick={onClose} className="flex-1 py-3 bg-white/5 rounded-xl text-sm">Anulează</button>
          <button onClick={submit} disabled={submitting || selectedRooms.length === 0}
            className="flex-1 btn-accent py-3 rounded-xl text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
            data-testid="design-submit">
            {submitting ? "..." : <><Sparkles className="w-4 h-4" />Plasează cererea</>}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

const PriceRow = ({ label, value, highlight }) => (
  <div className="flex items-center justify-between">
    <span className="text-stone-400 text-xs">{label}</span>
    <span className={`text-sm ${highlight === "emerald" ? "text-emerald-400" : "text-stone-200"}`}>{value}</span>
  </div>
);

// ============= PHASE QUOTES VIEWER (within request detail / chat sidebar) =============
export const DesignPhasesPanel = ({ request, onUpdate }) => {
  const [accepting, setAccepting] = useState(null);
  const phases = request?.phases || [];

  const acceptPhase = async (quoteId) => {
    if (!window.confirm("Confirmi plata fazei din portofelul tău?")) return;
    setAccepting(quoteId);
    try {
      await axios.post(`${API}/design/phase-accept?request_id=${request.id}`, { quote_id: quoteId });
      onUpdate?.();
    } catch (e) { alert(formatApiError(e)); }
    finally { setAccepting(null); }
  };

  const completePhase = async (quoteId) => {
    if (!window.confirm("Marchezi faza completă și eliberezi plata?")) return;
    try {
      await axios.post(`${API}/design/phase-complete?request_id=${request.id}`, { quote_id: quoteId });
      onUpdate?.();
    } catch (e) { alert(formatApiError(e)); }
  };

  if (phases.length === 0) {
    return (
      <div className="bg-white/5 rounded-xl p-4 text-center text-xs text-stone-400">
        Specialistul va trimite oferte pe faze ulterioare după livrarea conceptului.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="text-xs uppercase tracking-wider text-stone-400">Faze proiect ({phases.length})</div>
      {phases.map(p => {
        const statusInfo = {
          pending: { c: "amber", l: "În așteptare" },
          paid: { c: "cyan", l: "În escrow" },
          completed: { c: "emerald", l: "Finalizat" },
          rejected: { c: "red", l: "Respins" },
        }[p.status] || { c: "stone", l: p.status };
        return (
          <div key={p.id} className="bg-white/5 rounded-xl p-4" data-testid={`phase-${p.id}`}>
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="min-w-0">
                <div className="font-medium text-sm">{p.phase_name}</div>
                <div className="text-[10px] text-stone-500">{p.estimated_days} {p.estimated_days === 1 ? "zi" : "zile"} estimat</div>
              </div>
              <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-${statusInfo.c}-500/15 text-${statusInfo.c}-300 border border-${statusInfo.c}-500/30 whitespace-nowrap`}>{statusInfo.l}</span>
            </div>
            <p className="text-xs text-stone-400 mb-3 line-clamp-3">{p.description}</p>
            <div className="flex items-center justify-between">
              <div className="font-serif text-lg">{p.price.toFixed(0)} RON</div>
              <div className="flex gap-2">
                {p.status === "pending" && (
                  <button onClick={() => acceptPhase(p.id)} disabled={accepting === p.id}
                    className="btn-accent px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1"
                    data-testid={`accept-phase-${p.id}`}>
                    <Wallet className="w-3 h-3" />{accepting === p.id ? "..." : "Acceptă & Plătește"}
                  </button>
                )}
                {p.status === "paid" && (
                  <button onClick={() => completePhase(p.id)}
                    className="bg-emerald-500 text-black px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1"
                    data-testid={`complete-phase-${p.id}`}>
                    <CheckCircle2 className="w-3 h-3" />Marchează completă
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ============= SPECIALIST: PROPOSE PHASE MODAL =============
export const ProposePhaseModal = ({ requestId, onClose, onProposed }) => {
  const [form, setForm] = useState({ phase_name: "Proiect tehnic", description: "", price: 5000, estimated_days: 7 });
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (form.phase_name.length < 3) return alert("Numele fazei prea scurt");
    if (form.description.length < 10) return alert("Descrierea trebuie să aibă cel puțin 10 caractere");
    setSubmitting(true);
    try {
      await axios.post(`${API}/design/phase-quote`, { request_id: requestId, ...form });
      onProposed?.();
      onClose();
    } catch (e) { alert(formatApiError(e)); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl p-6 max-w-md w-full" onClick={e => e.stopPropagation()}
        data-testid="propose-phase-modal">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-serif text-xl">Propune fază nouă</h2>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg"><X className="w-4 h-4 text-stone-400" /></button>
        </div>
        <div className="space-y-3">
          <Field label="Nume fază" value={form.phase_name} onChange={v => setForm({ ...form, phase_name: v })} tid="phase-name" />
          <div>
            <label className="text-xs uppercase tracking-wider text-stone-400 mb-1 block">Descriere</label>
            <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={4}
              placeholder="Ce include faza: deliverables, milestones, ipoteze..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:border-[#d4ff3a]/50"
              data-testid="phase-desc" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Preț (RON)" type="number" value={form.price} onChange={v => setForm({ ...form, price: parseFloat(v) || 0 })} tid="phase-price" />
            <Field label="Zile estimate" type="number" value={form.estimated_days} onChange={v => setForm({ ...form, estimated_days: parseInt(v) || 1 })} tid="phase-days" />
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="flex-1 py-2.5 bg-white/5 rounded-xl text-sm">Anulează</button>
          <button onClick={submit} disabled={submitting} className="flex-1 btn-accent py-2.5 rounded-xl text-sm font-medium" data-testid="submit-phase">
            {submitting ? "..." : "Trimite oferta"}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

const Field = ({ label, value, onChange, type = "text", tid }) => (
  <div>
    <label className="text-xs uppercase tracking-wider text-stone-400 mb-1 block">{label}</label>
    <input type={type} value={value} onChange={e => onChange(e.target.value)}
      className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-[#d4ff3a]/50"
      data-testid={tid} />
  </div>
);
