// CMS text editor + Email templates editor + Zones manager
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Search, Save, RotateCcw, Plus, Trash2, Eye, X, Power } from "lucide-react";
import { AdminCard, AdminBtn } from "./AdminLayoutMetronic";
import { API } from "../DashShared";

// ============= CMS TEXTS =============
export const AdminCMS = () => {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [edits, setEdits] = useState({}); // key -> new value
  const [expiryEdits, setExpiryEdits] = useState({}); // key -> new expires_at
  const [saving, setSaving] = useState({});
  const [loaded, setLoaded] = useState(false);
  const [showEn, setShowEn] = useState(false); // bilingual edit mode

  const load = () => axios.get(`${API}/admin/cms`).then(r => { setItems(r.data); setLoaded(true); }).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async (key) => {
    const value = edits[key];
    const expiresEdit = expiryEdits[key];
    const valueChanged = value !== undefined;
    const expiryChanged = expiresEdit !== undefined;
    if (!valueChanged && !expiryChanged) return;
    setSaving(s => ({ ...s, [key]: true }));
    try {
      const it = items.find(i => i.key === key);
      const body = { key, value: valueChanged ? value : (it?.value || "") };
      if (expiryChanged) {
        // Convert "datetime-local" format → ISO with offset → backend uses UTC; we send local interpreted as UTC for simplicity
        body.expires_at = expiresEdit ? new Date(expiresEdit).toISOString() : "";
      }
      await axios.put(`${API}/admin/cms`, body);
      setEdits(e => { const n = { ...e }; delete n[key]; return n; });
      setExpiryEdits(e => { const n = { ...e }; delete n[key]; return n; });
      await load();
    } finally {
      setSaving(s => { const n = { ...s }; delete n[key]; return n; });
    }
  };

  const reset = async (key) => {
    if (!window.confirm("Resetează la valoarea default?")) return;
    await axios.delete(`${API}/admin/cms/${encodeURIComponent(key)}`);
    setEdits(e => { const n = { ...e }; delete n[key]; return n; });
    load();
  };

  const filtered = items.filter(it =>
    !it.key.endsWith(":en") && (
      !q ||
      it.key.toLowerCase().includes(q.toLowerCase()) ||
      (it.value || "").toLowerCase().includes(q.toLowerCase())
    )
  );

  const itemsByKey = items.reduce((acc, it) => { acc[it.key] = it; return acc; }, {});

  const grouped = filtered.reduce((acc, it) => {
    const ns = it.key.split(".")[0];
    (acc[ns] = acc[ns] || []).push(it);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      <AdminCard>
        <div className="flex flex-wrap gap-3 items-center">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="Caută cheie sau text..."
              className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
              data-testid="cms-search"
            />
          </div>
          <button
            onClick={() => setShowEn(!showEn)}
            className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
              showEn
                ? "border-blue-400 bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:border-blue-500/50 dark:text-blue-300"
                : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
            }`}
            data-testid="cms-toggle-en"
            title="Editează în paralel versiunea EN (engleză)"
          >
            🌍 {showEn ? "Bilingv ✓" : "Editor EN"}
          </button>
          <span className="text-xs text-slate-500">{filtered.length} / {items.filter(i => !i.key.endsWith(":en")).length} texte</span>
        </div>
      </AdminCard>

      {!loaded && <div className="text-center text-slate-500 py-12">Se încarcă...</div>}

      {Object.entries(grouped).map(([ns, list]) => (
        <AdminCard key={ns} title={`Namespace: ${ns}`} testid={`cms-group-${ns}`}>
          <div className="space-y-3">
            {list.map(it => {
              const current = edits[it.key] !== undefined ? edits[it.key] : it.value;
              const dirty = edits[it.key] !== undefined && edits[it.key] !== it.value;
              const supportsExpiry = it.key === "landing.promo_banner";
              const expiryCurrent = expiryEdits[it.key] !== undefined ? expiryEdits[it.key] :
                (it.expires_at ? it.expires_at.slice(0, 16) : "");
              const expiryDirty = expiryEdits[it.key] !== undefined;
              const isExpired = it.expires_at && it.expires_at <= new Date().toISOString();
              const fullDirty = dirty || expiryDirty;
              return (
                <div key={it.key} className="grid grid-cols-1 md:grid-cols-[280px_1fr_auto] gap-3 items-start" data-testid={`cms-row-${it.key}`}>
                  <div>
                    <div className="font-mono text-xs text-slate-600 dark:text-slate-300 break-all">{it.key}</div>
                    {it.is_overridden && <span className="text-[9px] uppercase tracking-wider text-amber-600 dark:text-amber-400">Modificat</span>}
                    {isExpired && <span className="text-[9px] uppercase tracking-wider text-red-600 dark:text-red-400 ml-1">Expirat</span>}
                    {it.expires_at && !isExpired && <span className="text-[9px] uppercase tracking-wider text-blue-600 dark:text-blue-400 ml-1">Programat</span>}
                  </div>
                  <div className="space-y-2">
                    <textarea
                      value={current}
                      onChange={e => setEdits(s => ({ ...s, [it.key]: e.target.value }))}
                      rows={Math.min(6, Math.max(1, Math.ceil((current || "").length / 80)))}
                      className={`w-full px-3 py-2 rounded-lg border text-sm font-medium bg-white dark:bg-slate-800 ${dirty ? "border-amber-400 dark:border-amber-600" : "border-slate-200 dark:border-slate-700"}`}
                      data-testid={`cms-input-${it.key}`}
                    />
                    {showEn && (() => {
                      const enKey = `${it.key}:en`;
                      const enItem = itemsByKey[enKey];
                      const enValue = edits[enKey] !== undefined ? edits[enKey] : (enItem?.value || "");
                      const enDirty = edits[enKey] !== undefined && edits[enKey] !== (enItem?.value || "");
                      return (
                        <div className="flex gap-2 items-start">
                          <div className="text-[10px] uppercase tracking-wider font-bold text-blue-600 dark:text-blue-400 mt-2 shrink-0 w-8">EN</div>
                          <textarea
                            value={enValue}
                            onChange={e => setEdits(s => ({ ...s, [enKey]: e.target.value }))}
                            rows={Math.min(6, Math.max(1, Math.ceil((enValue || "").length / 80)))}
                            className={`flex-1 px-3 py-2 rounded-lg border text-sm bg-blue-50/30 dark:bg-blue-500/5 ${enDirty ? "border-amber-400 dark:border-amber-600" : "border-blue-200 dark:border-blue-500/30"}`}
                            data-testid={`cms-input-${enKey}`}
                            placeholder={`English translation (fallback: RO value)`}
                          />
                          {enDirty && (
                            <AdminBtn variant="primary" onClick={() => save(enKey)} disabled={saving[enKey]} data-testid={`cms-save-${enKey}`}>
                              <Save className="w-3.5 h-3.5" />
                            </AdminBtn>
                          )}
                          {enItem?.is_overridden && !enDirty && (
                            <AdminBtn variant="ghost" onClick={() => reset(enKey)} title="Reset EN" data-testid={`cms-reset-${enKey}`}>
                              <RotateCcw className="w-3.5 h-3.5" />
                            </AdminBtn>
                          )}
                        </div>
                      );
                    })()}
                    {supportsExpiry && (
                      <div className="flex items-center gap-2 flex-wrap text-xs">
                        <label className="flex items-center gap-2">
                          <span className="text-slate-500">⏰ Expiră la:</span>
                          <input
                            type="datetime-local"
                            value={expiryCurrent}
                            onChange={e => setExpiryEdits(s => ({ ...s, [it.key]: e.target.value }))}
                            className={`px-2 py-1 rounded-md border text-xs bg-white dark:bg-slate-800 ${expiryDirty ? "border-amber-400" : "border-slate-200 dark:border-slate-700"}`}
                            data-testid={`cms-expiry-${it.key}`}
                          />
                        </label>
                        {expiryCurrent && (
                          <button
                            onClick={() => setExpiryEdits(s => ({ ...s, [it.key]: "" }))}
                            className="text-xs text-slate-500 hover:text-red-500 underline"
                            data-testid={`cms-expiry-clear-${it.key}`}
                          >Elimină dată</button>
                        )}
                        <span className="text-[10px] text-slate-400">După această dată, banner-ul dispare automat pentru public.</span>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <AdminBtn variant={fullDirty ? "primary" : "secondary"} onClick={() => save(it.key)} disabled={!fullDirty || saving[it.key]} data-testid={`cms-save-${it.key}`}>
                      <Save className="w-3.5 h-3.5" />
                    </AdminBtn>
                    {it.is_overridden && (
                      <AdminBtn variant="ghost" onClick={() => reset(it.key)} title="Reset la default" data-testid={`cms-reset-${it.key}`}>
                        <RotateCcw className="w-3.5 h-3.5" />
                      </AdminBtn>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </AdminCard>
      ))}
    </div>
  );
};

// ============= EMAIL TEMPLATES =============
export const AdminEmailTemplates = () => {
  const [items, setItems] = useState([]);
  const [active, setActive] = useState(null);
  const [edit, setEdit] = useState({ subject: "", html: "" });
  const [saving, setSaving] = useState(false);

  const load = () => axios.get(`${API}/admin/email-templates`).then(r => setItems(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const open = (it) => { setActive(it); setEdit({ subject: it.subject, html: it.html }); };

  const save = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/admin/email-templates/${active.id}`, edit);
      await load();
      setActive(null);
    } finally { setSaving(false); }
  };

  const reset = async () => {
    if (!window.confirm("Reset la template default?")) return;
    await axios.delete(`${API}/admin/email-templates/${active.id}`);
    await load();
    setActive(null);
  };

  return (
    <div className="space-y-4">
      <AdminCard title="Template-uri Email" testid="email-templates-card">
        <div className="space-y-2">
          {items.map(it => (
            <div key={it.id} className="flex items-center justify-between p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50" data-testid={`tpl-row-${it.id}`}>
              <div className="flex-1 min-w-0">
                <div className="font-medium">{it.id}</div>
                <div className="text-xs text-slate-500 truncate">{it.subject}</div>
              </div>
              {it.is_overridden && <span className="text-[9px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400 mr-2">Modificat</span>}
              <AdminBtn onClick={() => open(it)} data-testid={`tpl-edit-${it.id}`}>Editează</AdminBtn>
            </div>
          ))}
        </div>
      </AdminCard>

      {active && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={() => setActive(null)}>
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6" onClick={e => e.stopPropagation()} data-testid="tpl-modal">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Editare: {active.id}</h3>
              <button onClick={() => setActive(null)}><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">Subiect</label>
                <input value={edit.subject} onChange={e => setEdit({ ...edit, subject: e.target.value })} className="w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800" data-testid="tpl-subject" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400">HTML (folosește {`{{name}}, {{amount}}`} etc.)</label>
                <textarea value={edit.html} onChange={e => setEdit({ ...edit, html: e.target.value })} rows={12} className="w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 font-mono text-xs" data-testid="tpl-html" />
              </div>
              <details className="text-sm">
                <summary className="cursor-pointer text-slate-500 dark:text-slate-400">Preview HTML</summary>
                <div className="mt-2 p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" dangerouslySetInnerHTML={{ __html: edit.html }} />
              </details>
            </div>
            <div className="flex justify-between gap-2 mt-6">
              {active.is_overridden ? <AdminBtn variant="ghost" onClick={reset}><RotateCcw className="w-3.5 h-3.5 inline mr-1" /> Reset default</AdminBtn> : <span />}
              <div className="flex gap-2">
                <AdminBtn variant="secondary" onClick={() => setActive(null)}>Anulează</AdminBtn>
                <AdminBtn onClick={save} disabled={saving} data-testid="tpl-save">{saving ? "..." : "Salvează"}</AdminBtn>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ============= ZONES =============
export const AdminZones = () => {
  const [zones, setZones] = useState([]);
  const [q, setQ] = useState("");
  const [form, setForm] = useState({ country: "România", city: "", zone: "" });
  const [adding, setAdding] = useState(false);

  const load = () => axios.get(`${API}/admin/zones`).then(r => setZones(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!form.city || !form.zone) return;
    setAdding(true);
    try {
      await axios.post(`${API}/admin/zones`, form);
      setForm({ country: "România", city: "", zone: "" });
      await load();
    } catch (e) {
      alert(e?.response?.data?.detail || "Eroare");
    } finally { setAdding(false); }
  };

  const toggle = async (z) => {
    if (z.source === "custom") {
      if (!window.confirm(`Șterge zona custom "${z.city} - ${z.zone}"?`)) return;
      await axios.delete(`${API}/admin/zones/custom/${z.id}`);
    } else {
      await axios.post(`${API}/admin/zones/toggle`, { country: z.country, city: z.city, zone: z.zone });
    }
    load();
  };

  const filtered = zones.filter(z =>
    !q ||
    z.city.toLowerCase().includes(q.toLowerCase()) ||
    z.zone.toLowerCase().includes(q.toLowerCase())
  );

  const byCity = filtered.reduce((acc, z) => {
    (acc[z.city] = acc[z.city] || []).push(z);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      <AdminCard title="Adaugă zonă custom" testid="add-zone-card">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <input value={form.country} onChange={e => setForm({ ...form, country: e.target.value })} placeholder="Țară" className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="zone-country" />
          <input value={form.city} onChange={e => setForm({ ...form, city: e.target.value })} placeholder="Oraș (ex: Brașov)" className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="zone-city" />
          <input value={form.zone} onChange={e => setForm({ ...form, zone: e.target.value })} placeholder="Zonă (ex: Răcădău)" className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="zone-name" />
          <AdminBtn onClick={add} disabled={adding || !form.city || !form.zone} data-testid="zone-add"><Plus className="w-3.5 h-3.5 inline mr-1" /> Adaugă</AdminBtn>
        </div>
      </AdminCard>

      <AdminCard>
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Caută oraș sau zonă..." className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm" data-testid="zones-search" />
        </div>
        <div className="text-xs text-slate-500 mt-2">{filtered.length} zone afișate · {zones.filter(z => z.disabled).length} dezactivate · {zones.filter(z => z.source === "custom").length} custom</div>
      </AdminCard>

      {Object.entries(byCity).map(([city, list]) => (
        <AdminCard key={city} title={city} testid={`zones-city-${city}`}>
          <div className="flex flex-wrap gap-2">
            {list.map((z, i) => (
              <button
                key={`${z.source}-${z.id || i}-${z.zone}`}
                onClick={() => toggle(z)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                  z.disabled
                    ? "bg-slate-100 text-slate-400 border-slate-200 dark:bg-slate-800 dark:text-slate-600 line-through"
                    : z.source === "custom"
                      ? "bg-violet-100 text-violet-700 border-violet-200 dark:bg-violet-500/10 dark:text-violet-400 hover:bg-violet-200"
                      : "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 hover:bg-emerald-100"
                }`}
                title={z.source === "custom" ? "Custom — click pentru ștergere" : z.disabled ? "Dezactivată — click pentru activare" : "Activă — click pentru dezactivare"}
                data-testid={`zone-${z.city}-${z.zone}`}
              >
                {z.zone}
                {z.source === "custom" && <Trash2 className="w-3 h-3 inline ml-1" />}
                {z.disabled && <Power className="w-3 h-3 inline ml-1" />}
              </button>
            ))}
          </div>
        </AdminCard>
      ))}
    </div>
  );
};
