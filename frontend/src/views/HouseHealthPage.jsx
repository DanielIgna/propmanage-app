// House Health main page — sidebar + active section orchestrator.
// Route: /house-health/:twinId
// Implementation is split across /app/frontend/src/pages/house_health/* for maintainability.
import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import { Heart, ChevronLeft } from "lucide-react";
import { API } from "./DashShared";
import { SECTIONS, EVALUATION_KINDS } from "./house_health/constants";
import { ScoreSection } from "./house_health/ScoreSection";
import { DocumentsSection } from "./house_health/DocumentsSection";
import { HistorySection } from "./house_health/HistorySection";
import { EvaluationSection } from "./house_health/EvaluationSection";
import { RecommendationsSection } from "./house_health/RecommendationsSection";
import { PbContextBanner } from "../components/pb/PbEverywhere";

const HouseHealthPage = () => {
  const { twinId } = useParams();
  const [section, setSection] = useState("score");
  const [dashData, setDashData] = useState(null);

  useEffect(() => {
    axios.get(`${API}/house-health/dashboard`).then((r) => setDashData(r.data)).catch(() => {});
    import("../lib/analytics").then(({ trackIntent }) => trackIntent("audit_viewed")).catch(() => {});
  }, []);

  const renderSection = () => {
    if (section === "score") return <ScoreSection data={dashData} />;
    if (section === "docs") return <DocumentsSection twinId={twinId} />;
    if (section === "history") return <HistorySection twinId={twinId} />;
    if (section === "recommendations") return <RecommendationsSection twinId={twinId} />;
    if (EVALUATION_KINDS.includes(section)) return <EvaluationSection twinId={twinId} kind={section} />;
    return null;
  };

  return (
    <div className="min-h-screen bg-stone-950 text-stone-100">
      <div className="max-w-6xl mx-auto p-4 sm:p-6">
        <div className="flex items-center gap-3 mb-5">
          <Link to="/client" className="text-stone-400 hover:text-stone-200 inline-flex items-center gap-1 text-sm">
            <ChevronLeft className="w-4 h-4" /> Înapoi
          </Link>
        </div>

        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
            <Heart className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Sănătatea Casei</h1>
            <p className="text-xs text-stone-400">
              {dashData?.twin?.name || "Proprietatea ta"} ·
              <span className={`ml-1 ${dashData?.subscription?.status === "active" ? "text-emerald-400" : "text-amber-400"}`}>
                {(dashData?.subscription?.status || "no-sub").toUpperCase()}
              </span>
            </p>
          </div>
        </div>

        <PbContextBanner surface="house_health" />

        <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-5">
          <aside className="bg-stone-900/40 border border-stone-800 rounded-2xl p-3 h-fit" data-testid="hh-sidebar">
            {SECTIONS.map((s) => {
              const Icon = s.icon;
              const isActive = section === s.key;
              return (
                <button
                  key={s.key}
                  onClick={() => setSection(s.key)}
                  className={`w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 text-sm mb-0.5 transition-colors ${
                    isActive ? "bg-emerald-500/15 text-emerald-300 font-semibold" : "text-stone-300 hover:bg-stone-800"
                  }`}
                  data-testid={`hh-tab-${s.key}`}
                >
                  <Icon className="w-4 h-4" />
                  {s.label}
                </button>
              );
            })}
          </aside>

          <div data-testid={`hh-section-${section}`}>
            {renderSection()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HouseHealthPage;
