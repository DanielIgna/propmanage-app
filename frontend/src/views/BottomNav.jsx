// PropManage — navigație principală per rol (Legea lui Hick: max 4-5 zone, etichete clare).
// Mobil: bară jos mare, ușor de atins. Desktop: dock proeminent cu icon + etichetă orizontală.
import React from "react";

export const BottomNav = ({ tabs, active, onChange, dataPrefix = "tab" }) => {
  const go = (id) => { window.scrollTo({ top: 0 }); onChange(id); };

  return (
    <>
      {/* MOBIL — bară jos, ținte mari de atins */}
      <nav
        className="lg:hidden fixed bottom-0 left-0 right-0 z-30 backdrop-blur-xl border-t"
        style={{ background: "var(--pm-surface-lowest)", borderColor: "var(--pm-outline)" }}
        data-testid="bottom-nav"
      >
        <div className="max-w-7xl mx-auto px-1">
          <div className={`grid ${tabs.length === 5 ? "grid-cols-5" : "grid-cols-4"}`}>
            {tabs.map((tab) => {
              const isActive = active === tab.id;
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => go(tab.id)}
                  className="relative flex flex-col items-center justify-center gap-1 pt-2.5 pb-3 transition-colors"
                  style={{ color: isActive ? "var(--pm-accent-ink)" : "var(--pm-text-muted)" }}
                  data-testid={`${dataPrefix}-${tab.id}`}
                >
                  <div className={`relative flex items-center justify-center w-12 h-7 rounded-full transition-colors ${isActive ? "bg-[#d4ff3a]/15" : ""}`}>
                    <Icon className="w-[22px] h-[22px]" strokeWidth={isActive ? 2.3 : 1.9} />
                    {tab.badge > 0 && (
                      <span
                        className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 rounded-full bg-[#d4ff3a] text-black text-[10px] font-bold flex items-center justify-center"
                        data-testid={`${dataPrefix}-badge-${tab.id}`}
                      >
                        {tab.badge > 99 ? "99+" : tab.badge}
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] font-semibold tracking-tight leading-none">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* DESKTOP — dock mare centrat: icon + etichetă, acțiune clară în 3 secunde */}
      <nav
        className="hidden lg:flex fixed bottom-6 left-1/2 -translate-x-1/2 z-30 items-center gap-1 p-1.5 rounded-full border shadow-2xl backdrop-blur-xl"
        style={{ background: "var(--pm-surface)", borderColor: "var(--pm-outline-strong)" }}
        data-testid="bottom-nav-desktop"
      >
        {tabs.map((tab) => {
          const isActive = active === tab.id;
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => go(tab.id)}
              className={`relative flex items-center gap-2.5 px-5 py-3 rounded-full text-sm font-bold whitespace-nowrap transition-colors ${isActive ? "text-black" : ""}`}
              style={isActive ? { background: "#d4ff3a" } : { color: "var(--pm-text-variant)" }}
              data-testid={`${dataPrefix}-desktop-${tab.id}`}
            >
              <Icon className="w-5 h-5" strokeWidth={isActive ? 2.4 : 2} />
              {tab.label}
              {tab.badge > 0 && (
                <span className={`min-w-[20px] h-5 px-1.5 rounded-full text-[11px] font-black flex items-center justify-center ${isActive ? "bg-black text-[#d4ff3a]" : "bg-[#d4ff3a] text-black"}`}>
                  {tab.badge > 99 ? "99+" : tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </>
  );
};
