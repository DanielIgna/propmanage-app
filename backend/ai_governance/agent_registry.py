"""AI Governance — Agent Registry (Phase 1, observability)

Static metadata catalog of all AI agents in the PropManage ecosystem.
Each entry references the live data sources it writes to, so the dashboard
can compute "last activity", "items count", and rough cost without modifying
any agent code.

NEVER add an agent here without also documenting its data source. If an
agent has no observable trail, it cannot be governed — that's a finding.
"""

# Provider cost averages (rough, in EUR per 1000 input tokens — last update Feb 2026)
# Used ONLY for ballpark monthly cost estimate; not for billing.
PROVIDER_AVG_COST_PER_CALL_EUR = {
    "claude_sonnet_4_5":   0.012,   # Claude Sonnet 4.5 via Emergent Universal Key
    "claude_haiku":        0.003,
    "gpt_4o":              0.010,
    "gpt_4o_mini":         0.002,
    "gemini_3_flash":      0.001,
    "gemini_3_pro":        0.009,
    "mixed":               0.008,   # weighted average for agents using multiple
}


AI_AGENTS = [
    # --- Core orchestration ---
    {
        "slug": "ai_control_center",
        "name": "AI Control Center",
        "category": "control_plane",
        "lifecycle": "active",  # active | legacy | experimental | deprecated
        "maturity": "mature",
        "provider": "mixed",
        "purpose": "Provider switching, model selection, token control, ecosystem toggles.",
        "data_sources": ["app_settings"],
        "owner": "Platform Core",
        "permission_level": "execute",  # read | suggest | execute-with-approval | autonomous
    },
    {
        "slug": "autonomy_engine",
        "name": "Autonomy Engine",
        "category": "control_plane",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "claude_sonnet_4_5",
        "purpose": "Daily scoring of operational/technical/security/AI/dev autonomy with recommendations.",
        "data_sources": ["autonomy_snapshots"],
        "owner": "Platform Core",
        "permission_level": "suggest",
    },

    {
        "slug": "revenue_hunter",
        "name": "Revenue Hunter Engine",
        "category": "revenue",
        "lifecycle": "active",
        "maturity": "experimental",
        "provider": "mixed",  # v1 rule-based — zero cost LLM (ierarhia de cost, Prompt 003)
        "purpose": "Transformă starea Property DNA în oportunități comerciale pentru serviciile monetizabile (Digital Twin, Audit Tehnic, Design Interior, Design Tematic). Board Review 001. Nu contactează clientul — aprobare prin click in-app.",
        "data_sources": ["revenue_opportunities", "revenue_hunter_scans"],
        "owner": "Intelligence Engine",
        "permission_level": "suggest",
    },
    {
        "slug": "growth_intelligence",
        "name": "Growth Intelligence Agent",
        "category": "intelligence",
        "lifecycle": "active",
        "maturity": "experimental",
        "provider": "mixed",  # v1 rule-based — zero cost LLM (ierarhia de cost, Prompt 003)
        "purpose": "Analizează comportamentul real (sesiuni, bounce, funnel, trasee, ore/zile, surse) și produce probleme UX, pagini de abandon, Behavioral Intelligence și recomandări cu nivel de validare (Board 006).",
        "data_sources": ["growth_insights", "growth_insights_history"],
        "owner": "Intelligence Engine",
        "permission_level": "suggest",
    },
    {
        "slug": "lead_intelligence",
        "name": "Intent & Lead Intelligence Engine",
        "category": "intelligence",
        "lifecycle": "active",
        "maturity": "experimental",
        "provider": "mixed",  # v1 rule-based — zero cost LLM; calibrare Learning Engine în GI-4
        "purpose": "Intent Score 0-100 per vizitator din semnale reale (twin/audit vizualizat, cereri începute/abandonate, WhatsApp, reveniri, campanii) → clasificare visitor/prospect/qualified/hot/client. Prioritizează automat Revenue Hunter și alimentează Command Center.",
        "data_sources": ["lead_scores", "visitor_identities"],
        "owner": "Intelligence Engine",
        "permission_level": "suggest",
    },
    {
        "slug": "marketing_intelligence",
        "name": "Marketing Intelligence+ Engine",
        "category": "intelligence",
        "lifecycle": "active",
        "maturity": "experimental",
        "provider": "mixed",  # scan rule-based; Contact Playbook folosește Claude la cerere
        "purpose": "Recomandări executive de marketing din date reale (ferestre optime WhatsApp/postări cu uplift vs medie, canal/mesaj câștigător, serviciu de promovat, pagina care pierde utilizatori) + Opportunity Queue + AI Contact Playbook cu aprobare umană (Board 007). Deciziile intră în ai_decision_ledger.",
        "data_sources": ["marketing_insights", "contact_playbooks", "ai_decision_ledger"],
        "owner": "Intelligence Engine",
        "permission_level": "suggest",
    },
    {
        "slug": "learning_engine",
        "name": "Learning Engine (GI-4a Outcome Tracker)",
        "category": "intelligence",
        "lifecycle": "active",
        "maturity": "experimental",
        "provider": "mixed",  # rule-based, zero LLM
        "purpose": "Leagă fiecare decizie AI de rezultatul real (engagement → conversie → cerere → venit RON) prin ferestre de atribuire last-touch. Ledger-ul = SSoT pentru deciziile AI (arhitectura GI-4 frozen).",
        "data_sources": ["ai_decision_ledger", "ai_outcomes"],
        "owner": "Intelligence Engine",
        "permission_level": "suggest",
    },

    # --- Multi-agent dev team (read-only architecture) ---
    {
        "slug": "ai_dev_team_frontend",
        "name": "AI Dev Team — Frontend Agent",
        "category": "development",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "claude_sonnet_4_5",
        "purpose": "Analyzes frontend code, generates recommendations, suggests Emergent prompts.",
        "data_sources": ["admin_ai_findings", "admin_ai_scans"],
        "owner": "Platform Core",
        "permission_level": "suggest",
    },
    {
        "slug": "ai_dev_team_backend",
        "name": "AI Dev Team — Backend Agent",
        "category": "development",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "claude_sonnet_4_5",
        "purpose": "Analyzes backend code, identifies architectural issues, suggests refactors.",
        "data_sources": ["admin_ai_findings", "admin_ai_scans"],
        "owner": "Platform Core",
        "permission_level": "suggest",
    },
    {
        "slug": "ai_dev_team_qa",
        "name": "AI Dev Team — QA Agent",
        "category": "quality",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "claude_sonnet_4_5",
        "purpose": "Code-level QA scans, test coverage analysis.",
        "data_sources": ["admin_ai_findings"],
        "owner": "Platform Core",
        "permission_level": "suggest",
    },
    {
        "slug": "ai_dev_team_security",
        "name": "AI Dev Team — Security Agent",
        "category": "security",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "claude_sonnet_4_5",
        "purpose": "Code-level security review, vulnerability detection.",
        "data_sources": ["admin_ai_findings", "security_ai_runs"],
        "owner": "Platform Core",
        "permission_level": "suggest",
    },

    # --- End-user-facing ---
    {
        "slug": "qa_copilot",
        "name": "QA Copilot",
        "category": "quality",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "claude_sonnet_4_5",
        "purpose": "QA sessions for client/specialist/admin flows, prompt generator.",
        "data_sources": ["qa_sessions"],
        "owner": "Platform Core",
        "permission_level": "suggest",
    },
    {
        "slug": "ai_security_center",
        "name": "AI Security Center",
        "category": "security",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "claude_sonnet_4_5",
        "purpose": "OAuth health, GDPR checks, security scoring, daily security scans.",
        "data_sources": ["security_ai_runs", "admin_ai_findings"],
        "owner": "Platform Core",
        "permission_level": "suggest",
    },
    {
        "slug": "document_intelligence",
        "name": "Document Intelligence",
        "category": "knowledge",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "claude_sonnet_4_5",
        "purpose": "PDF/DOCX/TXT indexing, semantic search, contextual responses with citations.",
        "data_sources": ["ai_documents", "ai_doc_chunks"],
        "owner": "Platform Core",
        "permission_level": "read",
    },
    {
        "slug": "docs_ai_assistant",
        "name": "Admin Docs AI Assistant",
        "category": "knowledge",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "claude_sonnet_4_5",
        "purpose": "Context-aware assistant inside Admin Documentation, generates Emergent prompts.",
        "data_sources": ["ai_messages"],
        "owner": "Platform Core",
        "permission_level": "read",
    },

    # --- Memory & graph ---
    {
        "slug": "knowledge_graph",
        "name": "Knowledge Graph",
        "category": "memory",
        "lifecycle": "active",
        "maturity": "foundation",  # mature foundation but under-utilized
        "provider": "none",
        "purpose": "Entity + relationship graph (Users, Properties, Requests, etc.). Pure data, no LLM calls.",
        "data_sources": ["kg_nodes", "kg_edges"],
        "owner": "Platform Core",
        "permission_level": "read",
    },
    {
        "slug": "cross_session_memory",
        "name": "Cross-Session AI Memory",
        "category": "memory",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "none",
        "purpose": "Persistent memory across user sessions, used by all AI agents for context.",
        "data_sources": ["ai_memories"],
        "owner": "Platform Core",
        "permission_level": "read",
    },
    {
        "slug": "bug_memory_search",
        "name": "Bug Memory Search",
        "category": "quality",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "claude_sonnet_4_5",
        "purpose": "Semantic search across QA findings + AI findings history.",
        "data_sources": ["qa_sessions", "admin_ai_findings"],
        "owner": "Platform Core",
        "permission_level": "read",
    },

    # --- Schedulers & briefings ---
    {
        "slug": "weekly_ai_briefing",
        "name": "Weekly AI Briefing",
        "category": "reporting",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "claude_sonnet_4_5",
        "purpose": "Mondays 09:00 — executive AI report via Resend email.",
        "data_sources": ["ai_weekly_briefing_history", "ai_weekly_briefing_config"],
        "owner": "Platform Core",
        "permission_level": "execute",
    },
    {
        "slug": "future_ideas_digest",
        "name": "Future Ideas Weekly Digest",
        "category": "reporting",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "none",
        "purpose": "Mondays 09:15 — digest of stale proposals + recent decisions via email.",
        "data_sources": ["future_ideas_digest_history"],
        "owner": "Platform Core",
        "permission_level": "execute",
    },
    {
        "slug": "morning_briefing",
        "name": "Morning Briefing",
        "category": "reporting",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "claude_sonnet_4_5",
        "purpose": "Daily 09:00 — operational briefing digest.",
        "data_sources": ["admin_briefing_digest_history"],
        "owner": "Platform Core",
        "permission_level": "execute",
    },

    # --- Engines ---
    {
        "slug": "auto_match_engine",
        "name": "Auto-Match Engine",
        "category": "marketplace",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "none",
        "purpose": "Hourly — matches specialists with requests based on rules + AI scoring.",
        "data_sources": ["auto_match_runs"],
        "owner": "Marketplace",
        "permission_level": "execute",
    },
    {
        "slug": "ai_activity_stream",
        "name": "AI Activity Stream",
        "category": "control_plane",
        "lifecycle": "active",
        "maturity": "mature",
        "provider": "none",
        "purpose": "Operations Center timeline aggregating cross-module AI events.",
        "data_sources": ["ai_activity_log"],
        "owner": "Platform Core",
        "permission_level": "read",
    },

    # --- Legacy (candidates for deprecation per Phase 9) ---
    {
        "slug": "ai_concierge",
        "name": "AI Concierge",
        "category": "concierge",
        "lifecycle": "legacy",
        "maturity": "legacy",
        "provider": "claude_sonnet_4_5",
        "purpose": "Legacy chatbot on Properties. Subutilized — candidate for merge with Document Intelligence.",
        "data_sources": ["concierge_sessions"],
        "owner": "Legacy",
        "permission_level": "read",
    },
    {
        "slug": "ai_investigator",
        "name": "AI Investigator",
        "category": "investigation",
        "lifecycle": "legacy",
        "maturity": "legacy",
        "provider": "claude_sonnet_4_5",
        "purpose": "Legacy investigation agent. Candidate for merge with Security Guardian.",
        "data_sources": [],
        "owner": "Legacy",
        "permission_level": "read",
    },
]


def get_agents() -> list:
    """Return immutable agent list (copies)."""
    return [dict(a) for a in AI_AGENTS]


def get_agent(slug: str) -> dict | None:
    for a in AI_AGENTS:
        if a["slug"] == slug:
            return dict(a)
    return None


def agents_by_category() -> dict:
    grouped: dict = {}
    for a in AI_AGENTS:
        grouped.setdefault(a["category"], []).append(dict(a))
    return grouped


def registry_summary() -> dict:
    """High-level snapshot for dashboard header card."""
    total = len(AI_AGENTS)
    by_lifecycle: dict = {}
    by_category: dict = {}
    by_permission: dict = {}
    for a in AI_AGENTS:
        by_lifecycle[a["lifecycle"]] = by_lifecycle.get(a["lifecycle"], 0) + 1
        by_category[a["category"]] = by_category.get(a["category"], 0) + 1
        by_permission[a["permission_level"]] = by_permission.get(a["permission_level"], 0) + 1
    return {
        "total_agents": total,
        "by_lifecycle": by_lifecycle,
        "by_category": by_category,
        "by_permission_level": by_permission,
        "legacy_candidates": [a["slug"] for a in AI_AGENTS if a["lifecycle"] == "legacy"],
    }
