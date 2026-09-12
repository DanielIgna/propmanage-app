// RESEARCH COVERAGE MATRIX — Internal Founder tool (READ-ONLY view of research state)
// Zero backend changes. Reuses /api/founder/knowledge/doc to fetch INTERVIEW_REGISTRY.md
// + PATTERN_REGISTRY.md, parses markdown tables client-side, computes matrix/gaps/bias.
// This is NOT a user-facing feature — Founder-only via existing gate.
import React, { useEffect, useState, useMemo } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  BookOpenCheck, ArrowLeft, ShieldAlert, Loader2, TrendingUp, AlertTriangle,
  Target, Compass, Activity, LineChart,
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const ax = axios.create({ baseURL: API, withCredentials: true });

// ---------- Markdown table parser (client-side) ----------
const parseMarkdownTable = (md, sectionHeading) => {
  if (!md) return { headers: [], rows: [] };
  const sections = md.split(/^##\s+/im);
  const target = sections.find(s => new RegExp(`^${sectionHeading}\\b`, "i").test(s));
  if (!target) return { headers: [], rows: [] };
  const lines = target.split("\n");
  const tableLines = lines.filter(l => /^\s*\|.+\|\s*$/.test(l));
  if (tableLines.length < 2) return { headers: [], rows: [] };
  const isSep = (l) => /^\s*\|(\s*[-:]+\s*\|)+\s*$/.test(l);
  const cells = (l) => l.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(c => c.trim());
  const headers = cells(tableLines[0]);
  const headerKey = headers.join("||").toLowerCase();
  // Filter separators AND duplicate header rows (registry may have multiple sub-tables sharing schema)
  const dataRows = tableLines.slice(1)
    .filter(l => !isSep(l))
    .map(cells)
    .filter(r => r.join("||").toLowerCase() !== headerKey);
  return { headers, rows: dataRows.map(r => Object.fromEntries(headers.map((h, i) => [h, r[i] || ""]))) };
};

// ---------- Bucket classifiers ----------
const yearBucket = (year) => {
  const y = parseInt(year, 10);
  if (Number.isNaN(y)) return "N/A";
  if (y < 1980) return "pre-1980";
  if (y <= 2000) return "1980-2000";
  return "post-2000";
};
const aptsBucket = (n) => {
  const x = parseInt(n, 10);
  if (Number.isNaN(x)) return "N/A";
  if (x < 20) return "<20";
  if (x <= 50) return "20-50";
  return ">50";
};
const personaFromId = (id) => {
  const prefix = (id || "").split("-")[0].toUpperCase();
  return ({ AP: "Președinte", AD: "Administrator", PR: "Proprietar", SP: "Specialist" })[prefix] || "N/A";
};
const parseYears = (s) => {
  if (!s) return NaN;
  const clean = s.toLowerCase().replace(/[~+]/g, "").trim();
  const m = clean.match(/(\d+)/);
  if (!m) return NaN;
  const n = parseInt(m[1], 10);
  if (/peste|\+|over/.test(clean) && n >= 10) return n; // "peste 40 ani" → 40
  return n;
};
const experienceBucket = (tenureStr) => {
  const y = parseYears(tenureStr);
  if (Number.isNaN(y)) return "N/A";
  if (y <= 2) return "0-2 ani";
  if (y <= 10) return "2-10 ani";
  return ">10 ani";
};
const localityFromBloc = (bloc) => {
  // Interviews currently don't declare city/county — return N/A. Track gap.
  return "N/A";
};

// ---------- Coverage math ----------
const distribute = (arr, keyFn) => {
  const out = {};
  arr.forEach(x => {
    const k = keyFn(x);
    out[k] = (out[k] || 0) + 1;
  });
  return out;
};
const coveragePct = (dist, buckets) => {
  const filled = buckets.filter(b => (dist[b] || 0) > 0).length;
  return Math.round((filled / buckets.length) * 100);
};

const BUCKETS = {
  year: ["pre-1980", "1980-2000", "post-2000"],
  apts: ["<20", "20-50", ">50"],
  persona: ["Președinte", "Administrator", "Proprietar", "Specialist"],
  experience: ["0-2 ani", "2-10 ani", ">10 ani"],
};

const TARGET_TOTAL = 15; // Founder target: 15-20 for Feature Freeze release
const REPORT_MIN_INTERVIEWS = 3;
const REPORT_MIN_VALIDATED_PATTERNS = 1;

// ---------- Component ----------
export default function ResearchCoveragePage() {
  const [tree, setTree] = useState(null);
  const [interviewRegistry, setInterviewRegistry] = useState(null);
  const [patternRegistry, setPatternRegistry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        // Reuse existing endpoints — no new API calls introduced
        const treeR = await ax.get(`/api/founder/knowledge/tree`);
        setTree(treeR.data);
        const [ir, pr] = await Promise.all([
          ax.get(`/api/founder/knowledge/doc`, { params: { path: "memory/registries/INTERVIEW_REGISTRY.md" } }),
          ax.get(`/api/founder/knowledge/doc`, { params: { path: "memory/registries/PATTERN_REGISTRY.md" } }),
        ]);
        setInterviewRegistry(ir.data.content);
        setPatternRegistry(pr.data.content);
      } catch (e) {
        if (e?.response?.status === 403) setDenied(true);
        else setErr(e?.response?.data?.detail || e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Parse tables → interview objects
  const interviews = useMemo(() => {
    if (!interviewRegistry) return [];
    const { rows } = parseMarkdownTable(interviewRegistry, "Entries");
    return rows.map(r => ({
      id: r.InterviewID || "",
      date: r.Date || "",
      bloc: r.AssociationBloc || "",
      year: r.YearBuilt || "",
      apts: r.Apartments || "",
      tenure: r.PresidentTenure || "",
      status: r.Status || "",
      path: r.FilePath || "",
    })).filter(x => x.id && x.status === "Validated");
  }, [interviewRegistry]);

  // Parse pattern registry
  const patterns = useMemo(() => {
    if (!patternRegistry) return [];
    const { rows } = parseMarkdownTable(patternRegistry, "Entries — ordonate după Maturity descrescător apoi PatternID");
    // Fallback: try the "Entries" section
    if (!rows.length) {
      const alt = parseMarkdownTable(patternRegistry, "Entries");
      return alt.rows;
    }
    return rows;
  }, [patternRegistry]);

  // Compute distributions once
  const dist = useMemo(() => ({
    year: distribute(interviews, i => yearBucket(i.year)),
    apts: distribute(interviews, i => aptsBucket(i.apts)),
    persona: distribute(interviews, i => personaFromId(i.id)),
    experience: distribute(interviews, i => experienceBucket(i.tenure)),
    locality: distribute(interviews, i => localityFromBloc(i.bloc)),
  }), [interviews]);

  const scores = useMemo(() => ({
    persoane: coveragePct(dist.persona, BUCKETS.persona),
    tipBloc: coveragePct(dist.year, BUCKETS.year),
    vechime: coveragePct(dist.experience, BUCKETS.experience),
    apartamente: coveragePct(dist.apts, BUCKETS.apts),
    // Locality: manual since we only have N/A
    localizare: (dist.locality["N/A"] || 0) === interviews.length && interviews.length > 0 ? 0 : 100,
  }), [dist, interviews.length]);

  // Pattern maturity roll-up (parsed from PATTERN_REGISTRY)
  const patternMaturity = useMemo(() => {
    const counts = { Observation: 0, "Emerging Pattern": 0, "Validated Pattern Candidate": 0, "High Confidence Pattern": 0 };
    patterns.forEach(p => {
      const m = p.Maturity;
      if (m && counts.hasOwnProperty(m)) counts[m] += 1;
    });
    return counts;
  }, [patterns]);

  // Bias analysis
  const bias = useMemo(() => {
    const total = interviews.length;
    const findings = [];
    if (!total) return findings;
    Object.entries(dist).forEach(([dim, bucketMap]) => {
      Object.entries(bucketMap).forEach(([bucket, count]) => {
        if (bucket === "N/A") {
          if (count === total) findings.push({ level: "high", msg: `Dimensiunea "${dim}" nu este declarată la niciun interviu (100% N/A) — lipsă totală de date` });
          else if (count > 0) findings.push({ level: "medium", msg: `${count}/${total} interviuri au "${dim}" declarat ca N/A` });
        } else {
          const pct = Math.round(count / total * 100);
          if (pct >= 70 && total >= 3) findings.push({ level: "high", msg: `Supra-reprezentare: "${dim}=${bucket}" apare în ${pct}% din interviuri` });
        }
      });
      // Under-representation: buckets defined but not filled
      const definedBuckets = BUCKETS[dim];
      if (definedBuckets) {
        const missing = definedBuckets.filter(b => !bucketMap[b]);
        if (missing.length) findings.push({ level: "medium", msg: `"${dim}" — bucket-uri neacoperite: ${missing.join(", ")}` });
      }
    });
    return findings;
  }, [dist, interviews.length]);

  // Next Best Interview — find the intersection of most under-represented buckets
  const nextBest = useMemo(() => {
    if (!interviews.length) return null;
    const pickWorst = (dim) => {
      const b = BUCKETS[dim];
      if (!b) return null;
      let worst = b[0], min = Infinity;
      b.forEach(k => {
        const c = dist[dim][k] || 0;
        if (c < min) { min = c; worst = k; }
      });
      return { bucket: worst, count: min };
    };
    return {
      persoana: pickWorst("persona"),
      an: pickWorst("year"),
      apartamente: pickWorst("apts"),
      experienta: pickWorst("experience"),
      locality: "Declarat explicit (oraș + județ)",
    };
  }, [dist, interviews.length]);

  // Research Progress estimation
  const progress = useMemo(() => {
    const validatedCount = patternMaturity["Validated Pattern Candidate"] + patternMaturity["High Confidence Pattern"];
    const emergingCount = patternMaturity["Emerging Pattern"];
    const interviewsNeededForReport = Math.max(0, REPORT_MIN_INTERVIEWS - interviews.length);
    const patternsNeededForReport = Math.max(0, REPORT_MIN_VALIDATED_PATTERNS - validatedCount);
    // Optimistic: with 1 more interview and if it confirms one of the Emerging → 1 Validated
    const optimistic = interviewsNeededForReport <= 1 && emergingCount >= 1 ? 1 : interviewsNeededForReport;
    return { interviewsNeededForReport, patternsNeededForReport, optimistic, validatedCount, emergingCount };
  }, [interviews.length, patternMaturity]);

  if (loading) return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-200 flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-[#d4ff3a]" data-testid="rc-loading" />
    </div>
  );
  if (denied) return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-200 flex items-center justify-center p-6" data-testid="rc-denied">
      <div className="max-w-md text-center space-y-3">
        <ShieldAlert className="w-10 h-10 text-red-400 mx-auto" />
        <h1 className="font-serif text-2xl">Research Coverage — Founder Only</h1>
        <p className="text-sm text-stone-400">Această pagină este restricționată. Contactează Fondatorul.</p>
        <Link to="/admin" className="pm-btn pm-btn-secondary inline-block">Înapoi la Admin</Link>
      </div>
    </div>
  );
  if (err) return (
    <div className="min-h-screen bg-[#0a0a0b] text-red-300 flex items-center justify-center p-6" data-testid="rc-error">
      <div>Eroare: {err}</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-200" data-testid="research-coverage-page">
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <header className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <Link to="/admin/knowledge-center" className="text-xs text-stone-500 hover:text-white flex items-center gap-1" data-testid="rc-back-kc">
              <ArrowLeft className="w-3 h-3" /> Înapoi la Knowledge Center
            </Link>
            <h1 className="text-3xl font-serif mt-1 flex items-center gap-2" data-testid="rc-title">
              <BookOpenCheck className="w-6 h-6 text-[#d4ff3a]" /> Research Coverage Matrix
            </h1>
            <p className="text-xs text-stone-500 mt-1">
              Instrument intern Founder · <strong>NU</strong> feature pentru utilizatori · Read-only view peste INTERVIEW_REGISTRY + PATTERN_REGISTRY
            </p>
          </div>
          <div className="flex gap-3 text-[11px] text-stone-500">
            <div className="border border-white/10 rounded-lg px-3 py-1.5">
              <div className="uppercase tracking-widest text-[9px]">Interviews Validated</div>
              <div className="text-lg font-mono text-white" data-testid="rc-total-interviews">{interviews.length} / {TARGET_TOTAL}</div>
            </div>
            <div className="border border-white/10 rounded-lg px-3 py-1.5">
              <div className="uppercase tracking-widest text-[9px]">Patterns Tracked</div>
              <div className="text-lg font-mono text-white" data-testid="rc-total-patterns">{patterns.length}</div>
            </div>
          </div>
        </header>

        {/* SECTION 1 — Coverage Matrix */}
        <section className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5" data-testid="rc-section-matrix">
          <h2 className="font-serif text-xl mb-3 flex items-center gap-2"><Target className="w-4 h-4 text-[#d4ff3a]" /> Section 1 · Coverage Matrix</h2>
          <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
            {Object.entries(BUCKETS).map(([dim, buckets]) => (
              <div key={dim} className="border border-white/10 rounded-xl p-3" data-testid={`rc-dim-${dim}`}>
                <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-2">{dim === "year" ? "An construcție" : dim === "apts" ? "Nr. apartamente" : dim === "persona" ? "Tip participant" : "Experiență"}</div>
                {buckets.map(b => {
                  const count = dist[dim][b] || 0;
                  const isFilled = count > 0;
                  return (
                    <div key={b} className="flex items-center justify-between py-1 text-xs border-b border-white/[0.03] last:border-0">
                      <span className={isFilled ? "text-stone-200" : "text-stone-500"}>{b}</span>
                      <span className={`font-mono text-[11px] px-1.5 py-0.5 rounded ${isFilled ? "bg-[#d4ff3a]/10 text-[#d4ff3a] border border-[#d4ff3a]/30" : "bg-stone-500/10 text-stone-400 border border-white/5"}`}>{count}</span>
                    </div>
                  );
                })}
              </div>
            ))}
            <div className="border border-white/10 rounded-xl p-3" data-testid="rc-dim-locality">
              <div className="text-[10px] uppercase tracking-widest text-stone-500 mb-2">Localizare (oraș/județ)</div>
              <div className="text-xs text-red-300">
                {interviews.filter(i => localityFromBloc(i.bloc) === "N/A").length} / {interviews.length} interviuri fără localitate declarată — <strong>GAP CRITIC</strong>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 2 — Coverage Gaps */}
        <section className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5" data-testid="rc-section-gaps">
          <h2 className="font-serif text-xl mb-3 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-300" /> Section 2 · Coverage Gaps</h2>
          <ul className="space-y-1.5 text-xs">
            {Object.entries(BUCKETS).flatMap(([dim, buckets]) => {
              const missing = buckets.filter(b => !dist[dim][b]);
              if (!missing.length) return [];
              const label = dim === "year" ? "an construcție" : dim === "apts" ? "nr. apartamente" : dim === "persona" ? "tip participant" : "experiență";
              return [(
                <li key={dim} className="flex items-start gap-2" data-testid={`rc-gap-${dim}`}>
                  <span className="text-amber-300">◉</span>
                  <span>Lipsesc {label}: <strong className="text-white font-mono">{missing.join(" · ")}</strong></span>
                </li>
              )];
            })}
            {interviews.length && interviews.every(i => localityFromBloc(i.bloc) === "N/A") && (
              <li className="flex items-start gap-2" data-testid="rc-gap-locality">
                <span className="text-red-400">●</span>
                <span>Lipsă totală localizare — 0/{interviews.length} interviuri au oraș/județ declarat</span>
              </li>
            )}
          </ul>
        </section>

        {/* SECTION 3 — Next Best Interview */}
        <section className="bg-[#0e0e10] border border-[#d4ff3a]/30 rounded-2xl p-5" data-testid="rc-section-next">
          <h2 className="font-serif text-xl mb-3 flex items-center gap-2"><Compass className="w-4 h-4 text-[#d4ff3a]" /> Section 3 · Next Best Interview</h2>
          {nextBest && (
            <>
              <div className="grid md:grid-cols-2 gap-3 text-xs">
                <div className="border border-white/10 rounded-lg p-3">
                  <div className="text-[10px] uppercase text-stone-500">Persoană țintă</div>
                  <div className="text-lg text-[#d4ff3a] font-mono" data-testid="rc-next-persona">{nextBest.persoana.bucket}</div>
                  <div className="text-[10px] text-stone-500">acoperire actuală: {nextBest.persoana.count}</div>
                </div>
                <div className="border border-white/10 rounded-lg p-3">
                  <div className="text-[10px] uppercase text-stone-500">Tip bloc</div>
                  <div className="text-lg text-[#d4ff3a] font-mono" data-testid="rc-next-year">{nextBest.an.bucket}</div>
                  <div className="text-[10px] text-stone-500">acoperire actuală: {nextBest.an.count}</div>
                </div>
                <div className="border border-white/10 rounded-lg p-3">
                  <div className="text-[10px] uppercase text-stone-500">Nr. apartamente</div>
                  <div className="text-lg text-[#d4ff3a] font-mono" data-testid="rc-next-apts">{nextBest.apartamente.bucket}</div>
                  <div className="text-[10px] text-stone-500">acoperire actuală: {nextBest.apartamente.count}</div>
                </div>
                <div className="border border-white/10 rounded-lg p-3">
                  <div className="text-[10px] uppercase text-stone-500">Experiență</div>
                  <div className="text-lg text-[#d4ff3a] font-mono" data-testid="rc-next-experience">{nextBest.experienta.bucket}</div>
                  <div className="text-[10px] text-stone-500">acoperire actuală: {nextBest.experienta.count}</div>
                </div>
                <div className="border border-white/10 rounded-lg p-3 md:col-span-2">
                  <div className="text-[10px] uppercase text-stone-500">Localizare</div>
                  <div className="text-lg text-[#d4ff3a] font-mono" data-testid="rc-next-locality">{nextBest.locality}</div>
                </div>
              </div>
              <p className="text-[11px] text-stone-500 mt-3 italic" data-testid="rc-next-rationale">
                <strong>De ce această alegere reduce bias-ul</strong>: fiecare dimensiune are cel puțin un bucket la 0 (sub-reprezentare completă).
                Al 3-lea interviu care intră în bucket-uri diferite de cele existente crește coverage-ul cel mai mult per unitate de efort — și crește șansa să promoveze primul pattern la <strong>Validated Pattern Candidate</strong> (nevoie de 3 confirmări independente).
                Adăugarea localității rezolvă bias-ul geografic (0% acoperit acum).
              </p>
            </>
          )}
        </section>

        {/* SECTION 4 — Coverage Score */}
        <section className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5" data-testid="rc-section-score">
          <h2 className="font-serif text-xl mb-3 flex items-center gap-2"><LineChart className="w-4 h-4 text-emerald-300" /> Section 4 · Coverage Score</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
            {Object.entries(scores).map(([k, v]) => (
              <div key={k} className="border border-white/10 rounded-lg p-3" data-testid={`rc-score-${k}`}>
                <div className="text-[9px] uppercase tracking-widest text-stone-500 mb-1">{k}</div>
                <div className={`text-2xl font-mono ${v >= 75 ? "text-emerald-300" : v >= 50 ? "text-amber-300" : v >= 25 ? "text-orange-300" : "text-red-300"}`}>{v}%</div>
                <div className="w-full h-1 bg-white/5 rounded mt-2 overflow-hidden">
                  <div className={`h-full ${v >= 75 ? "bg-emerald-400" : v >= 50 ? "bg-amber-400" : v >= 25 ? "bg-orange-400" : "bg-red-400"}`} style={{ width: `${v}%` }} />
                </div>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-stone-500 mt-3 italic">
            Formula: <span className="font-mono">filled_buckets / total_buckets × 100</span> — reprezintă lărgimea acoperirii per dimensiune. Nu este scor de calitate, ci de breadth.
          </p>
        </section>

        {/* SECTION 5 — Bias Analysis */}
        <section className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5" data-testid="rc-section-bias">
          <h2 className="font-serif text-xl mb-3 flex items-center gap-2"><Activity className="w-4 h-4 text-orange-300" /> Section 5 · Bias Analysis</h2>
          {bias.length ? (
            <ul className="space-y-1.5 text-xs">
              {bias.map((b, i) => (
                <li key={i} className="flex items-start gap-2" data-testid={`rc-bias-${i}`}>
                  <span className={b.level === "high" ? "text-red-400" : "text-amber-300"}>{b.level === "high" ? "▲" : "△"}</span>
                  <span>{b.msg}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-stone-400">Zero riscuri de bias detectate — cohort echilibrat.</p>
          )}
        </section>

        {/* SECTION 6 — Research Progress */}
        <section className="bg-[#0e0e10] border border-white/10 rounded-2xl p-5" data-testid="rc-section-progress">
          <h2 className="font-serif text-xl mb-3 flex items-center gap-2"><TrendingUp className="w-4 h-4 text-sky-300" /> Section 6 · Research Progress</h2>
          <div className="flex items-center justify-between text-xs mb-3 gap-1.5 flex-wrap" data-testid="rc-pipeline">
            {[
              { label: "Interview", count: interviews.length, active: true, color: "emerald" },
              { label: "Observation", count: patternMaturity.Observation, active: patternMaturity.Observation > 0, color: "sky" },
              { label: "Emerging", count: patternMaturity["Emerging Pattern"], active: patternMaturity["Emerging Pattern"] > 0, color: "amber" },
              { label: "Validated Candidate", count: patternMaturity["Validated Pattern Candidate"], active: patternMaturity["Validated Pattern Candidate"] > 0, color: "violet" },
              { label: "Research Report", count: 0, active: false, color: "stone" },
            ].map((s, i, arr) => (
              <React.Fragment key={s.label}>
                <div className={`flex-1 border rounded-lg p-2 text-center min-w-[100px] ${s.active ? `border-${s.color}-500/40 bg-${s.color}-500/10 text-white` : "border-white/10 text-stone-500"}`}>
                  <div className="text-[9px] uppercase">{s.label}</div>
                  <div className="text-lg font-mono">{s.count}</div>
                </div>
                {i < arr.length - 1 && <span className="text-stone-600">→</span>}
              </React.Fragment>
            ))}
          </div>
          <div className="grid md:grid-cols-2 gap-3 text-xs">
            <div className="border border-white/10 rounded-lg p-3" data-testid="rc-progress-interviews-needed">
              <div className="text-[10px] uppercase text-stone-500">Până la primul Research Report</div>
              <div className="text-white mt-1">
                Interviuri suplimentare: <strong className="font-mono text-lg text-[#d4ff3a]">+{progress.interviewsNeededForReport}</strong>
                <span className="text-stone-500 text-[10px] ml-2">(min. {REPORT_MIN_INTERVIEWS} total)</span>
              </div>
              <div className="text-white mt-1">
                Pattern-uri Validated Candidate: <strong className="font-mono text-lg text-[#d4ff3a]">+{progress.patternsNeededForReport}</strong>
                <span className="text-stone-500 text-[10px] ml-2">(min. {REPORT_MIN_VALIDATED_PATTERNS})</span>
              </div>
            </div>
            <div className="border border-white/10 rounded-lg p-3" data-testid="rc-progress-optimistic">
              <div className="text-[10px] uppercase text-stone-500">Scenariu optimist (dacă AP-004 confirmă 1 Emerging)</div>
              <div className="text-white mt-1">
                Un singur interviu în plus poate:
                <ul className="list-disc pl-5 mt-1 text-stone-300">
                  <li>promova P-002/P-003/P-004/P-005 (Emerging → Validated Candidate)</li>
                  <li>atinge <strong>3 Validated Interviews</strong> (prag Research Report)</li>
                  <li>debloca primul Research Report emis metodologic</li>
                </ul>
              </div>
            </div>
          </div>
          <p className="text-[10px] text-stone-500 mt-3 italic">
            Feature Freeze rămâne <strong>ACTIV</strong> până la primul Research Report + Product Blueprint decision explicită. Metodologia păstrată: Interview → Observation → Emerging → Validated → Research Report → Blueprint → Roadmap → Build.
          </p>
        </section>
      </div>
    </div>
  );
}
