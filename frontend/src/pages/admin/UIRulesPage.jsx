import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Plus, Trash2, Save, Power, ShieldCheck } from "lucide-react";
import { AdminLayoutMetronic } from "./AdminLayoutMetronic";

const API = process.env.REACT_APP_BACKEND_URL;

const FIELDS = [
  { value: "role", label: "Rol utilizator" },
  { value: "verified", label: "Identitate verificată" },
  { value: "projects_completed", label: "Proiecte finalizate" },
  { value: "account_age_days", label: "Vechime cont (zile)" },
];
const OPS = [
  { value: "eq", label: "este" },
  { value: "neq", label: "nu este" },
  { value: "gte", label: "≥" },
  { value: "lte", label: "≤" },
];
const WIDGETS_FALLBACK = ["hero", "quick_actions", "copilot", "contextual", "discover"];

const newRule = () => ({
  id: `r_${Date.now().toString(36)}`,
  name: "Regulă nouă",
  target_type: "menu",
  target_id: "",
  action: "hide",
  conditions: [{ field: "role", op: "eq", value: "client" }],
  active: true,
});

export default function UIRulesPage() {
  const [rules, setRules] = useState(null);
  const [menuIds, setMenuIds] = useState([]);
  const [widgetIds, setWidgetIds] = useState(WIDGETS_FALLBACK);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    axios.get(`${API}/api/admin/ui-rules`, { withCredentials: true }).then((r) => setRules(r.data.rules || [])).catch(() => toast.error("Nu am putut încărca regulile."));
    axios.get(`${API}/api/admin/xos/registry`, { withCredentials: true })
      .then((r) => setWidgetIds([...new Set((r.data.entries || []).map((e) => e.id))]))
      .catch(() => {});
    axios.get(`${API}/api/public/site-menu`).then((r) => {
      const ids = [];
      (r.data.items || []).forEach((it) => { ids.push(it.id); (it.children || []).forEach((c) => ids.push(c.id)); });
      setMenuIds(ids);
    }).catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const r = await axios.put(`${API}/api/admin/ui-rules`, { rules }, { withCredentials: true });
      setRules(r.data.rules);
      toast.success("Reguli salvate — se aplică instant.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la salvare.");
    } finally {
      setSaving(false);
    }
  };

  const upd = (i, patch) => setRules(rules.map((r, ri) => (ri === i ? { ...r, ...patch } : r)));

  return (
    <AdminLayoutMetronic title="XOS · Dynamic UI Rules" subtitle="DACĂ [condiție] ATUNCI [ascunde/arată] element — fără cod">
      <div className="max-w-4xl mx-auto space-y-4 p-4 sm:p-6" data-testid="ui-rules-page">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-slate-500">Ex: ascunde „Wallet" pentru juniori · arată „Marketplace" doar după verificare identitate · arată doar după N proiecte.</p>
          <div className="flex items-center gap-2 shrink-0">
            <button onClick={() => setRules([...(rules || []), newRule()])} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm border border-dashed border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800" data-testid="ui-rules-add">
              <Plus className="w-4 h-4" /> Regulă nouă
            </button>
            <button onClick={save} disabled={saving} className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-sm font-bold bg-lime-500 text-black hover:bg-lime-400 disabled:opacity-50" data-testid="ui-rules-save">
              <Save className="w-4 h-4" /> {saving ? "..." : "Salvează"}
            </button>
          </div>
        </div>

        {!rules ? <div className="text-slate-400 p-8">Se încarcă...</div> : rules.length === 0 ? (
          <div className="text-center py-12 text-slate-400 border border-dashed border-slate-200 dark:border-slate-700 rounded-2xl">
            <ShieldCheck className="w-8 h-8 mx-auto mb-2 opacity-40" />
            Nicio regulă încă. Adaugă prima regulă de vizibilitate.
          </div>
        ) : rules.map((r, i) => (
          <div key={r.id} className={`rounded-2xl border p-4 space-y-3 bg-white dark:bg-slate-900 ${r.active ? "border-slate-200 dark:border-slate-700" : "border-dashed opacity-60"}`} data-testid={`ui-rule-${r.id}`}>
            <div className="flex flex-wrap items-center gap-2">
              <input value={r.name} onChange={(e) => upd(i, { name: e.target.value })}
                className="font-bold text-sm bg-transparent border-b border-slate-200 dark:border-slate-700 px-1 py-0.5 flex-1 min-w-[160px]" data-testid={`ui-rule-name-${r.id}`} />
              <button onClick={() => upd(i, { active: !r.active })}
                className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold border ${r.active ? "text-lime-700 bg-lime-50 border-lime-300" : "text-slate-400 border-slate-200"}`}
                data-testid={`ui-rule-toggle-${r.id}`}>
                <Power className="w-3 h-3" /> {r.active ? "Activă" : "Inactivă"}
              </button>
              <button onClick={() => setRules(rules.filter((_, ri) => ri !== i))} className="p-1.5 rounded-lg hover:bg-red-50 text-red-400" data-testid={`ui-rule-del-${r.id}`}>
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-xs font-black uppercase text-slate-400">DACĂ</span>
              {r.conditions.map((c, ci) => (
                <div key={ci} className="flex items-center gap-1.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-1.5">
                  <select value={c.field} onChange={(e) => upd(i, { conditions: r.conditions.map((x, xi) => (xi === ci ? { ...x, field: e.target.value } : x)) })}
                    className="bg-transparent text-xs font-semibold" data-testid={`ui-rule-field-${r.id}-${ci}`}>
                    {FIELDS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
                  </select>
                  <select value={c.op} onChange={(e) => upd(i, { conditions: r.conditions.map((x, xi) => (xi === ci ? { ...x, op: e.target.value } : x)) })}
                    className="bg-transparent text-xs" data-testid={`ui-rule-op-${r.id}-${ci}`}>
                    {OPS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                  <input value={c.value ?? ""} onChange={(e) => upd(i, { conditions: r.conditions.map((x, xi) => (xi === ci ? { ...x, value: e.target.value } : x)) })}
                    className="w-20 bg-transparent text-xs border-b border-slate-300 dark:border-slate-600" placeholder="valoare" data-testid={`ui-rule-value-${r.id}-${ci}`} />
                  <button onClick={() => upd(i, { conditions: r.conditions.filter((_, xi) => xi !== ci) })} className="text-slate-400 hover:text-red-400"><Trash2 className="w-3 h-3" /></button>
                </div>
              ))}
              <button onClick={() => upd(i, { conditions: [...r.conditions, { field: "role", op: "eq", value: "" }] })}
                className="text-xs text-slate-400 hover:text-slate-600 inline-flex items-center gap-0.5"><Plus className="w-3 h-3" /> condiție</button>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-xs font-black uppercase text-slate-400">ATUNCI</span>
              <select value={r.action} onChange={(e) => upd(i, { action: e.target.value })}
                className="rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-1.5 text-xs font-semibold" data-testid={`ui-rule-action-${r.id}`}>
                <option value="hide">Ascunde</option>
                <option value="show_if">Arată doar dacă e îndeplinită condiția</option>
              </select>
              <select value={r.target_type} onChange={(e) => upd(i, { target_type: e.target.value, target_id: "" })}
                className="rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-1.5 text-xs" data-testid={`ui-rule-ttype-${r.id}`}>
                <option value="menu">Element meniu</option>
                <option value="widget">Widget dashboard client</option>
              </select>
              <select value={r.target_id} onChange={(e) => upd(i, { target_id: e.target.value })}
                className="rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-1.5 text-xs min-w-[140px]" data-testid={`ui-rule-tid-${r.id}`}>
                <option value="">— alege —</option>
                {(r.target_type === "menu" ? menuIds : widgetIds).map((id) => <option key={id} value={id}>{id}</option>)}
              </select>
            </div>
          </div>
        ))}
      </div>
    </AdminLayoutMetronic>
  );
}
