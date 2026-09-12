import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  Layers, ArrowLeft, Save, Lock, ShieldCheck, Gauge, Trophy, Languages, Loader2, Check,
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const LevelPills = ({ levels, value, onChange }) => (
  <div className="flex gap-1">
    {levels.map(l => (
      <button key={l.id} onClick={() => onChange(l.id)} data-testid={`cap-level-${l.id}`}
        className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${value === l.id ? "bg-slate-900 text-white border-slate-900" : "border-slate-200 text-slate-400 hover:border-slate-400"}`}>
        {l.label}
      </button>
    ))}
  </div>
);

export default function CapabilityEditorPage() {
  const [catalog, setCatalog] = useState(null);
  const [mine, setMine] = useState(null);
  const [selected, setSelected] = useState({});
  const [software, setSoftware] = useState([]);
  const [langs, setLangs] = useState([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/capabilities/catalog`),
      axios.get(`${API}/professional/capabilities`),
    ]).then(([c, m]) => {
      setCatalog(c.data); setMine(m.data);
      setSelected(Object.fromEntries((m.data.capabilities || []).map(x => [x.id, x.level])));
      setSoftware((m.data.software || []).map(s => s.id));
      setLangs(m.data.languages || []);
    }).catch(() => setErr("Nu am putut încărca catalogul."));
  }, []);

  const nSelected = useMemo(() => Object.keys(selected).length, [selected]);

  const toggleCap = (id) => setSelected(s => {
    const n = { ...s };
    if (n[id]) delete n[id]; else n[id] = "professional";
    return n;
  });
  const toggleSoft = (id) => setSoftware(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);
  const toggleLang = (l) => setLangs(s => s.includes(l) ? s.filter(x => x !== l) : [...s, l]);

  const save = async () => {
    setSaving(true); setErr(""); setSaved(false);
    try {
      const r = await axios.put(`${API}/professional/capabilities`, {
        capabilities: Object.entries(selected).map(([id, level]) => ({ id, level })),
        software, languages: langs,
      });
      setMine(r.data); setSaved(true); setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Salvarea a eșuat.");
    } finally { setSaving(false); }
  };

  if (!catalog || !mine) return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center">
      {err ? <div className="text-sm text-red-500">{err}</div> : <Loader2 className="w-6 h-6 animate-spin text-slate-400" />}
    </div>
  );

  const comp = mine.compatibility || {};
  const prog = mine.progression || {};
  return (
    <div className="min-h-screen bg-slate-50" data-testid="capability-editor-page">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <Link to="/specialist" className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-slate-800" data-testid="cap-back">
          <ArrowLeft className="w-3.5 h-3.5" /> Înapoi la dashboard
        </Link>
        <div className="mt-3 flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 flex items-center gap-2">
              <Layers className="w-6 h-6 text-slate-700" /> Capabilitățile mele
            </h1>
            <p className="mt-1 text-sm text-slate-500 max-w-xl">
              Alege DOAR serviciile pe care le stăpânești cu adevărat. Clienții văd exact ce oferi,
              iar AI-ul te recomandă pe compatibilitate — nu pe promisiuni.
            </p>
          </div>
          <button onClick={save} disabled={saving} data-testid="cap-save-btn"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-slate-900 text-white text-sm font-bold disabled:opacity-60">
            {saved ? <Check className="w-4 h-4 text-[#d4ff3a]" /> : <Save className="w-4 h-4" />}
            {saving ? "Se salvează…" : saved ? "Salvat!" : "Salvează"}
          </button>
        </div>
        {err && <div className="mt-3 text-xs font-bold text-red-500" data-testid="cap-error">{err}</div>}

        <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="rounded-3xl bg-white border border-slate-200 p-5" data-testid="cap-score-card">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-500"><Gauge className="w-4 h-4" /> COMPATIBILITY SCORE</div>
            <div className="mt-1 flex items-end gap-2">
              <span className="text-4xl font-black text-slate-900" data-testid="cap-score-value">{comp.score ?? 0}</span>
              <span className="text-sm text-slate-400 mb-1">/ 100 · căutabil de clienți</span>
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {(comp.badges || []).map(b => (
                <span key={b.id} data-testid={`cap-badge-${b.id}`}
                  className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${b.earned ? "bg-[#d4ff3a]/20 border-[#d4ff3a] text-slate-900" : "border-slate-200 text-slate-300"}`}>
                  {b.label} {b.earned ? "✓" : ""}
                </span>
              ))}
            </div>
          </div>
          <div className="rounded-3xl bg-white border border-slate-200 p-5" data-testid="cap-progression-card">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-500"><Trophy className="w-4 h-4" /> NIVELUL TĂU ÎN ECOSISTEM</div>
            <div className="mt-1 text-2xl font-black text-slate-900" data-testid="cap-level-name">
              Nivel {prog.level}/7 · {prog.name}
            </div>
            {(prog.next_requirements || []).length > 0 && (
              <div className="mt-2 space-y-1">
                <div className="text-[10px] font-bold uppercase text-slate-400">Pentru nivelul următor:</div>
                {prog.next_requirements.map((r, i) => (
                  <div key={i} className={`text-xs ${r.met ? "text-green-600" : "text-slate-500"}`}>
                    {r.met ? "✓" : "○"} {r.label}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {catalog.phases.map(ph => (
          <section key={ph.id} className="mt-6" data-testid={`cap-phase-${ph.id}`}>
            <h2 className="text-sm font-black text-slate-700">{ph.label}</h2>
            <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
              {ph.capabilities.map(c => c.reserved ? (
                <div key={c.id} className="rounded-2xl border border-slate-200 bg-slate-100/60 px-4 py-3 flex items-center gap-2 opacity-70" data-testid={`cap-reserved-${c.id}`}>
                  <Lock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="text-sm font-bold text-slate-500 flex-1">{c.label}</span>
                  <span className="text-[9px] font-black uppercase tracking-wide bg-slate-900 text-[#d4ff3a] px-2 py-0.5 rounded-full">PropManage</span>
                </div>
              ) : (
                <div key={c.id}
                  className={`rounded-2xl border px-4 py-3 cursor-pointer transition-colors ${selected[c.id] ? "border-slate-900 bg-white shadow-sm" : "border-slate-200 bg-white hover:border-slate-400"}`}
                  onClick={() => toggleCap(c.id)} data-testid={`cap-item-${c.id}`}>
                  <div className="flex items-center gap-2">
                    <span className={`w-4 h-4 rounded-md border flex items-center justify-center shrink-0 ${selected[c.id] ? "bg-slate-900 border-slate-900" : "border-slate-300"}`}>
                      {selected[c.id] && <Check className="w-3 h-3 text-[#d4ff3a]" />}
                    </span>
                    <span className="text-sm font-bold text-slate-800 flex-1">{c.label}</span>
                  </div>
                  {selected[c.id] && (
                    <div className="mt-2 pl-6" onClick={e => e.stopPropagation()}>
                      <LevelPills levels={catalog.levels} value={selected[c.id]}
                        onChange={lv => setSelected(s => ({ ...s, [c.id]: lv }))} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        ))}

        <section className="mt-8" data-testid="cap-software-section">
          <h2 className="text-sm font-black text-slate-700 flex items-center gap-2"><ShieldCheck className="w-4 h-4" /> Software & formate stăpânite</h2>
          <p className="text-xs text-slate-400 mt-0.5">Selecțiile calculează automat Compatibility Score-ul (BIM, IFC, Digital Twin, Matterport…).</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {catalog.software.map(s => (
              <button key={s.id} onClick={() => toggleSoft(s.id)} data-testid={`cap-soft-${s.id}`}
                className={`px-3 py-1.5 rounded-full text-xs font-bold border ${software.includes(s.id) ? "bg-slate-900 text-white border-slate-900" : "bg-white border-slate-200 text-slate-500 hover:border-slate-400"}`}>
                {s.label}
              </button>
            ))}
          </div>
        </section>

        <section className="mt-6 pb-16" data-testid="cap-languages-section">
          <h2 className="text-sm font-black text-slate-700 flex items-center gap-2"><Languages className="w-4 h-4" /> Limbi vorbite</h2>
          <div className="mt-2 flex flex-wrap gap-2">
            {catalog.languages.map(l => (
              <button key={l} onClick={() => toggleLang(l)} data-testid={`cap-lang-${l}`}
                className={`px-3 py-1.5 rounded-full text-xs font-bold border ${langs.includes(l) ? "bg-slate-900 text-white border-slate-900" : "bg-white border-slate-200 text-slate-500 hover:border-slate-400"}`}>
                {l}
              </button>
            ))}
          </div>
          <div className="mt-6 text-xs text-slate-400">
            {nSelected} capabilități selectate · Serviciile marcate <Lock className="w-3 h-3 inline" /> (Audit, Cartografiere instalații,
            Infrastructură Digital Twin, Management construcție, Inspecție calitate, Recepție finală, House Health)
            rămân responsabilitatea PropManage — ecosistemul garantează calitatea lor.
          </div>
        </section>
      </div>
    </div>
  );
}
