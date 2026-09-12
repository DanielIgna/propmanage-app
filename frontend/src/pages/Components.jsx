// Review Modal + Property Manager + Photo Uploader components
import React, { useState, useRef } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import { Star, Upload, X, Plus, Trash2, Edit2, Building2, Box } from "lucide-react";
import { formatApiError } from "../auth";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ============= PHOTO UPLOADER =============
export const PhotoUploader = ({ photos, onChange, max = 5 }) => {
  const inputRef = useRef(null);
  
  const handleFiles = async (files) => {
    const arr = Array.from(files).slice(0, max - photos.length);
    const newPhotos = [];
    for (const file of arr) {
      if (file.size > 2 * 1024 * 1024) {
        alert(`${file.name} este prea mare (max 2MB)`);
        continue;
      }
      const dataUrl = await new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(r.result);
        r.onerror = rej;
        r.readAsDataURL(file);
      });
      newPhotos.push(dataUrl);
    }
    onChange([...photos, ...newPhotos]);
  };
  
  return (
    <div>
      <div className="grid grid-cols-3 gap-2">
        {photos.map((p, i) => (
          <div key={i} className="relative aspect-square rounded-lg overflow-hidden bg-white/5 group">
            <img src={p} alt="" className="w-full h-full object-cover" />
            <button onClick={() => onChange(photos.filter((_, idx) => idx !== i))} 
              className="absolute top-1 right-1 w-6 h-6 bg-black/80 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition" data-testid={`photo-rm-${i}`}>
              <X className="w-3 h-3" />
            </button>
          </div>
        ))}
        {photos.length < max && (
          <button type="button" onClick={() => inputRef.current?.click()} 
            className="aspect-square rounded-lg border-2 border-dashed border-white/10 hover:border-[#d4ff3a]/50 flex flex-col items-center justify-center gap-1 transition" data-testid="photo-add">
            <Upload className="w-4 h-4 text-stone-500" />
            <span className="text-[10px] text-stone-500">{photos.length}/{max}</span>
          </button>
        )}
      </div>
      <input ref={inputRef} type="file" accept="image/*" multiple className="hidden" 
        onChange={e => { handleFiles(e.target.files); e.target.value = ""; }} />
      <div className="text-[10px] text-stone-500 mt-1">JPG/PNG · max 2MB / poză</div>
    </div>
  );
};

// ============= REVIEW MODAL =============
export const ReviewModal = ({ requestId, specialistName, onClose, onSubmitted }) => {
  const [rating, setRating] = useState(5);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [hireAgain, setHireAgain] = useState(null);
  const [recommend, setRecommend] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const submit = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/requests/${requestId}/review`, {
        job_id: requestId, rating, comment,
        would_hire_again: hireAgain, would_recommend: recommend,
      });
      onSubmitted?.();
      onClose();
    } catch (e) { alert(formatApiError(e)); }
    finally { setLoading(false); }
  };
  
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-6" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl p-8 max-w-md w-full" onClick={e => e.stopPropagation()} data-testid="review-modal">
        <h2 className="font-serif text-2xl mb-2">Evaluează specialistul</h2>
        <p className="text-sm text-stone-400 mb-6">{specialistName}</p>
        
        <div className="flex justify-center gap-2 mb-6">
          {[1,2,3,4,5].map(n => (
            <button key={n} type="button"
              onClick={() => setRating(n)}
              onMouseEnter={() => setHover(n)}
              onMouseLeave={() => setHover(0)}
              data-testid={`star-${n}`}
              className="transition-transform hover:scale-110">
              <Star className={`w-10 h-10 transition ${
                n <= (hover || rating) ? "fill-amber-400 text-amber-400" : "text-stone-700"
              }`} />
            </button>
          ))}
        </div>

        {/* GBOS P0.3 — Rebook > stele */}
        <div className="mb-4">
          <div className="text-xs font-bold text-stone-300 mb-2">Ai angaja din nou acest specialist?</div>
          <div className="flex gap-2">
            {[["yes", "Da"], ["no", "Nu"], ["not_sure", "Nu sunt sigur"]].map(([v, l]) => (
              <button key={v} type="button" onClick={() => setHireAgain(v)} data-testid={`review-hire-${v}`}
                className={`flex-1 py-2 rounded-full text-xs font-bold border transition-colors ${hireAgain === v ? "bg-[#d4ff3a] text-black border-[#d4ff3a]" : "bg-white/5 border-white/10 text-stone-300"}`}>{l}</button>
            ))}
          </div>
        </div>
        <div className="mb-5">
          <div className="text-xs font-bold text-stone-300 mb-2">L-ai recomanda altui proprietar?</div>
          <div className="flex gap-2">
            {[[true, "Da"], [false, "Nu"]].map(([v, l]) => (
              <button key={String(v)} type="button" onClick={() => setRecommend(v)} data-testid={`review-recommend-${v ? "yes" : "no"}`}
                className={`flex-1 py-2 rounded-full text-xs font-bold border transition-colors ${recommend === v ? "bg-[#d4ff3a] text-black border-[#d4ff3a]" : "bg-white/5 border-white/10 text-stone-300"}`}>{l}</button>
            ))}
          </div>
        </div>
        
        <textarea
          value={comment}
          onChange={e => setComment(e.target.value)}
          placeholder="Comentariu opțional - cum a fost experiența ta?"
          rows={3}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#d4ff3a]/50 resize-none mb-6"
          data-testid="review-comment"
        />
        
        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 py-3 bg-white/5 rounded-xl text-sm" data-testid="review-skip">Mai târziu</button>
          <button onClick={submit} disabled={loading} className="flex-1 btn-accent py-3 rounded-xl text-sm font-medium" data-testid="review-submit">
            {loading ? "..." : "Trimite (+20 tokeni)"}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

// ============= PROPERTY MANAGER =============
export const PropertyManagerModal = ({ properties, onClose, onChange, onOpenTwin }) => {
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", address: "", type: "apartment", surface: 50, rooms: 2 });
  const [showAdd, setShowAdd] = useState((properties || []).length === 0);
  const [twinIndex, setTwinIndex] = useState({}); // { property_id: { status, dt_project_id, model_url } }

  // Batch-load DT status across all owned properties so each row can show a colored
  // 3D button. One call, refreshed when the list changes.
  React.useEffect(() => {
    let cancelled = false;
    axios.get(`${API}/me/digital-twins`).then(r => {
      if (cancelled) return;
      const idx = {};
      (r.data?.twins || []).forEach(t => {
        idx[t.property_id] = {
          status: t.status,
          dt_project_id: t.dt_project_id,
          dt_project_name: t.dt_project_name,
          model_url: t.model_url,
          property_name: t.property_name,
        };
      });
      setTwinIndex(idx);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [properties.length]);
  
  const refresh = async () => {
    const { data } = await axios.get(`${API}/properties`);
    onChange(data);
  };
  
  const startEdit = (p) => {
    setEditing(p.id);
    setForm({ name: p.name, address: p.address, type: p.type, surface: p.surface, rooms: p.rooms });
  };
  
  const save = async () => {
    try {
      const isFirst = !editing && (properties || []).length === 0;
      if (editing) {
        await axios.put(`${API}/properties/${editing}`, form);
      } else {
        await axios.post(`${API}/properties`, form);
      }
      await refresh();
      setEditing(null); setShowAdd(false);
      setForm({ name: "", address: "", type: "apartment", surface: 50, rooms: 2 });
      if (isFirst) onClose();
    } catch (e) { alert(formatApiError(e)); }
  };
  
  const del = async (id) => {
    if (!window.confirm("Sigur dorești să ștergi această proprietate?")) return;
    try {
      await axios.delete(`${API}/properties/${id}`);
      await refresh();
    } catch (e) { alert(formatApiError(e)); }
  };
  
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-6" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl p-8 max-w-2xl w-full max-h-[90vh] overflow-auto no-scrollbar" onClick={e => e.stopPropagation()} data-testid="property-modal">
        <div className="flex justify-between items-center mb-6">
          <h2 className="font-serif text-2xl">Proprietățile mele</h2>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg" data-testid="prop-close">
            <X className="w-4 h-4" />
          </button>
        </div>
        
        {!showAdd && !editing && (
          <button onClick={() => setShowAdd(true)} className="w-full mb-4 btn-accent py-3 rounded-xl text-sm font-medium flex items-center justify-center gap-2" data-testid="prop-add-btn">
            <Plus className="w-4 h-4" />Adaugă proprietate
          </button>
        )}
        
        {(showAdd || editing) && (
          <div className="bg-white/5 rounded-2xl p-5 mb-4 space-y-3">
            <input placeholder="Nume (ex: Apartament Cluj)" value={form.name} onChange={e => setForm({...form, name: e.target.value})}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm" data-testid="prop-name" />
            <input placeholder="Adresă" value={form.address} onChange={e => setForm({...form, address: e.target.value})}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm" data-testid="prop-address" />
            <div className="grid grid-cols-3 gap-2">
              <select value={form.type} onChange={e => setForm({...form, type: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-3 py-3 text-sm" data-testid="prop-type">
                <option value="apartment">Apartament</option>
                <option value="house">Casă</option>
                <option value="villa">Vilă</option>
              </select>
              <input type="number" placeholder="Suprafață m²" value={form.surface} onChange={e => setForm({...form, surface: parseFloat(e.target.value)})}
                className="bg-white/5 border border-white/10 rounded-xl px-3 py-3 text-sm" data-testid="prop-surface" />
              <input type="number" placeholder="Camere" value={form.rooms} onChange={e => setForm({...form, rooms: parseInt(e.target.value)})}
                className="bg-white/5 border border-white/10 rounded-xl px-3 py-3 text-sm" data-testid="prop-rooms" />
            </div>
            <div className="flex gap-2">
              <button onClick={() => { setShowAdd(false); setEditing(null); }} className="flex-1 py-2.5 bg-white/5 rounded-xl text-sm">Anulează</button>
              <button onClick={save} className="flex-1 btn-accent py-2.5 rounded-xl text-sm font-medium" data-testid="prop-save">{editing ? "Salvează" : "Adaugă"}</button>
            </div>
          </div>
        )}
        
        <div className="space-y-2">
          {properties.map(p => {
            const tw = twinIndex[p.id] || {};
            const twinStatus = tw.status;
            const twinAvailable = twinStatus === "approved";
            const twinInFlight = twinStatus === "pending_validation" || twinStatus === "draft";
            const has3D = twinAvailable && !!tw.model_url;
            const twinTone = twinAvailable
              ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/25"
              : twinInFlight
                ? "bg-amber-500/10 border-amber-500/30 text-amber-300/70 cursor-not-allowed"
                : "bg-white/5 border-white/10 text-stone-400 hover:bg-white/10";
            const twinTitle = has3D
              ? "Vezi modelul 3D (rotație 360° · X-Ray · Wireframe)"
              : twinAvailable
                ? "Vezi planul 2D al proprietății"
                : twinInFlight
                  ? "Digital Twin în generare — revino în curând"
                  : "Digital Twin indisponibil";
            return (
              <div key={p.id} className="bg-white/5 rounded-xl p-4 flex items-center gap-3" data-testid={`prop-item-${p.id}`}>
                <div className="w-10 h-10 rounded-lg bg-emerald-500/15 flex items-center justify-center">
                  <Building2 className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{p.name}</div>
                  <div className="text-[10px] text-stone-500">{p.type} · {p.surface}m² · {p.rooms} camere · Health: {p.health_score}/100</div>
                </div>
                {onOpenTwin && (
                  <button
                    onClick={() => twinAvailable && onOpenTwin({
                      property_id: p.id,
                      property_name: p.name,
                      dt_project_id: tw.dt_project_id,
                      dt_project_name: tw.dt_project_name,
                      model_url: tw.model_url,
                    })}
                    disabled={!twinAvailable}
                    title={twinTitle}
                    className={`px-2 py-1.5 rounded-lg border text-[10px] uppercase tracking-wider inline-flex items-center gap-1 transition ${twinTone}`}
                    data-testid={`prop-twin-${p.id}`}
                  >
                    <Box className="w-3.5 h-3.5" />{has3D ? "3D" : "2D"}
                  </button>
                )}
                <button onClick={() => startEdit(p)} className="p-2 hover:bg-white/10 rounded-lg" data-testid={`prop-edit-${p.id}`}>
                  <Edit2 className="w-3.5 h-3.5 text-stone-400" />
                </button>
                <button onClick={() => del(p.id)} className="p-2 hover:bg-red-500/10 rounded-lg" data-testid={`prop-del-${p.id}`}>
                  <Trash2 className="w-3.5 h-3.5 text-red-400" />
                </button>
              </div>
            );
          })}
        </div>
      </motion.div>
    </div>
  );
};
