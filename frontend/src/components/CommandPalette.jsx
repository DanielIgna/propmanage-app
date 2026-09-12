// CommandPalette — Cmd/Ctrl+K global launcher for the Admin Console.
// Fuzzy filter, keyboard navigation, favorite toggle, recents.
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Search, Star, ArrowRight, Command, Clock, X } from "lucide-react";

const RECENT_KEY = "pm_admin_recent_items_v1";

const norm = (s) => (s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
const matchScore = (item, q) => {
  if (!q) return 0;
  const hay = norm(`${item.label} ${item._sectionTitle || ""} ${item.id}`);
  const needle = norm(q);
  if (!needle) return 0;
  if (hay.startsWith(needle)) return 100;
  if (hay.includes(needle)) return 50;
  // letter-by-letter fuzzy
  let h = 0, score = 0;
  for (const c of needle) {
    const idx = hay.indexOf(c, h);
    if (idx === -1) return 0;
    score += 1;
    h = idx + 1;
  }
  return score;
};

export const CommandPalette = ({ open, onClose, sections = [], favIds = [], onNavigate, onToggleFavorite }) => {
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef(null);

  // Flatten items across all visible sections
  const flat = useMemo(() => sections.flatMap(s =>
    s.items.map(it => ({ ...it, _sectionId: s.id, _sectionTitle: s.title }))
  ), [sections]);

  const recents = (() => {
    try { return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]"); } catch { return []; }
  })();

  // Filtered & ranked items
  const filtered = useMemo(() => {
    if (!q.trim()) {
      // Default view: favorites first, then recents, then full flat list
      const favItems = favIds.map(id => flat.find(it => it.id === id)).filter(Boolean).map(it => ({ ...it, _group: "Favorite" }));
      const recentItems = recents.map(id => flat.find(it => it.id === id))
        .filter(Boolean)
        .filter(it => !favIds.includes(it.id))
        .map(it => ({ ...it, _group: "Recent" }));
      const restItems = flat
        .filter(it => !favIds.includes(it.id) && !recents.includes(it.id))
        .map(it => ({ ...it, _group: it._sectionTitle }));
      return [...favItems, ...recentItems, ...restItems];
    }
    return flat
      .map(it => ({ it, score: matchScore(it, q) }))
      .filter(x => x.score > 0)
      .sort((a, b) => b.score - a.score)
      .map(x => ({ ...x.it, _group: x.it._sectionTitle }));
  }, [q, flat, favIds]);

  // Reset state when opened
  useEffect(() => {
    if (open) {
      setQ("");
      setActive(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  // Keyboard nav
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") { e.preventDefault(); onClose(); }
      else if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive(a => Math.min(a + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive(a => Math.max(a - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        const sel = filtered[active];
        if (sel) onNavigate(sel);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, filtered, active, onNavigate, onClose]);

  useEffect(() => { setActive(0); }, [q]);

  if (!open) return null;

  // Group items by _group label for the default (no-query) view
  const grouped = (() => {
    const groups = new Map();
    filtered.forEach((it, idx) => {
      const g = it._group || "Altele";
      if (!groups.has(g)) groups.set(g, []);
      groups.get(g).push({ ...it, _idx: idx });
    });
    return Array.from(groups.entries());
  })();

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[10vh] px-4" data-testid="command-palette">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 dark:border-slate-800">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            ref={inputRef}
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Caută modul, pagină sau acțiune… (ex: house health, gdpr, IT)"
            className="flex-1 bg-transparent text-sm outline-none text-slate-900 dark:text-slate-100 placeholder:text-slate-400"
            data-testid="command-palette-input"
          />
          <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">ESC</kbd>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto py-2">
          {filtered.length === 0 && (
            <div className="px-6 py-10 text-center text-sm text-slate-500 dark:text-slate-400">
              Niciun rezultat pentru „{q}”
            </div>
          )}
          {grouped.map(([groupLabel, items]) => (
            <div key={groupLabel} className="mb-1">
              <div className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 flex items-center gap-1.5">
                {groupLabel === "Favorite" && <Star className="w-3 h-3 text-amber-500 fill-amber-500" />}
                {groupLabel === "Recent" && <Clock className="w-3 h-3" />}
                {groupLabel}
              </div>
              {items.map(it => {
                const Icon = it.icon;
                const isActive = it._idx === active;
                const isFav = favIds.includes(it.id);
                return (
                  <div
                    key={`${it._sectionId}-${it.id}`}
                    onClick={() => onNavigate(it)}
                    onMouseEnter={() => setActive(it._idx)}
                    className={`flex items-center gap-3 px-4 py-2 cursor-pointer transition-colors ${
                      isActive
                        ? "bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-300"
                        : "text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/70"
                    }`}
                    data-testid={`palette-item-${it.id}`}
                  >
                    {Icon && <Icon className="w-4 h-4 shrink-0" />}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm truncate">{it.label}</div>
                      <div className="text-[11px] text-slate-400 dark:text-slate-500 truncate">{it._sectionTitle}</div>
                    </div>
                    {it.badge && (
                      <span className="text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 text-white">{it.badge}</span>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); onToggleFavorite(it.id); }}
                      className={`p-1 rounded transition-colors ${isFav ? "text-amber-500" : "text-slate-300 dark:text-slate-600 hover:text-amber-500"}`}
                      title={isFav ? "Elimină din favorite" : "Adaugă la favorite"}
                      data-testid={`palette-fav-${it.id}`}
                    >
                      <Star className={`w-3.5 h-3.5 ${isFav ? "fill-amber-500" : ""}`} />
                    </button>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-300 dark:text-slate-600" />
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between gap-4 px-4 py-2 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-900/80">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1"><kbd className="font-mono px-1.5 py-0.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">↑↓</kbd> navighează</span>
            <span className="flex items-center gap-1"><kbd className="font-mono px-1.5 py-0.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">Enter</kbd> deschide</span>
            <span className="flex items-center gap-1"><Star className="w-3 h-3 text-amber-500" /> favorite</span>
          </div>
          <div className="flex items-center gap-1">
            <Command className="w-3 h-3" />
            <span>PropManage · Palette</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
