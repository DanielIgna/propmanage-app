// Digital Twin viewer — Phase E + H + I pin system (3D markers, draft modal, thread modal, issue report).
import React, { useEffect, useState } from "react";
import * as THREE from "three";
import axios from "axios";
import { Html } from "@react-three/drei";
import { X, Trash2, MessageCircle, Send, FileText, Eye, Loader2 } from "lucide-react";
import { API } from "../../views/DashShared";
import { CATEGORY_COLORS, STATUS_LABEL } from "./constants";

// 3D Pin marker on the model (Phase E + H highlight)
export const PinMarker = ({ pin, onOpen, isHighlighted }) => {
  const color = CATEGORY_COLORS[pin.category] || "#60a5fa";
  return (
    <group position={[pin.position.x, pin.position.y, pin.position.z]}>
      <mesh
        onClick={(e) => {
          e.stopPropagation();
          onOpen(pin);
        }}
      >
        <sphereGeometry args={[isHighlighted ? 0.2 : 0.12, 20, 20]} />
        <meshBasicMaterial color={color} />
      </mesh>
      {isHighlighted && (
        <mesh>
          <ringGeometry args={[0.3, 0.4, 32]} />
          <meshBasicMaterial color="#ffffff" side={THREE.DoubleSide} transparent opacity={0.85} />
        </mesh>
      )}
      <Html distanceFactor={10} position={[0, 0.25, 0]} center style={{ pointerEvents: "none" }}>
        <div
          className={`px-2 py-0.5 rounded-full text-[10px] text-white whitespace-nowrap shadow-lg font-medium ${isHighlighted ? "ring-2 ring-white scale-110" : ""}`}
          style={{ background: color }}
        >
          #{pin.title.slice(0, 16)}{pin.title.length > 16 ? "…" : ""}
        </div>
      </Html>
    </group>
  );
};

// Draft modal — when user clicks model in pin mode, capture title/desc/category/priority.
export const PinDraftModal = ({ draft, setDraft, onCancel, onSubmit }) => (
  <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onCancel}>
    <div
      onClick={(e) => e.stopPropagation()}
      className="bg-stone-900 border border-white/10 rounded-2xl p-5 w-full max-w-md"
      data-testid="dt-pin-draft-modal"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-400/80 font-semibold">Pin nou</div>
          <h3 className="font-serif text-lg text-white">Notă pe model 3D</h3>
          <div className="text-[10px] text-stone-500 font-mono mt-1">
            Pos: x={draft.position.x} y={draft.position.y} z={draft.position.z}
          </div>
        </div>
        <button onClick={onCancel} className="text-stone-500 hover:text-white"><X className="w-5 h-5" /></button>
      </div>

      <div className="space-y-3 text-sm">
        <input
          autoFocus
          value={draft.title}
          onChange={(e) => setDraft({ ...draft, title: e.target.value })}
          placeholder="Titlu scurt (ex: Crăpătură perete bucătărie)"
          maxLength={200}
          className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
          data-testid="dt-pin-title"
        />
        <textarea
          rows={3}
          value={draft.description}
          onChange={(e) => setDraft({ ...draft, description: e.target.value })}
          placeholder="Detalii (opțional, max 2000 caractere)"
          maxLength={2000}
          className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white"
          data-testid="dt-pin-description"
        />
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[10px] uppercase text-stone-500 font-semibold">Categorie</label>
            <select
              value={draft.category}
              onChange={(e) => setDraft({ ...draft, category: e.target.value })}
              className="w-full mt-1 bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white"
              data-testid="dt-pin-category"
            >
              {Object.keys(CATEGORY_COLORS).map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] uppercase text-stone-500 font-semibold">Prioritate</label>
            <select
              value={draft.priority}
              onChange={(e) => setDraft({ ...draft, priority: e.target.value })}
              className="w-full mt-1 bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white"
              data-testid="dt-pin-priority"
            >
              <option value="low">Scăzută</option>
              <option value="normal">Normală</option>
              <option value="high">Ridicată</option>
              <option value="urgent">Urgentă</option>
            </select>
          </div>
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <button onClick={onCancel} className="flex-1 px-3 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-stone-300">
          Anulează
        </button>
        <button
          onClick={onSubmit}
          disabled={!draft.title.trim()}
          className="flex-1 px-3 py-2 text-sm rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-medium"
          data-testid="dt-pin-submit"
        >
          Salvează pin
        </button>
      </div>
    </div>
  </div>
);

// Issue Report modal — Phase I. Sends PDF report to recipient with optional 3D screenshot.
const IssueReportModal = ({ pin, screenshot3d, onClose, onSent }) => {
  const [recipient, setRecipient] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const send = async () => {
    setBusy(true);
    setErr(null);
    try {
      const payload = {
        recipient_email: recipient.trim() || null,
        custom_message: message.trim() || null,
        screenshot_3d: screenshot3d || null,
        include_thread: true,
      };
      const { data } = await axios.post(`${API}/digital-twin/pins/${pin.id}/issue-report`, payload);
      onSent?.(data.report);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  const preview = async () => {
    setPreviewLoading(true);
    try {
      // For preview, we use GET with screenshot in query is too long; just open in new tab without screenshot
      const url = `${API}/digital-twin/pins/${pin.id}/issue-report/preview`;
      window.open(url, "_blank");
    } catch (e) {
      setErr(e.message);
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[55] bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-stone-900 border border-white/10 rounded-2xl p-5 w-full max-w-md space-y-3"
        data-testid="dt-issue-report-modal"
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-[#d4ff3a]/90 font-semibold">Raport oficial</div>
            <h3 className="font-serif text-lg text-white">Trimite raport problemă</h3>
            <p className="text-xs text-stone-400 mt-0.5 max-w-[300px]">PDF cu detalii, captură 3D, plan 2D ancorat (dacă există) + thread comentarii.</p>
          </div>
          <button onClick={onClose} className="text-stone-500 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        <div>
          <label className="text-[10px] uppercase text-stone-500 font-semibold">Destinatar (opțional)</label>
          <input
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            placeholder="Lasă gol pentru proprietarul proiectului"
            type="email"
            className="w-full mt-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            data-testid="dt-report-recipient"
          />
        </div>

        <div>
          <label className="text-[10px] uppercase text-stone-500 font-semibold">Mesaj suplimentar (opțional)</label>
          <textarea
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ex: Te rog verifică această crăpătură urgent — afectează structura clădirii?"
            maxLength={4000}
            className="w-full mt-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            data-testid="dt-report-message"
          />
        </div>

        <div className="text-[11px] text-stone-500 space-y-0.5 border border-white/5 rounded-lg p-2.5 bg-white/[0.02]">
          <div>📌 Pin: <strong className="text-stone-300">{pin.title}</strong></div>
          <div>📷 Captură 3D: {screenshot3d ? <strong className="text-emerald-400">incluse</strong> : <span className="text-stone-500">fără</span>}</div>
          <div>📐 Plan 2D ancorat: {(pin.plan_anchors || []).length > 0 ? <strong className="text-emerald-400">{pin.plan_anchors[0].plan_title}</strong> : <span className="text-stone-500">fără ancoră</span>}</div>
          <div>💬 Comentarii: <strong className="text-stone-300">{pin.comment_count || 0}</strong></div>
        </div>

        {err && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2">{err}</div>}

        <div className="flex gap-2 pt-1">
          <button
            onClick={preview}
            disabled={previewLoading}
            className="px-3 py-2 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-stone-300 flex items-center gap-1.5"
            data-testid="dt-report-preview"
          >
            {previewLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}
            Previzualizare PDF
          </button>
          <button
            onClick={send}
            disabled={busy}
            className="flex-1 px-3 py-2 text-sm rounded-lg bg-[#d4ff3a] hover:bg-[#c5f02e] disabled:opacity-50 text-black font-medium flex items-center justify-center gap-1.5"
            data-testid="dt-report-send"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            {busy ? "Se trimite…" : "Trimite raport"}
          </button>
        </div>
      </div>
    </div>
  );
};


// Thread modal — open an existing pin to see/post comments + change status / delete.
export const PinThreadModal = ({ pin, onClose, onDelete, onStatusChange, onRequestScreenshot }) => {
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [screenshot3d, setScreenshot3d] = useState(null);
  const [reportSent, setReportSent] = useState(null);

  useEffect(() => {
    setLoading(true);
    axios.get(`${API}/digital-twin/pins/${pin.id}/comments`)
      .then(r => setComments(r.data.items || []))
      .catch(() => setComments([]))
      .finally(() => setLoading(false));
  }, [pin.id]);

  const send = async () => {
    if (!text.trim()) return;
    setSending(true);
    try {
      const { data } = await axios.post(`${API}/digital-twin/pins/${pin.id}/comments`, { message: text.trim() });
      setComments((arr) => [...arr, data]);
      setText("");
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    } finally {
      setSending(false);
    }
  };

  const color = CATEGORY_COLORS[pin.category] || "#60a5fa";

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-stone-900 border border-white/10 rounded-2xl w-full max-w-lg flex flex-col max-h-[85vh]"
        data-testid="dt-pin-thread-modal"
      >
        {/* Header */}
        <div className="px-5 pt-5 pb-3 border-b border-white/10">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0 flex-1">
              <div className="w-9 h-9 rounded-full shrink-0 mt-0.5" style={{ background: color }} />
              <div className="min-w-0 flex-1">
                <h3 className="font-semibold text-white text-base truncate">{pin.title}</h3>
                <div className="flex flex-wrap gap-2 mt-1 text-[10px]">
                  <span className="px-2 py-0.5 rounded-full uppercase font-bold tracking-wider" style={{ background: `${color}25`, color }}>
                    {pin.category}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-white/5 text-stone-400 uppercase font-bold tracking-wider">
                    {pin.priority}
                  </span>
                  <span className="text-stone-500">
                    {pin.author_name} · {new Date(pin.created_at).toLocaleDateString("ro-RO")}
                  </span>
                </div>
              </div>
            </div>
            <button onClick={onClose} className="text-stone-500 hover:text-white shrink-0"><X className="w-5 h-5" /></button>
          </div>

          {pin.description && (
            <p className="mt-3 text-sm text-stone-300 leading-relaxed">{pin.description}</p>
          )}

          <div className="mt-3 flex flex-wrap gap-1.5">
            {["open", "in_review", "resolved", "rejected"].map((s) => (
              <button
                key={s}
                onClick={() => onStatusChange(s)}
                className={`px-2.5 py-1 rounded-full text-[10px] uppercase font-bold tracking-wider ${
                  pin.status === s
                    ? "bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-400/30"
                    : "bg-white/5 text-stone-400 hover:bg-white/10"
                }`}
                data-testid={`dt-pin-status-${s}`}
              >
                {STATUS_LABEL[s]}
              </button>
            ))}
            <button
              onClick={async () => {
                // Capture canvas before opening modal
                if (onRequestScreenshot) {
                  const dataUrl = await onRequestScreenshot();
                  setScreenshot3d(dataUrl);
                }
                setShowReport(true);
              }}
              className="ml-auto px-2.5 py-1 rounded-full text-[10px] uppercase font-bold tracking-wider bg-[#d4ff3a]/15 hover:bg-[#d4ff3a]/25 text-[#d4ff3a] flex items-center gap-1"
              data-testid="dt-pin-issue-report-btn"
              title="Trimite PDF raport către arhitect / proprietar"
            >
              <FileText className="w-3 h-3" /> Trimite raport
            </button>
            <button
              onClick={onDelete}
              className="px-2.5 py-1 rounded-full text-[10px] uppercase font-bold tracking-wider bg-red-500/10 hover:bg-red-500/20 text-red-300 flex items-center gap-1"
              data-testid="dt-pin-delete"
            >
              <Trash2 className="w-3 h-3" /> Șterge
            </button>
          </div>
        </div>

        {reportSent && (
          <div className="mx-5 mt-3 px-3 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[11px] text-emerald-200" data-testid="dt-report-success">
            ✅ Raport trimis către <strong>{reportSent.recipient_email}</strong> · {Math.round(reportSent.pdf_size_bytes / 1024)} KB
            {reportSent.has_screenshot && " · cu captură 3D"}
            {reportSent.has_plan_extract && " · cu extract 2D"}
          </div>
        )}

        {/* Comments thread */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3 min-h-[120px]">
          {loading && <div className="text-xs text-stone-500">Se încarcă...</div>}
          {!loading && comments.length === 0 && (
            <div className="text-center text-xs text-stone-500 py-8">
              <MessageCircle className="w-6 h-6 mx-auto mb-2 opacity-50" />
              Niciun comentariu încă. Începe conversația.
            </div>
          )}
          {comments.map((c) => (
            <div key={c.id} className="flex gap-3" data-testid={`dt-comment-${c.id}`}>
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center text-[10px] font-bold text-white shrink-0">
                {(c.author_name || "?").slice(0, 1).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2 mb-0.5">
                  <span className="text-xs font-medium text-stone-200 truncate">{c.author_name}</span>
                  <span className="text-[10px] text-stone-500 uppercase">{c.author_role}</span>
                  <span className="text-[10px] text-stone-500 ml-auto">
                    {new Date(c.created_at).toLocaleString("ro-RO", { dateStyle: "short", timeStyle: "short" })}
                  </span>
                </div>
                <div className="text-sm text-stone-300 whitespace-pre-wrap leading-relaxed">{c.message}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Compose */}
        <div className="border-t border-white/10 px-5 py-3 flex gap-2">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Scrie un comentariu..."
            className="flex-1 bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white"
            data-testid="dt-comment-input"
          />
          <button
            onClick={send}
            disabled={!text.trim() || sending}
            className="px-4 py-2 rounded-full bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white text-sm font-medium flex items-center gap-1"
            data-testid="dt-comment-send"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

      {showReport && (
        <IssueReportModal
          pin={pin}
          screenshot3d={screenshot3d}
          onClose={() => setShowReport(false)}
          onSent={(report) => {
            setReportSent(report);
            setShowReport(false);
            setScreenshot3d(null);
          }}
        />
      )}
    </div>
  );
};
