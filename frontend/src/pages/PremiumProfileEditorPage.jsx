// Sprint D — Premium Profile Editor for Nivel 3 (PREMIUM tier) specialists.
import React, { useEffect, useState } from "react";
import axios from "axios";
import { DashLayout } from "./DashShared";
import {
  Crown, Plus, Trash2, Save, Loader2, AlertTriangle, CheckCircle2,
  Camera, Award, Users, Globe, Clock, Phone, Video,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

export const PremiumProfileEditorPage = () => {
  const [state, setState] = useState({ tier: null, is_premium_eligible: false, premium_profile: {} });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const load = () => {
    setLoading(true);
    axios.get(`${API}/api/me/premium-profile`).then(r => setState(r.data)).catch(() => setMsg("Nu am putut încărca profilul. Reîncearcă.")).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const update = (key, val) => setState(s => ({ ...s, premium_profile: { ...s.premium_profile, [key]: val } }));

  const save = async () => {
    setSaving(true); setMsg("");
    try {
      await axios.put(`${API}/api/me/premium-profile`, state.premium_profile);
      setMsg("Salvat — profilul tău Premium e actualizat public.");
      load();
    } catch (e) {
      setMsg(`Eroare: ${e?.response?.data?.detail || e.message}`);
    } finally { setSaving(false); }
  };

  if (loading) {
    return <DashLayout role="specialist" title="Profil Premium"><Loader2 className="w-6 h-6 animate-spin text-[#d4ff3a]" /></DashLayout>;
  }

  const p = state.premium_profile || {};

  return (
    <DashLayout role="specialist" title="Profil Premium">
      {!state.is_premium_eligible && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-5 mb-6" data-testid="not-premium-warning">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-300 mt-0.5" />
            <div>
              <h3 className="font-semibold text-amber-200 mb-1">Profilul Premium e vizibil DOAR pentru tier PREMIUM (Nivel 3)</h3>
              <p className="text-xs text-amber-100/80">
                Tier-ul tău actual: <strong>{state.tier || "ENTRY"}</strong>. Poți completa profilul acum — devine vizibil când treci la PREMIUM (50+ joburi, rating ≥4.7, 25+ recenzii).
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-6" data-testid="premium-editor">
        <Section icon={Crown} title="Despre tine (extended bio)" testid="section-bio">
          <textarea value={p.bio_extended || ""} onChange={e => update("bio_extended", e.target.value)} rows={5} maxLength={3000}
            placeholder="Prezentare completă: experiență, abordare, specializări, valori..."
            className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm resize-none" data-testid="bio-extended" />
          <div className="text-[10px] text-stone-500 text-right">{(p.bio_extended || "").length}/3000</div>
        </Section>

        <Section icon={Camera} title="Portofoliu foto (max 12 imagini)" testid="section-portfolio">
          <ListEditor
            items={p.portfolio_images || []}
            onChange={v => update("portfolio_images", v)}
            placeholder="https://exemplu.com/foto.jpg"
            maxItems={12}
            testid="portfolio"
            simple
          />
        </Section>

        <Section icon={Award} title="Servicii detaliate" testid="section-services">
          <ListEditor
            items={p.services_detailed || []}
            onChange={v => update("services_detailed", v)}
            template={{ name: "", description: "", price_range: "", duration: "" }}
            fields={[
              { key: "name", label: "Nume serviciu", required: true },
              { key: "description", label: "Descriere", textarea: true },
              { key: "price_range", label: "Interval preț (ex: 500-1500 RON)" },
              { key: "duration", label: "Durată (ex: 1-3 zile)" },
            ]}
            maxItems={20}
            testid="services"
          />
        </Section>

        <Section icon={Award} title="Certificări / Atestate" testid="section-certs">
          <ListEditor
            items={p.certifications || []}
            onChange={v => update("certifications", v)}
            template={{ name: "", issuer: "", year: null }}
            fields={[
              { key: "name", label: "Denumire", required: true },
              { key: "issuer", label: "Emitent" },
              { key: "year", label: "An", type: "number" },
            ]}
            maxItems={15}
            testid="certs"
          />
        </Section>

        <Section icon={Users} title="Echipă" testid="section-team">
          <ListEditor
            items={p.team_members || []}
            onChange={v => update("team_members", v)}
            template={{ name: "", role: "", experience_years: null }}
            fields={[
              { key: "name", label: "Nume", required: true },
              { key: "role", label: "Rol" },
              { key: "experience_years", label: "Ani experiență", type: "number" },
            ]}
            maxItems={10}
            testid="team"
          />
        </Section>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Section icon={Globe} title="Limbi vorbite" testid="section-langs">
            <ListEditor
              items={p.languages || []}
              onChange={v => update("languages", v)}
              placeholder="Română, Engleză..."
              maxItems={8}
              testid="langs"
              simple
            />
          </Section>

          <Section icon={Clock} title="Timp răspuns țintă" testid="section-response">
            <input type="number" min="1" max="168" value={p.response_time_target_hours || ""}
              onChange={e => update("response_time_target_hours", parseInt(e.target.value) || null)}
              placeholder="2"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="response-time" />
            <div className="text-[10px] text-stone-500 mt-1">ore (max 168 = 1 săptămână)</div>
          </Section>

          <Section icon={Phone} title="Urgențe" testid="section-emergency">
            <label className="flex items-center gap-2 cursor-pointer pt-2">
              <input type="checkbox" checked={!!p.accepts_emergency_calls}
                onChange={e => update("accepts_emergency_calls", e.target.checked)}
                className="w-4 h-4 accent-[#d4ff3a]" data-testid="accepts-emergency" />
              <span className="text-sm text-stone-200">Accept apeluri urgență 24/7</span>
            </label>
          </Section>
        </div>

        <Section icon={Video} title="Video prezentare (link YouTube/Vimeo)" testid="section-video">
          <input type="url" value={p.showcase_video_url || ""} onChange={e => update("showcase_video_url", e.target.value)}
            placeholder="https://youtube.com/watch?v=..."
            className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm" data-testid="showcase-video" />
        </Section>

        <div className="sticky bottom-4 flex items-center gap-3 bg-[#0a0a0b]/95 backdrop-blur-xl border border-white/10 rounded-2xl p-4 shadow-2xl">
          <button onClick={save} disabled={saving} className="btn-accent px-6 py-3 rounded-xl text-sm font-semibold flex items-center gap-2 disabled:opacity-50" data-testid="premium-save">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salvează profilul Premium
          </button>
          {msg && (
            <div className="text-sm flex items-center gap-2" data-testid="premium-save-msg">
              {msg.startsWith("Eroare") ? <span className="text-red-300">{msg}</span> : <><CheckCircle2 className="w-4 h-4 text-emerald-300" /><span className="text-emerald-300">{msg}</span></>}
            </div>
          )}
        </div>
      </div>
    </DashLayout>
  );
};


const Section = ({ icon: Icon, title, children, testid }) => (
  <div className="glass rounded-2xl p-5" data-testid={testid}>
    <div className="flex items-center gap-2 mb-3">
      <Icon className="w-4 h-4 text-[#d4ff3a]" />
      <h3 className="font-serif text-lg">{title}</h3>
    </div>
    {children}
  </div>
);


const ListEditor = ({ items, onChange, template, fields, placeholder, maxItems, testid, simple }) => {
  const add = () => {
    if (items.length >= maxItems) return;
    onChange([...items, simple ? "" : { ...template }]);
  };
  const remove = (i) => onChange(items.filter((_, idx) => idx !== i));
  const update = (i, key, val) => {
    const next = [...items];
    if (simple) next[i] = val;
    else next[i] = { ...next[i], [key]: val };
    onChange(next);
  };

  return (
    <div className="space-y-2" data-testid={`list-${testid}`}>
      {items.length === 0 && <div className="text-xs text-stone-500 italic">Niciun element. Adaugă mai jos.</div>}
      {items.map((item, i) => (
        <div key={i} className="flex items-start gap-2 bg-white/3 rounded-xl p-2.5" data-testid={`list-${testid}-item-${i}`}>
          <div className="flex-1 space-y-1.5">
            {simple ? (
              <input type="text" value={item} onChange={e => update(i, null, e.target.value)} placeholder={placeholder}
                className="w-full bg-white/5 border border-white/10 rounded-md px-2 py-1.5 text-xs" />
            ) : (
              fields.map(f => f.textarea ? (
                <textarea key={f.key} value={item[f.key] || ""} onChange={e => update(i, f.key, e.target.value)} placeholder={f.label} rows={2}
                  className="w-full bg-white/5 border border-white/10 rounded-md px-2 py-1.5 text-xs resize-none" />
              ) : (
                <input key={f.key} type={f.type || "text"} value={item[f.key] || ""}
                  onChange={e => update(i, f.key, f.type === "number" ? (parseInt(e.target.value) || null) : e.target.value)}
                  placeholder={f.label}
                  className="w-full bg-white/5 border border-white/10 rounded-md px-2 py-1.5 text-xs" />
              ))
            )}
          </div>
          <button onClick={() => remove(i)} className="text-red-400 hover:bg-red-500/10 rounded-md p-1.5" data-testid={`list-${testid}-remove-${i}`}><Trash2 className="w-3.5 h-3.5" /></button>
        </div>
      ))}
      {items.length < maxItems && (
        <button onClick={add} className="w-full py-2 rounded-lg text-xs bg-white/5 hover:bg-white/10 flex items-center justify-center gap-1.5" data-testid={`list-${testid}-add`}>
          <Plus className="w-3.5 h-3.5" /> Adaugă ({items.length}/{maxItems})
        </button>
      )}
    </div>
  );
};

export default PremiumProfileEditorPage;
