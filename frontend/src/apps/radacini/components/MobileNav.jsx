import React from "react";
import { NavLink } from "react-router-dom";
import { LayoutDashboard, MapPin, Store, Briefcase, Menu } from "lucide-react";

const ITEMS = [
  { to: "/radacini", label: "Panou", icon: LayoutDashboard, end: true, testid: "radacini-bottom-panou" },
  { to: "/radacini/terenuri", label: "Terenuri", icon: MapPin, testid: "radacini-bottom-terenuri" },
  { to: "/radacini/piata", label: "Piață", icon: Store, testid: "radacini-bottom-piata" },
  { to: "/radacini/proiecte", label: "Proiecte", icon: Briefcase, testid: "radacini-bottom-proiecte" },
];
const base = "flex-1 min-h-[44px] min-w-[44px] flex flex-col items-center justify-center gap-0.5 py-1.5 text-[11px] font-semibold transition-colors";
const on = "text-emerald-600 dark:text-emerald-300";
const off = "text-slate-500 dark:text-slate-400";

// Bară de navigare jos, doar pe ecrane mici. „Meniu” deschide Sheet-ul existent (onMenu).
export default function MobileNav({ onMenu }) {
  return (
    <nav
      aria-label="Navigare rapidă"
      className="md:hidden print:hidden fixed bottom-0 inset-x-0 z-20 flex border-t border-slate-200 dark:border-white/10 bg-white/95 dark:bg-[#111213]/95 backdrop-blur pb-[env(safe-area-inset-bottom)]"
      data-testid="radacini-bottom-nav"
    >
      {ITEMS.map(({ to, label, icon: Icon, end, testid }) => (
        <NavLink key={to} to={to} end={end} data-testid={testid} className={({ isActive }) => `${base} ${isActive ? on : off}`}>
          <Icon className="w-5 h-5" />
          {label}
        </NavLink>
      ))}
      <button type="button" onClick={onMenu} className={`${base} ${off}`} data-testid="radacini-bottom-meniu">
        <Menu className="w-5 h-5" />
        Meniu
      </button>
    </nav>
  );
}
