// PropManage - Specialist Portfolio (manager modal + public gallery)
import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import {
  Image as ImageIcon, Plus, Trash2, Edit3, X, MapPin, Maximize2, Layers, Briefcase,
  ChevronLeft, ChevronRight, Upload, Camera,
} from "lucide-react";
import { formatApiError } from "../auth";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const CATEGORY_LABELS = {
  interior_design: "Design Interior",
  renovation: "Renovare",
  hvac: "HVAC / Climatizare",
  electric: "Electric",
  plumbing: "Sanitar",
  carpentry: "Tâmplărie",
  other: "Altele",
};

const STYLE_LABELS = {
  modern: "Modern", scandinavian: "Scandinavian", minimalist: "Minimalist",
  industrial: "Industrial", boho: "Boho", classic: "Clasic", rustic: "Rustic",
  japandi: "Japandi", mediterranean: "Mediteranean",
};

// ============= PUBLIC GALLERY (shown on specialist profile) =============
export const PortfolioGallery = ({ specialistId }) => {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    if (!specialistId) return;
    axios.get(`${API}/specialists/${specialistId}/portfolio`).then(r => setItems(r.data)).catch(() => setItems([]));
  }, [specialistId]);

  if (!items.length) {
    return (
      <div className="bg-white/5 rounded-2xl p-8 text-center" data-testid="portfolio-empty">
        <Briefcase className="w-10 h-10 text-stone-600 mx-auto mb-3" />
        <p className="text-sm text-stone-400">Acest specialist nu are încă proiecte publicate.</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="portfolio-grid">
        {items.map(it => (
          <button key={it.id} onClick={() => setSelected(it)}
            className="text-left group bg-white/5 rounded-2xl overflow-hidden hover:bg-white/10 transition border border-white/5"
            data-testid={`portfolio-item-${it.id}`}>
            <div className="relative aspect-[4/3] overflow-hidden">
              <img src={it.cover_image} alt={it.title} className="w-full h-full object-cover group-hover:scale-105 transition duration-500" />
              {it.gallery && it.gallery.length > 0 && (
                <div className="absolute top-2 right-2 bg-black/60 backdrop-blur-sm rounded-full px-2 py-0.5 text-[10px] flex items-center gap-1">
                  <ImageIcon className="w-3 h-3" />{it.gallery.length + 1}
                </div>
              )}
              {it.style && (
                <div className="absolute bottom-2 left-2 bg-purple-500/80 backdrop-blur-sm rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wider">
                  {STYLE_LABELS[it.style] || it.style}
                </div>
              )}
            </div>
            <div className="p-3">
              <div className="text-sm font-medium line-clamp-1">{it.title}</div>
              <div className="flex items-center gap-2 mt-1 text-[10px] text-stone-500">
                <span>{CATEGORY_LABELS[it.category] || it.category}</span>
                {it.location && <><span>·</span><span className="flex items-center gap-0.5"><MapPin className="w-2.5 h-2.5" />{it.location}</span></>}
                {it.surface && <><span>·</span><span>{it.surface} m²</span></>}
              </div>
            </div>
          </button>
        ))}
      </div>
      {selected && <PortfolioLightbox item={selected} onClose={() => setSelected(null)} />}
    </>
  );
};

// ============= LIGHTBOX =============
const PortfolioLightbox = ({ item, onClose }) => {
  const allImages = [item.cover_image, ...(item.gallery || [])];
  const [idx, setIdx] = useState(0);
  const prev = () => setIdx((idx - 1 + allImages.length) % allImages.length);
  const next = () => setIdx((idx + 1) % allImages.length);

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose} data-testid="portfolio-lightbox">
      <div className="max-w-5xl w-full" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3 text-stone-100">
          <div className="min-w-0">
            <div className="font-serif text-xl truncate">{item.title}</div>
            <div className="text-xs text-stone-400">{CATEGORY_LABELS[item.category] || item.category} {item.style && `· ${STYLE_LABELS[item.style] || item.style}`}</div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg" data-testid="lightbox-close">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="relative bg-black rounded-2xl overflow-hidden">
          <img src={allImages[idx]} alt={`${item.title} ${idx+1}`} className="w-full max-h-[70vh] object-contain bg-black" />
          {allImages.length > 1 && (
            <>
              <button onClick={prev} className="absolute left-3 top-1/2 -translate-y-1/2 p-2 bg-black/60 hover:bg-black/80 rounded-full backdrop-blur-sm" data-testid="lightbox-prev">
                <ChevronLeft className="w-5 h-5 text-white" />
              </button>
              <button onClick={next} className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-black/60 hover:bg-black/80 rounded-full backdrop-blur-sm" data-testid="lightbox-next">
                <ChevronRight className="w-5 h-5 text-white" />
              </button>
              <div className="absolute bottom-3 left-1/2 -translate-x-1/2 bg-black/60 backdrop-blur-sm rounded-full px-3 py-1 text-xs">
                {idx + 1} / {allImages.length}
              </div>
            </>
          )}
        </div>
        {item.description && (
          <p className="mt-3 text-sm text-stone-300 leading-relaxed bg-white/5 rounded-xl p-4">{item.description}</p>
        )}
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          {item.location && <Chip icon={MapPin}>{item.location}</Chip>}
          {item.surface && <Chip icon={Maximize2}>{item.surface} m²</Chip>}
          {item.completion_date && <Chip icon={Layers}>{new Date(item.completion_date).toLocaleDateString("ro-RO", { year: "numeric", month: "long" })}</Chip>}
        </div>
      </div>
    </div>
  );
};

const Chip = ({ children, icon: Ic }) => (
  <span className="inline-flex items-center gap-1 bg-white/10 text-stone-300 px-2.5 py-1 rounded-full">
    {Ic && <Ic className="w-3 h-3" />}{children}
  </span>
);

// ============= MANAGER MODAL (specialist's own) =============
export const PortfolioManagerModal = ({ onClose }) => {
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const [showEditor, setShowEditor] = useState(false);

  const load = () => axios.get(`${API}/specialist/portfolio`).then(r => setItems(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const remove = async (id) => {
    if (!window.confirm("Sigur ștergi acest proiect?")) return;
    try { await axios.delete(`${API}/specialist/portfolio/${id}`); load(); }
    catch (e) { alert(formatApiError(e)); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-3" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl max-w-4xl w-full max-h-[95vh] overflow-y-auto" onClick={e => e.stopPropagation()}
        data-testid="portfolio-manager">
        <div className="sticky top-0 bg-[#0a0a0b]/85 backdrop-blur-xl border-b border-white/10 p-5 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <Briefcase className="w-5 h-5 text-[#d4ff3a]" />
            <div>
              <h2 className="font-serif text-2xl">Portofoliul meu</h2>
              <p className="text-xs text-stone-400">{items.length} {items.length === 1 ? "proiect" : "proiecte"} publicate</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => { setEditing(null); setShowEditor(true); }} className="btn-accent px-3 py-2 rounded-full text-xs font-medium flex items-center gap-1" data-testid="add-portfolio-item">
              <Plus className="w-3.5 h-3.5" />Adaugă proiect
            </button>
            <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg"><X className="w-4 h-4 text-stone-400" /></button>
          </div>
        </div>

        <div className="p-6">
          {items.length === 0 ? (
            <div className="bg-white/5 rounded-2xl p-10 text-center">
              <Briefcase className="w-12 h-12 text-stone-600 mx-auto mb-3" />
              <h3 className="font-serif text-lg mb-1">Nu ai încă proiecte publicate</h3>
              <p className="text-sm text-stone-400 mb-4">Adaugă imagini din lucrările tale anterioare pentru a câștiga încrederea clienților.</p>
              <button onClick={() => { setEditing(null); setShowEditor(true); }} className="btn-accent px-4 py-2 rounded-full text-sm font-medium inline-flex items-center gap-2">
                <Plus className="w-4 h-4" />Primul proiect
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {items.map(it => (
                <div key={it.id} className="bg-white/5 rounded-2xl overflow-hidden border border-white/5" data-testid={`my-portfolio-${it.id}`}>
                  <div className="aspect-[4/3] overflow-hidden">
                    <img src={it.cover_image} alt={it.title} className="w-full h-full object-cover" />
                  </div>
                  <div className="p-3">
                    <div className="text-sm font-medium line-clamp-1 mb-1">{it.title}</div>
                    <div className="text-[10px] text-stone-500 mb-3">{CATEGORY_LABELS[it.category] || it.category} {it.style && `· ${STYLE_LABELS[it.style]}`}</div>
                    <div className="flex gap-2">
                      <button onClick={() => { setEditing(it); setShowEditor(true); }} className="flex-1 bg-white/10 hover:bg-white/15 py-1.5 rounded-lg text-xs flex items-center justify-center gap-1" data-testid={`edit-portfolio-${it.id}`}>
                        <Edit3 className="w-3 h-3" />Editează
                      </button>
                      <button onClick={() => remove(it.id)} className="bg-red-500/15 hover:bg-red-500/25 text-red-400 px-3 py-1.5 rounded-lg text-xs" data-testid={`del-portfolio-${it.id}`}>
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {showEditor && (
          <PortfolioEditor
            item={editing}
            onClose={() => setShowEditor(false)}
            onSaved={() => { setShowEditor(false); load(); }}
          />
        )}
      </motion.div>
    </div>
  );
};

// ============= EDITOR =============
const PortfolioEditor = ({ item, onClose, onSaved }) => {
  const isEdit = !!item;
  const [form, setForm] = useState(item || {
    title: "", description: "", style: "modern", category: "interior_design",
    cover_image: "", gallery: [], location: "", surface: ""
  });
  const [saving, setSaving] = useState(false);

  const onPickCover = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 4 * 1024 * 1024) return alert("Imaginea depășește 4 MB");
    const r = new FileReader();
    r.onload = () => setForm({ ...form, cover_image: r.result });
    r.readAsDataURL(f);
  };

  const onPickGallery = async (e) => {
    const files = Array.from(e.target.files || []).slice(0, 12 - (form.gallery?.length || 0));
    const reads = await Promise.all(files.map(f => new Promise(res => {
      if (f.size > 4 * 1024 * 1024) return res(null);
      const r = new FileReader();
      r.onload = () => res(r.result);
      r.readAsDataURL(f);
    })));
    setForm({ ...form, gallery: [...(form.gallery || []), ...reads.filter(Boolean)] });
  };

  const removeGalleryItem = (idx) => {
    setForm({ ...form, gallery: form.gallery.filter((_, i) => i !== idx) });
  };

  const submit = async () => {
    if (form.title.trim().length < 3) return alert("Titlul prea scurt");
    if (!form.cover_image) return alert("Adaugă o imagine cover");
    setSaving(true);
    try {
      const payload = {
        ...form,
        surface: form.surface ? parseFloat(form.surface) : null,
        gallery: form.gallery || [],
      };
      if (isEdit) await axios.put(`${API}/specialist/portfolio/${item.id}`, payload);
      else await axios.post(`${API}/specialist/portfolio`, payload);
      onSaved();
    } catch (e) { alert(formatApiError(e)); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[60] p-3" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-strong rounded-3xl max-w-2xl w-full max-h-[95vh] overflow-y-auto" onClick={e => e.stopPropagation()}
        data-testid="portfolio-editor">
        <div className="sticky top-0 bg-[#0a0a0b]/85 backdrop-blur-xl border-b border-white/10 p-4 flex items-center justify-between">
          <h3 className="font-serif text-xl">{isEdit ? "Editează proiect" : "Proiect nou"}</h3>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg"><X className="w-4 h-4 text-stone-400" /></button>
        </div>
        <div className="p-5 space-y-4">
          <Field label="Titlu" value={form.title} onChange={v => setForm({ ...form, title: v })} tid="pf-title" />
          <div>
            <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">Descriere</label>
            <textarea value={form.description || ""} onChange={e => setForm({ ...form, description: e.target.value })} rows={4}
              placeholder="Descrie pe scurt proiectul: materiale, soluții, provocări..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-[#d4ff3a]/50 resize-none"
              data-testid="pf-desc" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">Categorie</label>
              <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-[#d4ff3a]/50"
                data-testid="pf-cat">
                {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">Stil</label>
              <select value={form.style || ""} onChange={e => setForm({ ...form, style: e.target.value || null })}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-[#d4ff3a]/50"
                data-testid="pf-style">
                <option value="">Fără stil specific</option>
                {Object.entries(STYLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Locație" value={form.location || ""} onChange={v => setForm({ ...form, location: v })} placeholder="ex: București - Floreasca" tid="pf-loc" />
            <Field label="Suprafață (m²)" type="number" value={form.surface || ""} onChange={v => setForm({ ...form, surface: v })} placeholder="95" tid="pf-surf" />
          </div>

          {/* Cover image */}
          <div>
            <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">Imagine cover *</label>
            {form.cover_image ? (
              <div className="relative aspect-[4/3] bg-white/5 rounded-xl overflow-hidden group">
                <img src={form.cover_image} alt="cover" className="w-full h-full object-cover" />
                <button onClick={() => setForm({ ...form, cover_image: "" })}
                  className="absolute top-2 right-2 p-2 bg-black/70 hover:bg-red-500 rounded-full opacity-0 group-hover:opacity-100 transition">
                  <Trash2 className="w-3.5 h-3.5 text-red-300" />
                </button>
              </div>
            ) : (
              <label className="block aspect-[4/3] bg-white/5 border border-dashed border-white/20 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:bg-white/10" data-testid="pf-cover-input">
                <Camera className="w-8 h-8 text-stone-500 mb-2" />
                <span className="text-xs text-stone-400">Click pentru a încărca imagine (max 4MB)</span>
                <input type="file" accept="image/*" className="hidden" onChange={onPickCover} />
              </label>
            )}
          </div>

          {/* Gallery */}
          <div>
            <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">Galerie (opțional, max 12)</label>
            <div className="grid grid-cols-4 gap-2">
              {(form.gallery || []).map((g, i) => (
                <div key={i} className="relative aspect-square bg-white/5 rounded-lg overflow-hidden group">
                  <img src={g} alt={`g-${i}`} className="w-full h-full object-cover" />
                  <button onClick={() => removeGalleryItem(i)}
                    className="absolute top-1 right-1 p-1 bg-black/70 hover:bg-red-500 rounded-full opacity-0 group-hover:opacity-100 transition">
                    <Trash2 className="w-3 h-3 text-red-300" />
                  </button>
                </div>
              ))}
              {(form.gallery?.length || 0) < 12 && (
                <label className="aspect-square bg-white/5 border border-dashed border-white/20 rounded-lg flex flex-col items-center justify-center cursor-pointer hover:bg-white/10" data-testid="pf-gallery-input">
                  <Upload className="w-4 h-4 text-stone-500 mb-0.5" />
                  <span className="text-[9px] text-stone-500">Adaugă</span>
                  <input type="file" accept="image/*" multiple className="hidden" onChange={onPickGallery} />
                </label>
              )}
            </div>
          </div>
        </div>

        <div className="sticky bottom-0 bg-[#0a0a0b]/85 backdrop-blur-xl border-t border-white/10 p-4 flex gap-2">
          <button onClick={onClose} className="flex-1 py-2.5 bg-white/5 rounded-xl text-sm">Anulează</button>
          <button onClick={submit} disabled={saving} className="flex-1 btn-accent py-2.5 rounded-xl text-sm font-medium disabled:opacity-50" data-testid="pf-save">
            {saving ? "..." : isEdit ? "Salvează modificările" : "Publică proiectul"}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

const Field = ({ label, value, onChange, type = "text", placeholder, tid }) => (
  <div>
    <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">{label}</label>
    <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
      className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-[#d4ff3a]/50"
      data-testid={tid} />
  </div>
);
