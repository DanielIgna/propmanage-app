// PropManage Community Zone (Forum + Groups + FAQ + Reviews)
// Public read, authenticated post.
import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import {
  Building2, MessageSquare, Users, HelpCircle, Star, Plus,
  Heart, Reply, ChevronRight, Search, Pin, Send, X, Sparkles,
} from "lucide-react";
import { useAuth, formatApiError } from "../auth";
import {
  PMCard, PMCardPrimary, PMPillButton, PMChip, PMSectionHeader,
  PMEmptyState, PMTopBar,
} from "../components/pm";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const CATEGORIES = [
  { id: "forum", label: "Forum", icon: MessageSquare, desc: "Discuții deschise între proprietari și specialiști." },
  { id: "groups", label: "Grupuri", icon: Users, desc: "Comunități pe complex / cartier / specialitate." },
  { id: "faq", label: "Întrebări frecvente", icon: HelpCircle, desc: "Răspunsuri verificate de echipa PropManage." },
  { id: "reviews", label: "Recenzii", icon: Star, desc: "Experiențe reale ale utilizatorilor cu specialiști." },
];

export default function CommunityPage() {
  const { user } = useAuth();
  const [activeCat, setActiveCat] = useState("forum");
  const [topics, setTopics] = useState([]);
  const [stats, setStats] = useState({ topics_per_category: {}, total_topics: 0, total_replies: 0 });
  const [searchQ, setSearchQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [openTopic, setOpenTopic] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ category: activeCat });
      if (searchQ) params.set("q", searchQ);
      const [topicsRes, statsRes] = await Promise.all([
        axios.get(`${API}/community/topics?${params}`),
        axios.get(`${API}/community/stats`),
      ]);
      setTopics(topicsRes.data);
      setStats(statsRes.data);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [activeCat]);

  return (
    <div className="pm-page-bg">
      <PMTopBar
        leading={
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-4 h-4 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg font-semibold">PropManage</span>
          </Link>
        }
        title="Comunitate"
        trailing={
          user ? (
            <PMPillButton variant="primary" size="sm" icon={Plus} onClick={() => setShowCreate(true)} testid="community-new-topic">
              Subiect nou
            </PMPillButton>
          ) : (
            <Link to="/login"><PMPillButton variant="primary" size="sm">Conectare</PMPillButton></Link>
          )
        }
      />

      <main className="max-w-6xl mx-auto px-4 md:px-8 py-10">
        {/* Hero */}
        <PMCardPrimary className="mb-8 pm-fade-in" testid="community-hero">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <PMChip variant="primary" className="!bg-[var(--pm-on-primary-container)] !text-[var(--pm-primary-container)] !border-transparent mb-3">
                COMUNITATE PROPMANAGE
              </PMChip>
              <h1 className="font-serif text-3xl md:text-5xl text-[var(--pm-on-primary-container)] mb-2">Întreabă. Învață. Conectează.</h1>
              <p className="text-[var(--pm-on-primary-container)] opacity-80 max-w-xl">
                {stats.total_topics} subiecte · {stats.total_replies} răspunsuri. Comunitatea proprietarilor și specialiștilor verificați.
              </p>
            </div>
            <div className="flex gap-3">
              {!user && <Link to="/register"><PMPillButton variant="on-container">Alătură-te</PMPillButton></Link>}
            </div>
          </div>
        </PMCardPrimary>

        {/* Category tabs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6 pm-fade-in-delay-1">
          {CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            const active = activeCat === cat.id;
            const count = stats.topics_per_category[cat.id] || 0;
            return (
              <button
                key={cat.id}
                onClick={() => setActiveCat(cat.id)}
                data-testid={`community-cat-${cat.id}`}
                className={`pm-card !p-4 text-left transition-all ${active ? "!border-[var(--pm-primary)] !bg-[var(--pm-primary-container)]" : ""}`}
              >
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${active ? "bg-[var(--pm-on-primary-container)]/10 text-[var(--pm-on-primary-container)]" : "bg-[var(--pm-surface-high)] text-[var(--pm-primary)]"}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div className={`font-semibold text-sm ${active ? "text-[var(--pm-on-primary-container)]" : ""}`}>{cat.label}</div>
                <div className={`text-xs mt-1 ${active ? "text-[var(--pm-on-primary-container)]/70" : "text-[var(--pm-text-muted)]"}`}>
                  {count} subiecte
                </div>
              </button>
            );
          })}
        </div>

        {/* Search */}
        <div className="pm-card-glass !p-3 mb-6 pm-fade-in-delay-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-500" />
            <input
              type="text"
              placeholder="Caută în comunitate..."
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && load()}
              className="w-full bg-white/5 border border-white/10 rounded-full pl-10 pr-3 py-2.5 text-sm focus:outline-none focus:border-[var(--pm-primary)]/50 transition-colors"
              data-testid="community-search"
            />
          </div>
        </div>

        {/* Topics list */}
        <PMSectionHeader title={CATEGORIES.find(c => c.id === activeCat)?.label} />
        <div className="space-y-3">
          {loading ? (
            <div className="text-center py-12 text-stone-500 text-sm">Se încarcă...</div>
          ) : topics.length === 0 ? (
            <PMEmptyState
              icon={MessageSquare}
              title="Niciun subiect aici încă"
              description={user ? "Fii primul care deschide o discuție!" : "Conectează-te pentru a porni o conversație."}
              action={user ? (
                <PMPillButton variant="primary" icon={Plus} onClick={() => setShowCreate(true)}>Deschide subiect</PMPillButton>
              ) : (
                <Link to="/login"><PMPillButton variant="primary">Conectare</PMPillButton></Link>
              )}
            />
          ) : (
            topics.map(t => {
              const badgeActive = t.badge === "MEMBER_OF_THE_WEEK" && t.badge_expires_at && new Date(t.badge_expires_at) > new Date();
              return (
              <PMCard
                key={t.id}
                accent={badgeActive ? "primary" : t.pinned ? "primary" : "default"}
                onClick={() => setOpenTopic(t)}
                testid={`community-topic-${t.id}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      {badgeActive && (
                        <PMChip variant="primary" icon={Sparkles} testid={`community-badge-week-${t.id}`}>
                          MEMBRU AL SĂPTĂMÂNII
                        </PMChip>
                      )}
                      {t.pinned && <PMChip variant="primary" icon={Pin}>Fixat</PMChip>}
                      <span className="text-[11px] text-stone-500">
                        {t.author_name} · {t.author_role} · {new Date(t.created_at).toLocaleDateString("ro-RO")}
                      </span>
                    </div>
                    <h3 className="font-semibold text-sm md:text-base mb-1">{t.title}</h3>
                    <p className="text-xs md:text-sm text-stone-400 line-clamp-2">{t.body}</p>
                    <div className="flex items-center gap-4 mt-3 text-xs text-stone-500">
                      <span className="flex items-center gap-1">
                        <Heart className="w-3.5 h-3.5" /> {t.likes_count}
                      </span>
                      <span className="flex items-center gap-1">
                        <Reply className="w-3.5 h-3.5" /> {t.replies_count}
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-stone-600 shrink-0" />
                </div>
              </PMCard>
              );
            })
          )}
        </div>
      </main>

      {showCreate && (
        <CreateTopicModal
          defaultCategory={activeCat}
          onClose={() => setShowCreate(false)}
          onCreated={(t) => { setShowCreate(false); setTopics([t, ...topics]); }}
        />
      )}
      {openTopic && (
        <TopicDetailModal
          topic={openTopic}
          onClose={() => { setOpenTopic(null); load(); }}
        />
      )}
    </div>
  );
}

// ============= CREATE TOPIC MODAL =============
const CreateTopicModal = ({ defaultCategory, onClose, onCreated }) => {
  const [form, setForm] = useState({ category: defaultCategory || "forum", title: "", body: "" });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await axios.post(`${API}/community/topics`, form);
      onCreated(data);
    } catch (err) {
      alert(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-end sm:items-center justify-center p-3" onClick={onClose}>
      <form onSubmit={submit} onClick={e => e.stopPropagation()}
        className="bg-stone-950 border border-white/10 rounded-3xl p-6 w-full max-w-lg space-y-4" data-testid="community-create-modal">
        <div className="flex items-center justify-between">
          <h3 className="font-serif text-2xl">Subiect nou</h3>
          <button type="button" onClick={onClose} className="text-stone-500 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div>
          <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">Categorie</label>
          <select value={form.category} onChange={e => setForm({...form, category: e.target.value})}
            className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2.5 text-sm" data-testid="community-create-category">
            {CATEGORIES.filter(c => c.id !== "reviews").map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">Titlu</label>
          <input required value={form.title} onChange={e => setForm({...form, title: e.target.value})}
            placeholder="Ex: Cum aleg un instalator pentru baie?" minLength={4} maxLength={200}
            className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2.5 text-sm focus:outline-none focus:border-[var(--pm-primary)]/50"
            data-testid="community-create-title"
          />
        </div>
        <div>
          <label className="text-xs uppercase tracking-wider text-stone-400 mb-1.5 block">Mesaj</label>
          <textarea required value={form.body} onChange={e => setForm({...form, body: e.target.value})}
            placeholder="Descrie situația ta, cere sfaturi, povestește o experiență..." minLength={10} maxLength={10000} rows={6}
            className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-sm focus:outline-none focus:border-[var(--pm-primary)]/50 resize-none"
            data-testid="community-create-body"
          />
          <div className="text-[10px] text-stone-500 mt-1">{form.body.length} / 10000 caractere</div>
        </div>
        <div className="flex gap-2 pt-2">
          <button type="button" onClick={onClose} className="pm-pill pm-pill-ghost flex-1">Anulează</button>
          <button type="submit" disabled={busy || form.title.length < 4 || form.body.length < 10} className="pm-pill pm-pill-primary flex-1" data-testid="community-create-submit">
            {busy ? "..." : "Publică"}
          </button>
        </div>
      </form>
    </div>
  );
};

// ============= TOPIC DETAIL MODAL =============
const TopicDetailModal = ({ topic, onClose }) => {
  const { user } = useAuth();
  const [replies, setReplies] = useState([]);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [topicState, setTopicState] = useState(topic);

  useEffect(() => {
    axios.get(`${API}/community/topics/${topic.id}/replies`).then(r => setReplies(r.data)).catch(() => {});
  }, [topic.id]);

  const reply = async (e) => {
    e.preventDefault();
    if (body.length < 2) return;
    setBusy(true);
    try {
      const { data } = await axios.post(`${API}/community/topics/${topic.id}/replies`, { body });
      setReplies([...replies, data]);
      setBody("");
      setTopicState({ ...topicState, replies_count: (topicState.replies_count || 0) + 1 });
    } catch (err) {
      alert(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const toggleLike = async (target_type, target_id) => {
    if (!user) { alert("Conectează-te pentru a aprecia."); return; }
    try {
      const { data } = await axios.post(`${API}/community/likes/toggle`, { target_type, target_id });
      const delta = data.liked ? 1 : -1;
      if (target_type === "topic") {
        setTopicState({ ...topicState, likes_count: (topicState.likes_count || 0) + delta });
      } else {
        setReplies(replies.map(r => r.id === target_id ? { ...r, likes_count: (r.likes_count || 0) + delta } : r));
      }
    } catch (e) {
      // silent fail
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-end sm:items-center justify-center p-3" onClick={onClose}>
      <div onClick={e => e.stopPropagation()}
        className="bg-stone-950 border border-white/10 rounded-3xl w-full max-w-2xl max-h-[90vh] flex flex-col" data-testid="community-topic-modal">
        <div className="p-6 border-b border-white/10 flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              {topicState.badge === "MEMBER_OF_THE_WEEK" && topicState.badge_expires_at && new Date(topicState.badge_expires_at) > new Date() && (
                <PMChip variant="primary" icon={Sparkles}>MEMBRU AL SĂPTĂMÂNII</PMChip>
              )}
              {topicState.pinned && <PMChip variant="primary" icon={Pin}>Fixat</PMChip>}
              <PMChip>{topicState.category}</PMChip>
            </div>
            <h2 className="font-serif text-xl md:text-2xl mb-1">{topicState.title}</h2>
            <div className="text-xs text-stone-500">
              {topicState.author_name} · {new Date(topicState.created_at).toLocaleString("ro-RO")}
            </div>
          </div>
          <button onClick={onClose} className="text-stone-500 hover:text-white shrink-0"><X className="w-5 h-5" /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <p className="text-sm text-stone-200 whitespace-pre-wrap">{topicState.body}</p>
          <div className="flex items-center gap-3">
            <button onClick={() => toggleLike("topic", topicState.id)} className="pm-pill pm-pill-ghost pm-pill-sm" data-testid="community-like-topic">
              <Heart className="w-3.5 h-3.5" /> {topicState.likes_count}
            </button>
          </div>

          <div className="border-t border-white/10 pt-4">
            <div className="text-xs uppercase tracking-wider text-stone-500 mb-3">{replies.length} răspunsuri</div>
            {replies.map(r => (
              <div key={r.id} className="pm-card !p-4 mb-3" data-testid={`community-reply-${r.id}`}>
                <div className="flex items-center gap-2 mb-2 text-xs text-stone-500">
                  <span className="font-semibold text-stone-300">{r.author_name}</span>
                  <span>·</span>
                  <span>{r.author_role}</span>
                  <span>·</span>
                  <span>{new Date(r.created_at).toLocaleString("ro-RO")}</span>
                </div>
                <p className="text-sm whitespace-pre-wrap">{r.body}</p>
                <button onClick={() => toggleLike("reply", r.id)} className="mt-2 pm-pill pm-pill-ghost pm-pill-sm">
                  <Heart className="w-3 h-3" /> {r.likes_count}
                </button>
              </div>
            ))}
          </div>
        </div>

        {user ? (
          <form onSubmit={reply} className="p-4 border-t border-white/10 flex gap-2">
            <input value={body} onChange={e => setBody(e.target.value)}
              placeholder="Scrie un răspuns..." minLength={2} maxLength={5000}
              className="flex-1 bg-white/5 border border-white/10 rounded-full px-4 py-2.5 text-sm focus:outline-none focus:border-[var(--pm-primary)]/50"
              data-testid="community-reply-input"
            />
            <button type="submit" disabled={busy || body.length < 2} className="pm-pill pm-pill-primary" data-testid="community-reply-submit">
              {busy ? "..." : <><Send className="w-4 h-4" /> Trimite</>}
            </button>
          </form>
        ) : (
          <div className="p-4 border-t border-white/10 text-center text-sm text-stone-400">
            <Link to="/login" className="text-[var(--pm-primary)] hover:underline">Conectează-te</Link> pentru a răspunde.
          </div>
        )}
      </div>
    </div>
  );
};
