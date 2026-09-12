// InteriorDesignAdminPage — administrare completă serviciu Design Interior.
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { Sofa, Save, ExternalLink, RefreshCw } from "lucide-react";
import { AdminLayoutMetronic, AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { KpiCard, DSButton, EmptyState, DSSkeleton } from "../../design-system";

const ax = axios.create({ baseURL: API, withCredentials: true });
const STATUS = { new: "Nou", contacted: "Contactat", offered: "Ofertat", won: "Câștigat", lost: "Pierdut" };
const STATUS_CLS = { new: "bg-cyan-500", contacted: "bg-amber-400", offered: "bg-lime-400", won: "bg-emerald-500", lost: "bg-rose-500" };

export default function InteriorDesignAdminPage() {
  const [content, setContent] = useState(null);
  const [leads, setLeads] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [flash, setFlash] = useState(null);

  const load = useCallback(async () => {
    try {
      const [c, l] = await Promise.all([
        ax.get("/admin/interior-design/content"),
        ax.get("/admin/interior-design/leads"),
      ]);
      setContent(c.data);
      setLeads(l.data);
    } catch (e) { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async (patch) => {
    setSaving(true);
    try {
      const r = await ax.put("/admin/interior-design/content", patch);
      setContent(r.data);
      setFlash("Salvat — modificările sunt LIVE pe /design-interior.");
      setTimeout(() => setFlash(null), 3000);
    } catch (e) { setFlash("Eroare la salvare."); }
    setSaving(false);
  };

  const setLeadStatus = async (id, status) => {
    try { await ax.patch(`/admin/interior-design/leads/${id}`, { status }); load(); } catch (e) { /* silent */ }
  };

  const upd = (path, value) => {
    setContent((c) => {
      const copy = JSON.parse(JSON.stringify(c));
      const keys = path.split(".");
      let o = copy;
      for (let i = 0; i < keys.length - 1; i++) o = o[keys[i]];
      o[keys[keys.length - 1]] = value;
      return copy;
    });
  };

  const inputCls = "w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm";
  const counts = leads?.counts || {};

  return (
    <AdminLayoutMetronic title="Design Interior · Administrare" subtitle="Serviciu independent — conținut, SEO, vizibilitate și lead-uri">
      {loading ? <DSSkeleton kpis={4} blocks={2} /> : (
        <div className="space-y-6" data-testid="interior-admin-root">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard icon={Sofa} label="Lead-uri totale" value={leads?.total ?? 0} accent="ai" testid="ida-kpi-total" />
            <KpiCard icon={Sofa} label="Noi" value={counts.new ?? 0} accent="info" testid="ida-kpi-new" />
            <KpiCard icon={Sofa} label="Ofertate" value={counts.offered ?? 0} accent="warning" testid="ida-kpi-offered" />
            <KpiCard icon={Sofa} label="Câștigate" value={counts.won ?? 0} accent="success" testid="ida-kpi-won" />
          </div>

          {flash && <div className="p-3 rounded-xl text-sm bg-lime-50 dark:bg-lime-500/10 border border-lime-300 dark:border-lime-500/30 text-lime-800 dark:text-lime-200" data-testid="ida-flash">{flash}</div>}

          <AdminCard
            title="Setări serviciu + SEO"
            action={
              <div className="flex gap-2">
                <a href="/design-interior" target="_blank" rel="noreferrer"><DSButton variant="ghost" icon={ExternalLink} data-testid="ida-preview">Vezi pagina</DSButton></a>
                <DSButton variant="primary" icon={Save} disabled={saving} onClick={() => save({ active: content.active, show_on_homepage: content.show_on_homepage, seo: content.seo, hero: content.hero })} data-testid="ida-save">{saving ? "Salvez…" : "Salvează"}</DSButton>
              </div>
            }
            testid="ida-settings"
          >
            <div className="grid lg:grid-cols-2 gap-4">
              <div className="space-y-3">
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-sm font-semibold">
                    <input type="checkbox" checked={!!content.active} onChange={(e) => upd("active", e.target.checked)} data-testid="ida-toggle-active" /> Serviciu activ
                  </label>
                  <label className="flex items-center gap-2 text-sm font-semibold">
                    <input type="checkbox" checked={!!content.show_on_homepage} onChange={(e) => upd("show_on_homepage", e.target.checked)} data-testid="ida-toggle-homepage" /> Afișat pe homepage
                  </label>
                </div>
                <div><label className="text-[10px] font-bold uppercase text-slate-400">H1 (hero)</label>
                  <input value={content.hero.h1} onChange={(e) => upd("hero.h1", e.target.value)} className={inputCls} data-testid="ida-hero-h1" /></div>
                <div><label className="text-[10px] font-bold uppercase text-slate-400">Subtitlu hero</label>
                  <textarea rows={2} value={content.hero.subtitle} onChange={(e) => upd("hero.subtitle", e.target.value)} className={inputCls} data-testid="ida-hero-sub" /></div>
                <div><label className="text-[10px] font-bold uppercase text-slate-400">Imagine hero (URL)</label>
                  <input value={content.hero.image} onChange={(e) => upd("hero.image", e.target.value)} className={inputCls} data-testid="ida-hero-img" /></div>
              </div>
              <div className="space-y-3">
                <div><label className="text-[10px] font-bold uppercase text-slate-400">Meta Title (SEO)</label>
                  <input value={content.seo.title} onChange={(e) => upd("seo.title", e.target.value)} className={inputCls} data-testid="ida-seo-title" /></div>
                <div><label className="text-[10px] font-bold uppercase text-slate-400">Meta Description</label>
                  <textarea rows={3} value={content.seo.description} onChange={(e) => upd("seo.description", e.target.value)} className={inputCls} data-testid="ida-seo-desc" /></div>
                <div className="text-[11px] text-slate-400">Keywords ({content.seo.keywords?.length}): {content.seo.keywords?.slice(0, 8).join(", ")}… · FAQ: {content.faq?.length} · Articol SEO: {content.seo_article?.length} secțiuni (editabile via API)</div>
              </div>
            </div>
          </AdminCard>

          <AdminCard title={`Lead-uri (${leads?.total ?? 0})`} action={<DSButton variant="ghost" icon={RefreshCw} onClick={load} data-testid="ida-refresh">Refresh</DSButton>} testid="ida-leads">
            {!leads?.leads?.length && <EmptyState icon={Sofa} title="Niciun lead încă" hint="Lead-urile din formularul public apar aici + notificare in-app." />}
            <div className="space-y-2">
              {(leads?.leads || []).map((l) => (
                <div key={l.id} className="p-3 rounded-xl border border-slate-200 dark:border-slate-700 flex flex-wrap items-center gap-3" data-testid={`ida-lead-${l.id}`}>
                  <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded text-white ${STATUS_CLS[l.status]}`}>{STATUS[l.status]}</span>
                  <div className="flex-1 min-w-[200px]">
                    <div className="text-sm font-bold text-slate-900 dark:text-white">{l.name} <span className="font-normal text-slate-400">· {l.email} {l.phone ? `· ${l.phone}` : ""}</span></div>
                    <div className="text-xs text-slate-500">{l.lead_type} · {l.style || "—"} · {l.budget || "—"} · {l.surface_mp ? `${l.surface_mp}mp` : "—"} · {l.city || "—"} {l.rooms ? `· ${l.rooms}` : ""}</div>
                    {l.message && <div className="text-xs text-slate-400 italic mt-0.5">"{l.message}"</div>}
                  </div>
                  <div className="flex gap-1">
                    {Object.keys(STATUS).map((s) => (
                      <button key={s} disabled={l.status === s} onClick={() => setLeadStatus(l.id, s)}
                        className={`text-[9px] font-bold px-2 py-1 rounded ${l.status === s ? `${STATUS_CLS[s]} text-white` : "bg-slate-100 dark:bg-slate-700 text-slate-500"}`}
                        data-testid={`ida-lead-${l.id}-${s}`}>{STATUS[s]}</button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </AdminCard>
        </div>
      )}
    </AdminLayoutMetronic>
  );
}
