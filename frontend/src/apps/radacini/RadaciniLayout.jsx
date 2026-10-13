import React, { Suspense, useState } from "react";
import { NavLink, Outlet, Navigate, Link, useLocation } from "react-router-dom";
import { Sprout, Menu, ArrowLeft } from "lucide-react";
import { useAuth } from "../../auth";
import { DSSkeleton } from "../../design-system";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "../../components/ui/sheet";
import { NAV, canSee } from "./config";
import { useStaffMe } from "./hooks";

const linkCls = ({ isActive }) =>
  `flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-semibold transition-colors ${
    isActive
      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300"
      : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-white/5"
  }`;

const Brand = () => (
  <div className="flex items-center gap-2 px-5 h-16 border-b border-slate-200 dark:border-white/10">
    <Sprout className="w-5 h-5 text-emerald-600" />
    <span className="font-bold text-slate-900 dark:text-white">Rădăcini</span>
  </div>
);

const SidebarNav = ({ items, onNavigate }) => (
  <nav className="flex flex-col gap-1 p-3" data-testid="radacini-nav">
    {items.map(({ to, label, icon: Icon, testid }) => (
      <NavLink key={to} to={to} end={to === "/radacini"} onClick={onNavigate} className={linkCls} data-testid={testid}>
        <Icon className="w-4 h-4" />
        {label}
      </NavLink>
    ))}
  </nav>
);

export const RadaciniLayout = () => {
  const { user } = useAuth();
  const { staff } = useStaffMe();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);

  if (user === null) {
    return (
      <div className="p-6">
        <DSSkeleton kpis={3} blocks={1} />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;

  const items = NAV.filter((item) => canSee(item, staff));
  // Cel mai lung prefix care se potrivește dă titlul (ex. /radacini/terenuri/abc → Terenuri).
  const current = NAV.filter(
    (n) => pathname === n.to || (n.to !== "/radacini" && pathname.startsWith(`${n.to}/`))
  ).sort((a, b) => b.to.length - a.to.length)[0];
  const title = current?.label ?? "Rădăcini";
  const displayName = user.full_name || user.name || user.email;

  return (
    <div className="min-h-screen flex bg-slate-50 dark:bg-[#0b0c0d]">
      {/* Sidebar desktop */}
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-slate-200 dark:border-white/10 bg-white dark:bg-[#111213] print:hidden">
        <Brand />
        <SidebarNav items={items} />
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-10 flex items-center gap-3 h-16 px-4 md:px-6 border-b border-slate-200 dark:border-white/10 bg-white/90 dark:bg-[#111213]/90 backdrop-blur print:hidden">
          {/* Sidebar mobil */}
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <button type="button" aria-label="Meniu" data-testid="radacini-menu-mobil" className="md:hidden p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5">
                <Menu className="w-5 h-5 text-slate-700 dark:text-slate-200" />
              </button>
            </SheetTrigger>
            <SheetContent side="left" className="p-0 w-60">
              <SheetHeader className="sr-only">
                <SheetTitle>Meniu Rădăcini</SheetTitle>
              </SheetHeader>
              <Brand />
              <SidebarNav items={items} onNavigate={() => setOpen(false)} />
            </SheetContent>
          </Sheet>

          <h1 className="text-base md:text-lg font-bold text-slate-900 dark:text-white truncate">{title}</h1>

          <div className="ml-auto flex items-center gap-4">
            <div className="hidden sm:block text-right leading-tight">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{displayName}</p>
              {user.email && user.email !== displayName && (
                <p className="text-xs text-slate-500 dark:text-slate-400">{user.email}</p>
              )}
            </div>
            <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline">
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">Înapoi la PropManage</span>
            </Link>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-6">
          <Suspense fallback={<DSSkeleton kpis={3} blocks={2} />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
};
