import React from "react";
import {
  PMCard, PMCardPrimary, PMCardGlass,
  PMStatCard, PMPillButton, PMChip, PMSectionHeader,
  PMTaskRow, PMFab, PMTopBar, PMBottomNav, PMProgress,
  PMAvatarStack, PMEmptyState,
} from "../components/pm";
import {
  Wallet, BadgeCheck, HardHat, Home, Briefcase, MessageSquare,
  Bell, Settings, ArrowUpRight, Calendar, MapPin, Clock,
  Plus, Search, Filter, AlertCircle, Star, Inbox,
} from "lucide-react";

export default function DesignSystemShowcase() {
  const bottomNavItems = [
    { id: "home", label: "Acasă", icon: Home, active: true, onClick: () => {} },
    { id: "jobs", label: "Lucrări", icon: Briefcase, onClick: () => {} },
    { id: "msg", label: "Mesaje", icon: MessageSquare, onClick: () => {} },
    { id: "settings", label: "Profil", icon: Settings, onClick: () => {} },
  ];

  return (
    <div className="pm-page-bg pb-32">
      {/* Top Bar */}
      <PMTopBar
        title="PropManage v2 — Playground"
        subtitle="Design System Showcase"
        trailing={
          <>
            <PMPillButton variant="ghost" size="sm" icon={Bell}>3</PMPillButton>
            <PMPillButton variant="primary" size="sm" icon={Plus}>Nou</PMPillButton>
          </>
        }
        testid="pm-playground-topbar"
      />

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-10 space-y-12">
        {/* Hero */}
        <section className="pm-fade-in">
          <PMCardPrimary testid="pm-hero-card">
            <PMChip variant="primary" className="!bg-[var(--pm-on-primary-container)] !text-[var(--pm-primary-container)] !border-transparent mb-3">
              SISTEM v2 · FAZA 0
            </PMChip>
            <h1 className="text-3xl md:text-5xl font-bold text-[var(--pm-on-primary-container)] mb-3 tracking-tight">
              Începem redesign-ul.
            </h1>
            <p className="text-[var(--pm-on-primary-container)] opacity-80 max-w-2xl mb-6">
              Sistem de design unificat pentru zonele Specialist, Client, Public și Community.
              Backend-ul rămâne intact. Doar UI-ul se transformă într-unul prietenos și modern.
            </p>
            <div className="flex gap-3 flex-wrap">
              <PMPillButton variant="on-container" icon={ArrowUpRight}>Vezi Specialist Dashboard</PMPillButton>
              <PMPillButton variant="ghost" className="!text-[var(--pm-on-primary-container)] !border-[var(--pm-on-primary-container)]/30">
                Documentație
              </PMPillButton>
            </div>
          </PMCardPrimary>
        </section>

        {/* Bento stats */}
        <section className="pm-fade-in-delay-1">
          <PMSectionHeader title="Statistici Bento" linkLabel="Vezi toate" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <PMStatCard
              icon={Wallet}
              label="Câștiguri totale"
              value="€12,480"
              delta="+12.5%"
              deltaType="up"
              testid="stat-earnings"
            />
            <PMStatCard
              icon={BadgeCheck}
              label="Rată succes"
              value="99.2%"
              trailing={<PMChip variant="primary">Top 2%</PMChip>}
              testid="stat-success"
            />
            <PMStatCard
              icon={HardHat}
              label="Lucrări active"
              value="8"
              trailing={
                <PMAvatarStack
                  avatars={[
                    { initials: "AI" },
                    { initials: "MV" },
                    { initials: "DC" },
                  ]}
                  max={2}
                />
              }
              testid="stat-active-jobs"
            />
          </div>
        </section>

        {/* Task rows */}
        <section className="pm-fade-in-delay-2">
          <PMSectionHeader title="Sarcini active" linkLabel="Vezi calendarul" />
          <div className="space-y-3">
            <PMTaskRow
              urgency="urgent"
              icon={AlertCircle}
              title="Înlocuire încuietori inteligente"
              subtitle="Complex Nord · Urgență ridicată"
              meta={
                <>
                  <p className="text-sm font-semibold text-[var(--pm-error)]">Astăzi</p>
                  <p className="text-xs text-[var(--pm-text-variant)]">Imediat</p>
                </>
              }
              onClick={() => {}}
              testid="task-urgent"
            />
            <PMTaskRow
              urgency="primary"
              icon={HardHat}
              title="Reparație HVAC · Apartament 4B"
              subtitle="Strada Victoriei nr. 12 · Mediu"
              meta={
                <>
                  <p className="text-sm font-semibold text-[var(--pm-text)]">24 Oct</p>
                  <p className="text-xs text-[var(--pm-text-variant)]">14:30 – 16:00</p>
                </>
              }
              onClick={() => {}}
              testid="task-primary"
            />
            <PMTaskRow
              urgency="default"
              icon={Briefcase}
              title="Curățenie profesională · Vila Green Park"
              subtitle="Șos. Pipera 45 · Planificat"
              meta={
                <>
                  <p className="text-sm font-semibold text-[var(--pm-text)]">25 Oct</p>
                  <p className="text-xs text-[var(--pm-text-variant)]">09:00 – 18:00</p>
                </>
              }
              onClick={() => {}}
              testid="task-default"
            />
          </div>
        </section>

        {/* Chips & Pills */}
        <section className="pm-fade-in-delay-3">
          <PMSectionHeader title="Atomi UI" />
          <PMCardGlass>
            <div className="space-y-6">
              <div>
                <p className="text-xs uppercase tracking-wider text-[var(--pm-text-muted)] mb-3">Chips</p>
                <div className="flex gap-2 flex-wrap">
                  <PMChip>Default</PMChip>
                  <PMChip variant="primary" icon={Star}>Premium</PMChip>
                  <PMChip variant="error" icon={AlertCircle}>Urgent</PMChip>
                  <PMChip variant="warning">În așteptare</PMChip>
                  <PMChip variant="success">Verificat</PMChip>
                  <PMChip variant="info">Beta</PMChip>
                </div>
              </div>

              <div>
                <p className="text-xs uppercase tracking-wider text-[var(--pm-text-muted)] mb-3">Pill Buttons</p>
                <div className="flex gap-3 flex-wrap items-center">
                  <PMPillButton variant="primary" icon={Plus}>Acțiune principală</PMPillButton>
                  <PMPillButton variant="on-container" icon={Search}>On Container</PMPillButton>
                  <PMPillButton variant="ghost" icon={Filter}>Ghost</PMPillButton>
                  <PMPillButton variant="primary" size="sm">Small</PMPillButton>
                  <PMPillButton variant="primary" size="lg">Large</PMPillButton>
                </div>
              </div>

              <div>
                <p className="text-xs uppercase tracking-wider text-[var(--pm-text-muted)] mb-3">Progres ghid</p>
                <PMProgress value={65} label="Completare profil" showValue />
              </div>
            </div>
          </PMCardGlass>
        </section>

        {/* Empty state */}
        <section>
          <PMSectionHeader title="Empty State" />
          <PMEmptyState
            icon={Inbox}
            title="Nicio cerere activă"
            description="Aplică la oportunitățile din marketplace ca să apară aici."
            action={<PMPillButton variant="primary" icon={Search}>Caută oportunități</PMPillButton>}
            testid="pm-empty-state"
          />
        </section>

        {/* Card variants */}
        <section>
          <PMSectionHeader title="Variante Card" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <PMCard accent="primary">
              <p className="text-xs uppercase tracking-wider text-[var(--pm-text-muted)] mb-2">Card standard</p>
              <p className="text-[var(--pm-text)]">Border-left primary accent.</p>
            </PMCard>
            <PMCard accent="urgent">
              <p className="text-xs uppercase tracking-wider text-[var(--pm-text-muted)] mb-2">Card urgent</p>
              <p className="text-[var(--pm-text)]">Border-left urgent (roșu).</p>
            </PMCard>
            <PMCardGlass>
              <p className="text-xs uppercase tracking-wider text-[var(--pm-text-muted)] mb-2">Glass card</p>
              <p className="text-[var(--pm-text)]">Backdrop blur + transparență.</p>
            </PMCardGlass>
          </div>
        </section>
      </main>

      {/* FAB */}
      <PMFab onClick={() => alert("FAB clicked!")} label="Acțiune rapidă" testid="pm-fab-demo" />

      {/* Bottom Nav (mobile only) */}
      <PMBottomNav items={bottomNavItems} testid="pm-playground-bottomnav" />
    </div>
  );
}
