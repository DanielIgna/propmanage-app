import React, { useEffect, useState, useCallback, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { ThemeToggle } from "../pages/DashShared";
import {
  Menu, X, ChevronDown, ChevronRight, Home, Layers, BadgeCheck, Box, Palette, Trees,
  Compass, Hammer, Paintbrush, Armchair, Wrench, Brush, Users, MessageCircle, KeyRound,
  PlayCircle, Sparkles, CircleDollarSign, HelpCircle, Building2, Info, BookOpen, Mail,
  UserCircle, LogIn, LogOut, UserPlus, LayoutDashboard, FolderKanban, MessageSquare,
  Bell, Settings, Languages, ShieldCheck, Circle,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const ICONS = {
  Home, Layers, BadgeCheck, Box, Palette, Trees, Compass, Hammer, Paintbrush, Armchair,
  Wrench, Brush, Users, MessageCircle, KeyRound, PlayCircle, Sparkles, CircleDollarSign,
  HelpCircle, Building2, Info, BookOpen, Mail, UserCircle, LogIn, LogOut, UserPlus,
  LayoutDashboard, FolderKanban, MessageSquare, Bell, Settings, ShieldCheck,
};

const MenuIcon = ({ name, className }) => {
  const Ico = ICONS[name] || Circle;
  return <Ico className={className} />;
};

const filterByAuth = (items, isAuth) =>
  items
    .filter((it) => it.visibility === "all" || (isAuth ? it.visibility === "auth" : it.visibility === "guests"))
    .map((it) => ({ ...it, children: filterByAuth(it.children || [], isAuth) }));

export const SiteNav = () => {
  const [scrolled, setScrolled] = useState(false);
  const [items, setItems] = useState([]);
  const [hidden, setHidden] = useState([]);
  const [entryRoute, setEntryRoute] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { user, logout } = useAuth();
  const { lang, toggle, t } = useI18n();
  const navigate = useNavigate();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    axios.get(`${API}/api/public/site-menu`).then((r) => setItems(r.data.items || [])).catch(() => {});
    axios.get(`${API}/api/ui-rules/my`, { withCredentials: true }).then((r) => setHidden(r.data.hidden || [])).catch(() => {});
  }, []);

  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [drawerOpen]);

  useEffect(() => {
    if (user && user.role) {
      axios.get(`${API}/api/experience/profile/${user.role}`).then((r) => setEntryRoute(r.data.entry_route)).catch(() => {});
    }
  }, [user]);

  const isAuth = Boolean(user && user !== false);
  const applyRules = (arr) => arr
    .filter((it) => !hidden.includes(`menu:${it.id}`))
    .map((it) => ({ ...it, children: applyRules(it.children || []) }));
  const visible = applyRules(filterByAuth(items, isAuth));

  const resolveHref = useCallback(
    (href) => (href || "").replace(/^\/dashboard/, entryRoute || `/${(user && user.role) || "login"}`),
    [user, entryRoute]
  );

  const handleLogout = async () => {
    try { await logout(); } catch (_) { /* ignore */ }
    window.location.href = "/";
  };

  const go = (href, meta) => {
    setDrawerOpen(false);
    if (meta?.id) {
      axios.post(`${API}/api/public/site-menu/track`, { item_id: meta.id, label: meta.label, href: href || "" }, { withCredentials: true }).catch(() => {});
    }
    if (href === "#logout") { handleLogout(); return; }
    const target = resolveHref(href);
    if (!target) return;
    if (target.startsWith("mailto:")) { window.location.href = target; return; }
    if (target.startsWith("/#") || target.startsWith("#")) {
      const hash = target.replace(/^\//, "");
      if (window.location.pathname !== "/") { window.location.href = "/" + hash; }
      else {
        const el = document.querySelector(hash);
        if (el) el.scrollIntoView({ behavior: "smooth" });
      }
      return;
    }
    navigate(target);
  };

  return (
    <>
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${scrolled ? "py-3" : "py-6"}`}>
        <div className={`max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between gap-2 ${scrolled ? "glass-strong rounded-full sm:mx-6 sm:px-6" : ""}`}>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setDrawerOpen(true)}
              className="lg:hidden p-2 -ml-1 rounded-full hover:bg-white/10 text-stone-200"
              aria-label="Deschide meniul"
              data-testid="mobile-menu-btn"
            >
              <Menu className="w-6 h-6" />
            </button>
            <a href="/" className="flex items-center gap-2" data-testid="nav-logo">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
                <Building2 className="w-4 h-4 text-black" strokeWidth={2.5} />
              </div>
              <span className="font-serif text-lg sm:text-xl font-semibold tracking-tight">PropManage</span>
            </a>
          </div>

          {/* Desktop: același meniu CMS, orizontal cu dropdown-uri */}
          <div className="hidden lg:flex items-center gap-1 xl:gap-2">
            {visible.map((it) =>
              it.children && it.children.length > 0 ? (
                <div key={it.id} className="relative group">
                  <button
                    className="flex items-center gap-1 px-3 py-2 text-sm text-stone-400 hover:text-white transition-colors rounded-full hover:bg-white/5"
                    data-testid={`nav-item-${it.id}`}
                  >
                    {it.label}
                    <ChevronDown className="w-3.5 h-3.5 transition-transform group-hover:rotate-180" />
                  </button>
                  <div className="absolute left-0 top-full pt-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity duration-200 z-50">
                    <div className="glass-strong rounded-2xl p-2 min-w-[240px] max-h-[70vh] overflow-y-auto shadow-2xl border border-white/10">
                      {it.children.map((c) => (
                        <button
                          key={c.id}
                          onClick={() => go(c.href, c)}
                          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-stone-300 hover:text-white hover:bg-white/10 transition-colors text-left"
                          data-testid={`nav-sub-${c.id}`}
                        >
                          <MenuIcon name={c.icon} className="w-4 h-4 text-[#d4ff3a]" />
                          {c.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <button
                  key={it.id}
                  onClick={() => go(it.href, it)}
                  className="px-3 py-2 text-sm text-stone-400 hover:text-white transition-colors rounded-full hover:bg-white/5"
                  data-testid={`nav-item-${it.id}`}
                >
                  {it.label}
                </button>
              )
            )}
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button onClick={toggle} className="hidden sm:flex items-center gap-1 px-2 sm:px-3 py-1.5 hover:bg-white/5 rounded-full text-xs uppercase tracking-wider text-stone-300" data-testid="lang-toggle">
              <Languages className="w-3.5 h-3.5" />{lang.toUpperCase()}
            </button>
            {isAuth && user.role === "admin" && (
              <Link to="/admin" className="inline-flex items-center gap-1.5 px-3 sm:px-4 py-2 sm:py-2.5 rounded-full text-xs sm:text-sm font-semibold bg-red-500/15 hover:bg-red-500/25 text-red-300 border border-red-500/30 transition-colors" data-testid="nav-admin" title="Panou Admin">
                <ShieldCheck className="w-3.5 h-3.5" /><span className="hidden sm:inline">Admin</span>
              </Link>
            )}
            {isAuth ? (
              <>
                <Link to={entryRoute || `/${user.role}`} className="btn-accent px-3 sm:px-5 py-2 sm:py-2.5 rounded-full text-xs sm:text-sm font-medium inline-flex items-center gap-1.5" data-testid="nav-dashboard">
                  <LayoutDashboard className="w-3.5 h-3.5" /><span className="hidden sm:inline">{t("nav.dashboard")}</span>
                </Link>
                <button onClick={handleLogout} className="hidden sm:inline-flex items-center gap-1.5 px-3 sm:px-4 py-2 sm:py-2.5 rounded-full text-xs sm:text-sm font-medium bg-white/5 hover:bg-white/10 text-stone-300 border border-white/10 transition-colors" data-testid="nav-logout" title="Deconectare">
                  <LogOut className="w-3.5 h-3.5" /><span className="hidden sm:inline">Logout</span>
                </button>
              </>
            ) : (
              <Link to="/login" className="btn-accent px-3 sm:px-5 py-2 sm:py-2.5 rounded-full text-xs sm:text-sm font-medium inline-flex items-center gap-1.5" data-testid="nav-login">
                <LogIn className="w-3.5 h-3.5" /><span className="hidden sm:inline">{t("nav.login")}</span>
              </Link>
            )}
          </div>
        </div>
      </nav>

      <MobileDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} items={visible} go={go} isAuth={isAuth} />
    </>
  );
};

const MobileDrawer = ({ open, onClose, items, go, isAuth }) => {
  const [expanded, setExpanded] = useState({});
  const touchX = useRef(null);

  const onTouchStart = (e) => { touchX.current = e.touches[0].clientX; };
  const onTouchMove = (e) => {
    if (touchX.current !== null && touchX.current - e.touches[0].clientX > 70) {
      touchX.current = null;
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[90] bg-black/60 backdrop-blur-sm lg:hidden"
            onClick={onClose}
            data-testid="mobile-drawer-overlay"
          />
          <motion.aside
            initial={{ x: "-100%" }} animate={{ x: 0 }} exit={{ x: "-100%" }}
            transition={{ type: "tween", duration: 0.28, ease: [0.32, 0.72, 0, 1] }}
            className="fixed top-0 left-0 bottom-0 z-[95] w-[85vw] max-w-[360px] bg-[#111210] border-r border-white/10 flex flex-col lg:hidden"
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            data-testid="mobile-drawer"
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/10 shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
                  <Building2 className="w-4 h-4 text-black" strokeWidth={2.5} />
                </div>
                <span className="font-serif text-lg font-semibold text-white">PropManage</span>
              </div>
              <button onClick={onClose} className="p-2 rounded-full hover:bg-white/10 text-stone-300" aria-label="Închide meniul" data-testid="mobile-drawer-close">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto py-3 px-3">
              {items.map((it, idx) => (
                <motion.div
                  key={it.id}
                  initial={{ opacity: 0, x: -14 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.05 + idx * 0.04 }}
                >
                  {it.children && it.children.length > 0 ? (
                    <>
                      <button
                        onClick={() => setExpanded((p) => ({ ...p, [it.id]: !p[it.id] }))}
                        className="w-full flex items-center justify-between gap-3 px-4 py-3.5 rounded-2xl text-lg font-medium text-stone-200 hover:bg-white/5 active:bg-white/10 transition-colors"
                        data-testid={`drawer-item-${it.id}`}
                      >
                        <span className="flex items-center gap-3">
                          <MenuIcon name={it.icon} className="w-5 h-5 text-[#d4ff3a]" />
                          {it.label}
                        </span>
                        <ChevronRight className={`w-5 h-5 text-stone-500 transition-transform duration-200 ${expanded[it.id] ? "rotate-90" : ""}`} />
                      </button>
                      <AnimatePresence initial={false}>
                        {expanded[it.id] && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.22 }}
                            className="overflow-hidden ml-4 border-l border-white/10 pl-2"
                          >
                            {it.children.map((c) => (
                              <button
                                key={c.id}
                                onClick={() => go(c.href, c)}
                                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-base text-stone-300 hover:bg-white/5 active:bg-white/10 transition-colors text-left"
                                data-testid={`drawer-sub-${c.id}`}
                              >
                                <MenuIcon name={c.icon} className="w-[18px] h-[18px] text-stone-500" />
                                {c.label}
                              </button>
                            ))}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </>
                  ) : (
                    <button
                      onClick={() => go(it.href, it)}
                      className="w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl text-lg font-medium text-stone-200 hover:bg-white/5 active:bg-white/10 transition-colors text-left"
                      data-testid={`drawer-item-${it.id}`}
                    >
                      <MenuIcon name={it.icon} className="w-5 h-5 text-[#d4ff3a]" />
                      {it.label}
                    </button>
                  )}
                </motion.div>
              ))}
            </div>

            {!isAuth && (
              <div className="p-4 border-t border-white/10 shrink-0">
                <button onClick={() => go("/register")} className="w-full btn-accent py-3.5 rounded-2xl text-base font-semibold" data-testid="drawer-cta-register">
                  Creează cont gratuit
                </button>
              </div>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};

export default SiteNav;
