import React, { Suspense, useEffect, useState } from "react";
import { NavLink, Outlet, Navigate, Link, useLocation } from "react-router-dom";
import { Sprout, Menu, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { api } from "../../lib/api";
import { useAuth } from "../../auth";
import { errMsg } from "./api";
import { impersonatePersona, loadCachedPersonas } from "./testAccounts";
import { DSSkeleton } from "../../design-system";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "../../components/ui/sheet";
import { NAV, canSee } from "./config";
import { StaffContext, useStaffLoader } from "./hooks";
import { TermsGateProvider } from "./components/TermsGate";
import OnboardingGuide from "./components/OnboardingGuide";
import MobileNav from "./components/MobileNav";
import PwaHead from "./components/PwaHead";

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
  const staffState = useStaffLoader();
  const { staff } = staffState;
  const { pathname, search } = useLocation();
  const [open, setOpen] = useState(false);
  // Cel mai lung prefix care se potrivește dă titlul (ex. /radacini/terenuri/abc → Terenuri).
  const current = NAV.filter(
    (n) => pathname === n.to || (n.to !== "/radacini" && pathname.startsWith(`${n.to}/`))
  ).sort((a, b) => b.to.length - a.to.length)[0];
  const title = current?.label ?? "Rădăcini";
  // Tab-ul browserului arată Rădăcini, nu PropManage.
  useEffect(() => {
    const prev = document.title;
    document.title = title === "Rădăcini" || title === "Panou" ? "Rădăcini" : `${title} · Rădăcini`;
    return () => {
      document.title = prev;
    };
  }, [title]);

  const imp = user?.impersonation;
  const [switching, setSwitching] = useState(false);
  const stopTest = async () => {
    setSwitching(true);
    try {
      await api.post("/admin/stop-impersonation");
      window.location.href = "/radacini/conturi-test";
    } catch (e) {
      toast.error(errMsg(e));
      setSwitching(false);
    }
  };
  const switchTo = async (key) => {
    const p = loadCachedPersonas().find((x) => x.key === key);
    if (!p) return;
    setSwitching(true);
    try {
      // Impersonarea imbricată e refuzată: ieșim întâi din contul curent.
      await api.post("/admin/stop-impersonation");
      await impersonatePersona(p);
    } catch (e) {
      toast.error(errMsg(e));
      setSwitching(false);
    }
  };

  // Beta închis: backend-ul răspunde 403 {code: "beta_closed"} conturilor care nu sunt pe lista de invitați.
  const [betaClosed, setBetaClosed] = useState(false);
  useEffect(() => {
    if (!user) return;
    api.get("/radacini/me").then(
      () => setBetaClosed(false),
      (e) => setBetaClosed(e?.response?.status === 403 && e?.response?.data?.detail?.code === "beta_closed")
    );
  }, [user]);

  if (user === null) {
    return (
      <div className="p-6">
        <DSSkeleton kpis={3} blocks={1} />
      </div>
    );
  }
  if (!user) return <Navigate to={`/radacini/login?next=${encodeURIComponent(pathname + search)}`} replace />;

  if (betaClosed) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#0b0c0d] p-4" data-testid="radacini-beta-closed">
        <div className="max-w-md w-full rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-6 text-center space-y-3">
          <Sprout className="mx-auto h-10 w-10 text-emerald-600" aria-hidden />
          <h1 className="text-xl font-bold text-slate-900 dark:text-white">Rădăcini e în beta închis</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Momentan testăm platforma cu un grup mic de invitați. Contul <b>{user.email}</b> nu e încă pe listă.
            Te anunțăm când deschidem accesul.
          </p>
          <Link to="/" className="inline-block text-sm font-semibold text-emerald-700 underline dark:text-emerald-300">Înapoi la PropManage</Link>
        </div>
      </div>
    );
  }

  const items = NAV.filter((item) => canSee(item, staff, user));
  const displayName = user.full_name || user.name || user.email;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-[#0b0c0d]">
      {imp && (
        <div className="sticky top-0 z-30 flex flex-wrap items-center gap-3 px-4 py-2 bg-amber-400 text-amber-950 text-sm font-semibold print:hidden" data-testid="radacini-test-bar">
          <span>Ești în contul de test {displayName}</span>
          <button type="button" disabled={switching} onClick={stopTest} className="underline disabled:opacity-60" data-testid="radacini-test-revino">
            Revino la contul tău
          </button>
          {loadCachedPersonas().length > 0 && (
            <select
              aria-label="Schimbă contul de test"
              disabled={switching}
              value=""
              onChange={(e) => e.target.value && switchTo(e.target.value)}
              className="ml-auto rounded-md border border-amber-600 bg-amber-50 px-2 py-1 text-xs"
              data-testid="radacini-test-switch"
            >
              <option value="">Schimbă contul…</option>
              {loadCachedPersonas().map((p) => (
                <option key={p.key} value={p.key}>{p.name} · {p.label}</option>
              ))}
            </select>
          )}
        </div>
      )}
      <div className="flex-1 flex min-h-0">
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
            <Link to="/" className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:underline" data-testid="radacini-inapoi-propmanage">
              <ArrowLeft className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Înapoi la PropManage</span>
            </Link>
          </div>
        </header>

        <main className="flex-1 p-4 pb-24 md:p-6 print:pb-0">
          <StaffContext.Provider value={staffState}>
            <TermsGateProvider>
              <Suspense fallback={<DSSkeleton kpis={3} blocks={2} />}>
                <Outlet />
              </Suspense>
              <OnboardingGuide />
            </TermsGateProvider>
          </StaffContext.Provider>
        </main>
      </div>
      </div>
      <PwaHead />
      <MobileNav onMenu={() => setOpen(true)} />
    </div>
  );
};
