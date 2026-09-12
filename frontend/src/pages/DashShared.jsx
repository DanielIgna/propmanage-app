// PropManage - Shared Dashboard utilities (Layout, Stats, Notifications)
import React, { useState, useEffect } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import axios from "axios";
import { Building2, Home, Wrench, ShieldCheck, Settings, LogOut, Languages, Bell, Sun, Moon, ArrowLeftRight } from "lucide-react";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { AIAssistant } from "./AIAssistant";
import { VoucherExpiryAlert } from "../lib/VoucherExpiryAlert";
import { EmailVerificationBanner } from "../components/EmailVerificationBanner";
import { PendingReviewsWidget } from "../components/MultiDimReviews";
import { GettingStartedWidget } from "../components/GettingStartedWidget";
import { HelpButton } from "../components/HelpButton";
import { ThemeSwitcher } from "../components/ThemeSwitcher";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ============= THEME TOGGLE (light/dark) =============
export const ThemeToggle = () => {
  // Bridge: wraps the new multi-theme switcher so existing call sites stay working.
  return <ThemeSwitcher compact />;
};

// ============= NAVIGATE BUTTONS (Google Maps / Waze deep-links) =============
export const NavigateButtons = ({ address, lat, lng, compact = false }) => {
  if (!address && !lat) return null;
  const query = address ? encodeURIComponent(address) : `${lat},${lng}`;
  const gmaps = `https://www.google.com/maps/dir/?api=1&destination=${query}&travelmode=driving`;
  const waze = lat && lng
    ? `https://www.waze.com/ul?ll=${lat}%2C${lng}&navigate=yes`
    : `https://waze.com/ul?q=${query}`;
  if (compact) {
    return (
      <div className="flex gap-1.5" data-testid="navigate-buttons-compact">
        <a href={gmaps} target="_blank" rel="noopener noreferrer"
          className="text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-blue-500/15 hover:bg-blue-500/25 text-blue-300 border border-blue-500/40 flex items-center gap-1"
          data-testid="open-gmaps-btn" title="Deschide în Google Maps">
          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C8 2 5 5 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-4-3-7-7-7zm0 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z"/></svg>
          Maps
        </a>
        <a href={waze} target="_blank" rel="noopener noreferrer"
          className="text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/40 flex items-center gap-1"
          data-testid="open-waze-btn" title="Deschide în Waze">
          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>
          Waze
        </a>
      </div>
    );
  }
  return (
    <div className="flex gap-2 flex-wrap" data-testid="navigate-buttons">
      <a href={gmaps} target="_blank" rel="noopener noreferrer"
        className="px-3 py-2 rounded-full bg-blue-500/15 hover:bg-blue-500/25 text-blue-300 border border-blue-500/40 text-xs flex items-center gap-1.5 font-medium"
        data-testid="open-gmaps-btn">
        Mergi cu Google Maps
      </a>
      <a href={waze} target="_blank" rel="noopener noreferrer"
        className="px-3 py-2 rounded-full bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/40 text-xs flex items-center gap-1.5 font-medium"
        data-testid="open-waze-btn">
        Mergi cu Waze
      </a>
    </div>
  );
};



// ============= NOTIFICATIONS BELL =============
export const NotificationsBell = () => {
  const [notifs, setNotifs] = useState([]);
  const [open, setOpen] = useState(false);

  const load = () => axios.get(`${API}/notifications`).then(r => setNotifs(r.data)).catch(() => {});
  useEffect(() => {
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  const unread = notifs.filter(n => !n.read).length;

  const markRead = async (id) => {
    await axios.post(`${API}/notifications/${id}/read`).catch(() => {});
    load();
  };

  return (
    <div className="relative" data-tour="notifications-bell">
      <button onClick={() => setOpen(!open)} aria-label="Notificări" className="relative p-2 hover:bg-white/5 rounded-lg" data-testid="notif-bell">
        <Bell className="w-4 h-4 text-stone-400" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-[#d4ff3a] text-black text-[9px] font-bold rounded-full flex items-center justify-center">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-2 w-80 glass-strong rounded-2xl border border-white/10 z-40 max-h-[400px] overflow-auto no-scrollbar" data-testid="notif-panel">
            <div className="p-3 border-b border-white/5 sticky top-0 bg-[#0a0a0b]/80 backdrop-blur">
              <div className="text-xs uppercase tracking-wider text-stone-400">Notificări</div>
            </div>
            {notifs.length === 0 ? (
              <div className="p-6 text-center text-xs text-stone-500">Nicio notificare</div>
            ) : (
              <div className="divide-y divide-white/5">
                {notifs.slice(0, 10).map(n => (
                  <div key={n.id} onClick={() => markRead(n.id)}
                    className={`p-3 cursor-pointer hover:bg-white/5 ${!n.read ? "bg-[#d4ff3a]/5" : ""}`}
                    data-testid={`notif-${n.id}`}>
                    <div className="flex items-start gap-2">
                      {!n.read && <div className="w-1.5 h-1.5 rounded-full bg-[#d4ff3a] mt-1.5 shrink-0" />}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium">{n.title}</div>
                        <div className="text-[11px] text-stone-400 mt-0.5">{n.message}</div>
                        <div className="text-[9px] text-stone-600 mt-1">
                          {new Date(n.created_at).toLocaleString("ro-RO")}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

// ============= LAYOUT =============
export const DashLayout = ({ children, role, title, bottomNav }) => {
  const { user, logout, refreshUser } = useAuth();
  const { lang, toggle, t } = useI18n();
  const navigate = useNavigate();

  const roleConfig = {
    client: { icon: Home, label: "Client", color: "lime" },
    specialist: { icon: Wrench, label: "Specialist", color: "amber" },
    admin: { icon: ShieldCheck, label: "Admin", color: "cyan" },
    operator: { icon: Settings, label: "Operator", color: "purple" },
  }[role];

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const switchProfile = async () => {
    if (!user?.dual_role_enabled) return;
    const target = user.active_view === "client" ? "specialist" : "client";
    try {
      await axios.post(`${API}/auth/switch-view`, { view: target });
      await refreshUser();
      window.location.href = target === "client" ? "/client" : "/specialist";
    } catch (e) {
      alert(e?.response?.data?.detail || "Eroare la comutare profil");
    }
  };

  // Auth state: null = checking, false = not authenticated, object = authenticated
  if (user === false) return <Navigate to={`/login?next=/${role}`} replace />;
  if (!user) return <div className="min-h-screen flex items-center justify-center text-stone-400">{t("common.loading")}</div>;

  // Dual-role: route guard accepts the user when their active_view matches the dashboard role
  const effectiveRole = user.active_view || user.role;
  if (effectiveRole !== role) return <Navigate to={`/${effectiveRole}`} replace />;

  const inClientView = effectiveRole === "client" && user.dual_role_enabled;
  // Show the quick-switch button only when the user actually has both profiles
  const showQuickSwitch = user.dual_role_enabled === true && (role === "client" || role === "specialist");
  const switchTargetLabel = effectiveRole === "client" ? "Specialist" : "Client";
  // Avatar fallback chain: uploaded avatar → Google picture → initials
  const avatarSrc = user.avatar || user.picture || null;

  return (
    <div className="pm-shell min-h-screen bg-[#0a0a0b] text-stone-100">
      <EmailVerificationBanner />
      <header className="border-b border-white/5 sticky top-0 z-40 bg-[#0a0a0b]/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4 sm:gap-8 min-w-0">
            <Link to="/" className="flex items-center gap-2 shrink-0" data-testid="dash-logo">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
                <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
              </div>
              <span className="font-serif text-lg font-semibold">PropManage</span>
            </Link>
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-full">
              <roleConfig.icon className="w-3.5 h-3.5 text-[#d4ff3a]" />
              <span className="text-xs uppercase tracking-wider text-stone-300">{roleConfig.label}</span>
            </div>
            {user.dual_role_enabled && (
              <span className="hidden sm:inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30" data-testid="dual-role-badge">
                Profil activ: {effectiveRole === "client" ? "Client" : "Specialist"}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            {showQuickSwitch && (
              <button
                onClick={switchProfile}
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] uppercase tracking-wider bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 text-[#d4ff3a] hover:bg-[#d4ff3a]/20 transition"
                title={`Comută la profilul de ${switchTargetLabel}`}
                data-testid="dash-switch-profile"
              >
                <ArrowLeftRight className="w-3 h-3" />
                <span className="hidden md:inline">Schimbă la </span>{switchTargetLabel}
              </button>
            )}
            <HelpButton />
            <ThemeToggle />
            <NotificationsBell />
            {(role === "client" || role === "specialist") && <VoucherExpiryAlert />}
            <button onClick={toggle} className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 hover:bg-white/5 rounded-full text-xs uppercase tracking-wider" data-testid="dash-lang">
              <Languages className="w-3.5 h-3.5" />{lang.toUpperCase()}
            </button>
            <div className="hidden md:block text-right">
              <div className="text-sm font-medium truncate max-w-[160px]">{user.name}</div>
              <div className="text-[10px] text-stone-500 truncate max-w-[160px] flex items-center gap-1 justify-end">
                <span className="truncate">{user.email}</span>
                {role === "client" && <TierBadgeMini tier={user.experience_tier || "junior"} />}
              </div>
            </div>
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-stone-600 to-stone-800 flex items-center justify-center font-medium text-sm overflow-hidden" data-testid="dash-avatar">
              {avatarSrc ? (
                <img
                  src={avatarSrc}
                  alt={user.name}
                  className="w-full h-full object-cover"
                  referrerPolicy="no-referrer"
                  onError={(e) => { e.currentTarget.style.display = "none"; e.currentTarget.parentNode.textContent = (user.name?.[0] || "U").toUpperCase(); }}
                />
              ) : (user.name?.[0] || "U").toUpperCase()}
            </div>
            <button onClick={handleLogout} aria-label="Deconectare" className="hidden sm:block p-2 hover:bg-white/5 rounded-lg" data-testid="dash-logout">
              <LogOut className="w-4 h-4 text-stone-400" />
            </button>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 pb-24">
        {title && <h1 className="xos-display font-light lg:font-bold tracking-tight text-4xl sm:text-5xl lg:text-[40px] mb-6 sm:mb-8" data-testid="dash-title">{title}</h1>}
        {role === "client" && <GettingStartedWidget role={role} />}
        {(role === "client" || role === "specialist") && (
          <div className="mb-6"><PendingReviewsWidget /></div>
        )}
        {children}
      </main>
      {bottomNav}
      <AIAssistant />
    </div>
  );
};

// ============= STAT CARD (Updated to PM v2 design) =============
export const Stat = ({ icon: Icon, label, value, sub, color = "lime", tid, ...rest }) => (
  <div className="pm-stat" data-testid={tid} {...rest}>
    <div className="flex items-center justify-between">
      <div className="pm-stat-icon">
        <Icon className="w-5 h-5" />
      </div>
      {sub && <span className="text-[10px] text-stone-500 uppercase tracking-wider font-semibold">{sub}</span>}
    </div>
    <div>
      <p className="pm-stat-label mb-1">{label}</p>
      <p className="pm-stat-value">{value}</p>
    </div>
  </div>
);

// ============= STATUS BADGE =============
export const StatusBadge = ({ status }) => {
  const cfg = {
    open: { c: "blue", l: "Deschis" },
    assigned: { c: "amber", l: "Asignat" },
    in_progress: { c: "yellow", l: "În lucru" },
    completed: { c: "purple", l: "Finalizat" },
    confirmed: { c: "emerald", l: "Confirmat" },
  }[status] || { c: "stone", l: status };
  return <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-${cfg.c}-500/15 text-${cfg.c}-400 border border-${cfg.c}-500/20`}>{cfg.l}</span>;
};

// Tier mini-badge for dashboard header. Imported via inline definition to
// avoid circular dep with /lib/experienceTier (which uses useAuth).
const TIER_BADGE_STYLE = {
  junior:   "bg-stone-500/10 border-stone-500/30 text-stone-300",
  regular:  "bg-blue-500/10 border-blue-500/30 text-blue-300",
  verified: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
  pro:      "bg-violet-500/10 border-violet-500/30 text-violet-300",
};
const TIER_BADGE_LABEL = { junior: "Junior", regular: "Regular", verified: "Verified", pro: "Pro" };
const TierBadgeMini = ({ tier }) => {
  const t = tier || "junior";
  const cls = TIER_BADGE_STYLE[t] || TIER_BADGE_STYLE.junior;
  return (
    <span
      className={`inline-flex items-center text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded-full border ${cls}`}
      title={`Experience tier: ${TIER_BADGE_LABEL[t]}`}
      data-testid="dash-tier-badge"
    >
      {TIER_BADGE_LABEL[t]}
    </span>
  );
};

