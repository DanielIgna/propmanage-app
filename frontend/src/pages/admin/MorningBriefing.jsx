// Morning Briefing — at-a-glance status snapshot of all monitoring systems.
// Aggregates: Healthcheck, Smoke Test, Data Integrity, Incidents, AI findings.
// Goal: admin sees in 5 seconds whether all systems are OK or needs action.
import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  Sunrise, CheckCircle2, AlertTriangle, XCircle, Activity, Database,
  PlayCircle, AlertOctagon, FileSearch, RefreshCw, ArrowRight, Mail, HardDrive, BarChart3, Download
} from "lucide-react";
import { AdminCard } from "./AdminLayoutMetronic";
import { API } from "../DashShared";
import { toast } from "sonner";

// Status helpers
const TONE = {
  ok:    { bg: "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30", text: "text-emerald-700 dark:text-emerald-300", icon: CheckCircle2, iconColor: "text-emerald-500" },
  warn:  { bg: "bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/30",         text: "text-amber-700 dark:text-amber-300",   icon: AlertTriangle, iconColor: "text-amber-500" },
  fail:  { bg: "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30",                 text: "text-red-700 dark:text-red-300",       icon: XCircle, iconColor: "text-red-500" },
  idle:  { bg: "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700",            text: "text-slate-600 dark:text-slate-300",   icon: Activity, iconColor: "text-slate-400" },
};

const SystemTile = ({ icon: Icon, title, tone, headline, sub, action, secondaryAction, testid }) => {
  const t = TONE[tone] || TONE.idle;
  const StatusIcon = t.icon;
  return (
    <div className={`rounded-xl border p-3 ${t.bg}`} data-testid={testid}>
      <div className="flex items-start gap-2.5">
        <Icon className="w-4 h-4 shrink-0 mt-0.5 text-slate-600 dark:text-slate-300" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-500 dark:text-slate-400">{title}</span>
            <StatusIcon className={`w-3 h-3 ${t.iconColor}`} />
          </div>
          <div className={`text-sm font-semibold mt-0.5 ${t.text} truncate`}>{headline}</div>
          {sub && <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 truncate">{sub}</div>}
          {action && (
            <button
              onClick={action.onClick}
              disabled={action.disabled}
              className="mt-1.5 text-[11px] font-medium text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 disabled:opacity-50"
              data-testid={`${testid}-action`}
            >
              {action.label} <ArrowRight className="w-3 h-3" />
            </button>
          )}
          {secondaryAction && (
            <button
              onClick={secondaryAction.onClick}
              disabled={secondaryAction.disabled}
              className="mt-1 text-[11px] font-medium text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 disabled:opacity-50"
              data-testid={`${testid}-secondary-action`}
            >
              {secondaryAction.label} <Download className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const goToAI = () => window.dispatchEvent(new CustomEvent("propmanage:nav-admin", { detail: { tab: "ai" } }));

export const MorningBriefing = () => {
  const [healthcheck, setHealthcheck] = useState(null);
  const [smokeHistory, setSmokeHistory] = useState(null);
  const [smokeMonitor, setSmokeMonitor] = useState(null);
  const [integrity, setIntegrity] = useState(null);
  const [incidents, setIncidents] = useState(null);
  const [findings, setFindings] = useState(null);
  const [backupStatus, setBackupStatus] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [sendingTest, setSendingTest] = useState(false);
  const [sendingVelocity, setSendingVelocity] = useState(false);

  const sendVelocityReport = async () => {
    setSendingVelocity(true);
    try {
      const r = await axios.post(`${API}/admin/dev-velocity/send-now`, {}, { timeout: 60000 });
      const d = r.data || {};
      if (d.sent) {
        toast.success(`Raport săptămânal trimis · ${d.stats?.commits || 0} commits · ${d.recipients}/${d.total_recipients} admini`);
      } else {
        toast.error(`Trimitere eșuată: ${d.reason || "necunoscut"}`);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la generarea raportului");
    } finally {
      setSendingVelocity(false);
    }
  };
  const [runningBackup, setRunningBackup] = useState(false);
  const [dumpingBson, setDumpingBson] = useState(false);
  const dumpingBsonRef = useRef(false);

  const downloadBsonDump = async () => {
    if (dumpingBsonRef.current) return;
    dumpingBsonRef.current = true;
    setDumpingBson(true);
    const tid = toast.loading("Se generează dump BSON...");
    try {
      const r = await axios.post(`${API}/admin/backups/dump-bson`, {}, { timeout: 180000 });
      const d = r.data?.dump || {};
      if (!d.ok || !d.filename) {
        toast.error(`Dump BSON eșuat: ${d.error || "necunoscut"}`, { id: tid });
        return;
      }
      const fileResp = await axios.get(`${API}/admin/backups/download/${d.filename}`, {
        responseType: "blob",
        timeout: 180000,
      });
      const url = window.URL.createObjectURL(new Blob([fileResp.data], { type: "application/gzip" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = d.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`Dump BSON descărcat: ${d.size_mb}MB · ${d.collections_count} colecții`, { id: tid });
      load();
    } catch (err) {
      let detail = err?.response?.data?.detail;
      const data = err?.response?.data;
      if (data instanceof Blob) {
        try {
          const text = await data.text();
          detail = JSON.parse(text).detail || text;
        } catch {
          detail = null;
        }
      }
      toast.error(detail || "Eroare la dump BSON", { id: tid });
    } finally {
      dumpingBsonRef.current = false;
      setDumpingBson(false);
    }
  };

  const runManualBackup = async () => {
    setRunningBackup(true);
    try {
      const r = await axios.post(`${API}/admin/backups/run`);
      const b = r.data?.backup || {};
      const e = r.data?.email || {};
      if (b.ok) {
        toast.success(`Backup creat: ${b.size_mb}MB · ${b.collections_count} colecții · email→${e.recipients || 0}/${e.total_recipients || 0}`);
        load();
      } else {
        toast.error(`Backup eșuat: ${b.error || "necunoscut"}`);
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Eroare la creare backup");
    } finally {
      setRunningBackup(false);
    }
  };

  const sendTestEmail = async () => {
    setSendingTest(true);
    try {
      const r = await axios.post(`${API}/admin/morning-briefing/send-test`);
      const d = r.data || {};
      if (d.sent) {
        toast.success(`Email trimis către ${d.recipients}/${d.total_recipients} admin(s) · stare: ${d.overall}`);
      } else if (d.reason === "no_recipients") {
        toast.error("Niciun admin în ADMIN_EMAILS — configurează în deployment secrets.");
      } else {
        toast.error(`Trimitere eșuată: ${d.reason || "necunoscut"}`);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Eroare la trimiterea email-ului de test");
    } finally {
      setSendingTest(false);
    }
  };

  const load = async () => {
    setRefreshing(true);
    const safe = (p) => p.then(r => r.data).catch(() => null);
    const [hc, sh, sm, ig, inc, fi, bk] = await Promise.all([
      safe(axios.get(`${API}/admin/healthcheck/run`)),
      safe(axios.get(`${API}/admin/smoke-test/history?limit=1`)),
      safe(axios.get(`${API}/admin/smoke-test/monitor/config`)),
      safe(axios.get(`${API}/admin/data-integrity/history?limit=1`)),
      safe(axios.get(`${API}/admin/incidents?days=30`)),
      safe(axios.get(`${API}/admin/ai/findings?status=open`)),
      safe(axios.get(`${API}/admin/backups`)),
    ]);
    setHealthcheck(hc);
    setSmokeHistory(sh);
    setSmokeMonitor(sm);
    setIntegrity(ig);
    setIncidents(inc);
    setFindings(fi);
    setBackupStatus(bk);
    setRefreshing(false);
  };

  useEffect(() => {
    load();
    // Refresh every 5 minutes
    const t = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(t);
  }, []);

  // Derive per-system tone + headline
  const hcTile = (() => {
    if (!healthcheck) return { tone: "idle", headline: "Se încarcă..." };
    const s = healthcheck.summary || {};
    if (s.critical_failed > 0) return { tone: "fail", headline: `${s.critical_failed} integrare critică jos`, sub: `${s.passed}/${s.total} OK` };
    if (s.warnings_failed > 0) return { tone: "warn", headline: `${s.warnings_failed} cu avertizare`, sub: `${s.passed}/${s.total} OK` };
    return { tone: "ok", headline: "Toate integrările OK", sub: `${s.passed}/${s.total} verificate` };
  })();

  const smokeTile = (() => {
    const last = smokeHistory?.items?.[0];
    const monitorOn = smokeMonitor?.enabled;
    if (!last) return { tone: "idle", headline: "Niciun test rulat", sub: monitorOn ? "Monitor activ" : "Monitor inactiv" };
    const subParts = [];
    subParts.push(new Date(last.started_at).toLocaleString("ro-RO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }));
    if (monitorOn) subParts.push(`monitor ${smokeMonitor.interval_minutes}min`);
    if (last.ok) return { tone: "ok", headline: `${last.passed || last.total}/${last.total} PASS`, sub: subParts.join(" · ") };
    return { tone: "fail", headline: `${last.failed} pași eșuați`, sub: subParts.join(" · ") };
  })();

  const integrityTile = (() => {
    const last = integrity?.items?.[0];
    if (!last) return { tone: "idle", headline: "Niciun scan rulat", sub: "Rulează manual din AI Investigator" };
    const s = last.summary || {};
    const sub = new Date(last.started_at).toLocaleString("ro-RO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
    if (s.critical_failed > 0) return { tone: "fail", headline: `${s.critical_failed} verificări critice eșuate`, sub };
    if (s.total_issues_found > 0) return { tone: "warn", headline: `${s.total_issues_found} probleme detectate`, sub };
    return { tone: "ok", headline: "Toate verificările OK", sub };
  })();

  const incidentsTile = (() => {
    if (!incidents) return { tone: "idle", headline: "Se încarcă..." };
    const all = incidents.items || [];
    const active = all.filter(i => i.status !== "resolved");
    if (active.length === 0) return { tone: "ok", headline: "Niciun incident activ", sub: `${all.length} închise în ultimele 30 zile` };
    const worst = active.reduce((w, i) => {
      const sev = { critical: 3, major: 2, minor: 1 }[i.severity] || 0;
      return sev > w.sev ? { sev, item: i } : w;
    }, { sev: 0, item: null });
    const tone = worst.sev === 3 ? "fail" : "warn";
    return { tone, headline: `${active.length} incident${active.length > 1 ? "e" : ""} ${active.length > 1 ? "active" : "activ"}`, sub: worst.item ? `Cel mai grav: ${worst.item.title}` : null };
  })();

  const findingsTile = (() => {
    if (!findings) return { tone: "idle", headline: "Se încarcă..." };
    const counts = findings.by_severity || {};
    const open = findings.counts?.open || 0;
    if (open === 0) return { tone: "ok", headline: "Niciun finding deschis", sub: "Platforma e curată" };
    if ((counts.high || 0) > 0) return { tone: "fail", headline: `${counts.high} findings critice`, sub: `${open} deschise total` };
    if ((counts.warning || 0) > 0) return { tone: "warn", headline: `${counts.warning} warnings`, sub: `${open} deschise total` };
    return { tone: "warn", headline: `${open} findings deschise`, sub: "Verifică AI Investigator" };
  })();

  const backupTile = (() => {
    const latest = backupStatus?.latest_run;
    if (!latest) return { tone: "fail", headline: "Niciun backup creat", sub: "Apasă \"Backup acum\"" };
    const startedAt = new Date(latest.started_at);
    const ageH = (Date.now() - startedAt.getTime()) / 3600000;
    const sub = `${startedAt.toLocaleString("ro-RO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })} · ${latest.size_mb}MB · email ${latest.email_recipients || 0}`;
    if (!latest.ok) return { tone: "fail", headline: "Ultimul backup a eșuat", sub };
    if (ageH > 72) return { tone: "fail", headline: `Vechi de ${Math.round(ageH / 24)}z`, sub };
    if (ageH > 36) return { tone: "warn", headline: `Vechi de ${Math.round(ageH)}h`, sub };
    return { tone: "ok", headline: `${latest.collections_count} colecții salvate`, sub };
  })();

  // Aggregate overall health verdict
  const tiles = [hcTile, smokeTile, integrityTile, incidentsTile, findingsTile, backupTile];
  const hasFail = tiles.some(t => t.tone === "fail");
  const hasWarn = tiles.some(t => t.tone === "warn");
  const overallTone = hasFail ? "fail" : hasWarn ? "warn" : "ok";
  const overallMessage = hasFail
    ? "Atenție necesară — există probleme critice"
    : hasWarn
      ? "Câteva avertizări — verifică detaliile mai jos"
      : "Toate sistemele funcționează normal. Zi liniștită!";

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Bună dimineața" : hour < 18 ? "Bună ziua" : "Bună seara";

  return (
    <AdminCard
      title={
        <div className="flex items-center gap-2">
          <Sunrise className="w-4 h-4 text-amber-500" />
          <span>{greeting}, briefing rapid</span>
          <span className="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300">NEW</span>
        </div>
      }
      action={
        <div className="flex items-center gap-1">
          <button
            onClick={sendVelocityReport}
            disabled={sendingVelocity}
            className="px-2 py-1 rounded-lg text-[11px] font-semibold flex items-center gap-1.5 bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-500/30 hover:bg-blue-100 dark:hover:bg-blue-500/20 disabled:opacity-50"
            data-testid="briefing-send-velocity-btn"
            title="Generează și trimite raportul săptămânal de dev velocity (AI summary + stats git)"
          >
            <BarChart3 className={`w-3 h-3 ${sendingVelocity ? "animate-pulse" : ""}`} />
            {sendingVelocity ? "Se generează..." : "Raport săptămânal"}
          </button>
          <button
            onClick={sendTestEmail}
            disabled={sendingTest}
            className="px-2 py-1 rounded-lg text-[11px] font-semibold flex items-center gap-1.5 bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-500/30 hover:bg-amber-100 dark:hover:bg-amber-500/20 disabled:opacity-50"
            data-testid="briefing-send-test-email-btn"
            title="Forțează trimiterea email-ului de briefing acum (test Resend)"
          >
            <Mail className={`w-3 h-3 ${sendingTest ? "animate-pulse" : ""}`} />
            {sendingTest ? "Se trimite..." : "Test email"}
          </button>
          <button
            onClick={load}
            disabled={refreshing}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 disabled:opacity-50"
            data-testid="briefing-refresh-btn"
            title="Reîncarcă"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
          </button>
        </div>
      }
    >
      {/* Overall verdict banner */}
      <div className={`rounded-xl border p-3 mb-4 ${TONE[overallTone].bg}`} data-testid="briefing-verdict">
        <div className="flex items-center gap-2.5">
          {overallTone === "ok" && <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          {overallTone === "warn" && <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
          {overallTone === "fail" && <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />}
          <div className={`text-sm font-semibold ${TONE[overallTone].text}`}>{overallMessage}</div>
        </div>
      </div>

      {/* 6 system tiles in a responsive grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-6 gap-2.5" data-testid="briefing-tiles">
        <SystemTile
          icon={Activity}
          title="Healthcheck"
          tone={hcTile.tone}
          headline={hcTile.headline}
          sub={hcTile.sub}
          action={{ label: "Detalii", onClick: goToAI }}
          testid="briefing-tile-healthcheck"
        />
        <SystemTile
          icon={PlayCircle}
          title="Smoke Test"
          tone={smokeTile.tone}
          headline={smokeTile.headline}
          sub={smokeTile.sub}
          action={{ label: "Rulează", onClick: goToAI }}
          testid="briefing-tile-smoke"
        />
        <SystemTile
          icon={Database}
          title="Data Integrity"
          tone={integrityTile.tone}
          headline={integrityTile.headline}
          sub={integrityTile.sub}
          action={{ label: "Scanează", onClick: goToAI }}
          testid="briefing-tile-integrity"
        />
        <SystemTile
          icon={AlertOctagon}
          title="Incidents"
          tone={incidentsTile.tone}
          headline={incidentsTile.headline}
          sub={incidentsTile.sub}
          action={{ label: "Vezi /status", onClick: () => window.open("/status", "_blank") }}
          testid="briefing-tile-incidents"
        />
        <SystemTile
          icon={FileSearch}
          title="AI Findings"
          tone={findingsTile.tone}
          headline={findingsTile.headline}
          sub={findingsTile.sub}
          action={{ label: "Investighează", onClick: goToAI }}
          testid="briefing-tile-findings"
        />
        <SystemTile
          icon={HardDrive}
          title="Backup DB"
          tone={backupTile.tone}
          headline={backupTile.headline}
          sub={backupTile.sub}
          action={{ label: runningBackup ? "Se creează..." : "Backup acum", onClick: runManualBackup, disabled: runningBackup }}
          secondaryAction={{
            label: dumpingBson ? "Se generează..." : "Generează și descarcă dump BSON",
            onClick: downloadBsonDump,
            disabled: dumpingBson,
          }}
          testid="briefing-tile-backup"
        />
      </div>
    </AdminCard>
  );
};
