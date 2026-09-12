import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Save, Megaphone, Type, Plus, Trash2, Eye } from "lucide-react";
import { AdminLayoutMetronic } from "./AdminLayoutMetronic";

const API = process.env.REACT_APP_BACKEND_URL;

const Input = (props) => (
  <input {...props} className={`w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-sm ${props.className || ""}`} />
);

export default function ContentManagerPage() {
  const [content, setContent] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    axios.get(`${API}/api/admin/site-content`, { withCredentials: true }).then((r) => setContent(r.data)).catch(() => toast.error("Nu am putut încărca conținutul."));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/api/admin/site-content`, content, { withCredentials: true });
      toast.success("Conținut salvat — vizibil instant pe site.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la salvare.");
    } finally {
      setSaving(false);
    }
  };

  if (!content) return <AdminLayoutMetronic title="XOS · Content Manager" subtitle="Texte și bannere din DB"><div className="p-8 text-slate-400">Se încarcă...</div></AdminLayoutMetronic>;

  const b = content.banner;
  const h = content.hero;
  const bannerBg = b.variant === "promo" ? "bg-[#d4ff3a] text-black" : b.variant === "warning" ? "bg-amber-500 text-black" : "bg-sky-500 text-white";

  return (
    <AdminLayoutMetronic title="XOS · Theme & Content Manager" subtitle="Texte, bannere și anunțuri editabile din DB — fără cod">
      <div className="max-w-3xl mx-auto space-y-6 p-4 sm:p-6" data-testid="content-manager-page">
        <div className="flex justify-end">
          <button onClick={save} disabled={saving} className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-sm font-bold bg-lime-500 text-black hover:bg-lime-400 disabled:opacity-50" data-testid="content-save">
            <Save className="w-4 h-4" /> {saving ? "Se salvează..." : "Salvează tot"}
          </button>
        </div>

        <section className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 space-y-3">
          <h2 className="text-sm font-black flex items-center gap-2"><Megaphone className="w-4 h-4 text-lime-600" /> Banner anunț (homepage)</h2>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={b.active} onChange={(e) => setContent({ ...content, banner: { ...b, active: e.target.checked } })} data-testid="banner-active" />
            Banner activ pe homepage
          </label>
          <Input value={b.text} onChange={(e) => setContent({ ...content, banner: { ...b, text: e.target.value } })} placeholder="Textul anunțului" data-testid="banner-text" />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <Input value={b.link} onChange={(e) => setContent({ ...content, banner: { ...b, link: e.target.value } })} placeholder="Link (/design-interior)" data-testid="banner-link" />
            <Input value={b.link_label} onChange={(e) => setContent({ ...content, banner: { ...b, link_label: e.target.value } })} placeholder="Etichetă buton" data-testid="banner-link-label" />
            <select value={b.variant} onChange={(e) => setContent({ ...content, banner: { ...b, variant: e.target.value } })}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-sm" data-testid="banner-variant">
              <option value="promo">Promo (lime)</option>
              <option value="info">Info (albastru)</option>
              <option value="warning">Atenție (amber)</option>
            </select>
          </div>
          <div className="space-y-1">
            <div className="text-[10px] font-black uppercase text-slate-400 flex items-center gap-1"><Eye className="w-3 h-3" /> Preview</div>
            <div className={`rounded-xl px-4 py-2 text-sm font-semibold flex items-center gap-2 ${bannerBg}`} data-testid="banner-preview">
              <Megaphone className="w-4 h-4" /><span className="flex-1">{b.text || "Textul anunțului..."}</span>
              {b.link && <span className="underline font-bold">{b.link_label || "Vezi"}</span>}
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 space-y-3">
          <h2 className="text-sm font-black flex items-center gap-2"><Type className="w-4 h-4 text-lime-600" /> Override texte Hero (homepage)</h2>
          <p className="text-xs text-slate-400">Lasă gol pentru textul implicit din traduceri. Completează doar ce vrei să suprascrii.</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <Input value={h.title1} onChange={(e) => setContent({ ...content, hero: { ...h, title1: e.target.value } })} placeholder="Titlu rând 1" data-testid="hero-title1" />
            <Input value={h.title2} onChange={(e) => setContent({ ...content, hero: { ...h, title2: e.target.value } })} placeholder="Titlu accent (italic)" data-testid="hero-title2" />
            <Input value={h.title3} onChange={(e) => setContent({ ...content, hero: { ...h, title3: e.target.value } })} placeholder="Titlu rând 2" data-testid="hero-title3" />
          </div>
          <Input value={h.subtitle} onChange={(e) => setContent({ ...content, hero: { ...h, subtitle: e.target.value } })} placeholder="Subtitlu hero" data-testid="hero-subtitle" />
        </section>

        <section className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 space-y-3">
          <h2 className="text-sm font-black">Conținut personalizat (chei libere)</h2>
          {content.entries.map((e, i) => (
            <div key={i} className="flex items-center gap-2">
              <Input value={e.key} onChange={(ev) => setContent({ ...content, entries: content.entries.map((x, xi) => (xi === i ? { ...x, key: ev.target.value } : x)) })} placeholder="cheie" className="!w-48" />
              <Input value={e.value} onChange={(ev) => setContent({ ...content, entries: content.entries.map((x, xi) => (xi === i ? { ...x, value: ev.target.value } : x)) })} placeholder="valoare" />
              <button onClick={() => setContent({ ...content, entries: content.entries.filter((_, xi) => xi !== i) })} className="p-1.5 text-red-400 hover:bg-red-50 rounded-lg"><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
          <button onClick={() => setContent({ ...content, entries: [...content.entries, { key: "", value: "" }] })}
            className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600" data-testid="content-add-entry">
            <Plus className="w-3.5 h-3.5" /> Adaugă intrare
          </button>
        </section>
      </div>
    </AdminLayoutMetronic>
  );
}
