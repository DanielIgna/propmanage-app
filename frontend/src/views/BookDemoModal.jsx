// BookDemoModal — simple lead capture for landing page CTA.
import React, { useState } from "react";
import axios from "axios";
import { X, Calendar, CheckCircle2 } from "lucide-react";
import { API } from "./DashShared";
import { trackLeadFormConversion } from "../lib/analytics";

export const BookDemoModal = ({ open, onClose }) => {
  const [form, setForm] = useState({ name: "", email: "", whatsapp: "", company: "", role: "", message: "" });
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);

  if (!open) return null;

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!form.name.trim() || !form.email.trim()) {
      setError("Numele și emailul sunt obligatorii.");
      return;
    }
    setSubmitting(true);
    try {
      await axios.post(`${API}/public/demo-request`, form);
      setSent(true);
      trackLeadFormConversion(); // Google Ads lead-form conversion (după succes)
    } catch (err) {
      setError(err?.response?.data?.detail || "Eroare. Încearcă din nou.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[90] bg-black/80 backdrop-blur-md flex items-center justify-center p-4"
      onClick={onClose}
      data-testid="book-demo-modal"
    >
      <div
        className="bg-gradient-to-br from-stone-900 to-stone-950 border border-[#d4ff3a]/30 rounded-3xl max-w-md w-full p-8 shadow-2xl relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 hover:bg-white/5 rounded-full"
          data-testid="book-demo-close"
          aria-label="Închide"
        >
          <X className="w-4 h-4 text-stone-400" />
        </button>

        {sent ? (
          <div className="text-center py-6" data-testid="book-demo-success">
            <CheckCircle2 className="w-16 h-16 mx-auto text-[#d4ff3a] mb-4" />
            <h2 className="font-serif text-3xl text-white mb-3">Mulțumim!</h2>
            <p className="text-stone-300 mb-6">Te contactăm în maxim 24h pe email-ul <span className="text-[#d4ff3a]">{form.email}</span>.</p>
            <button onClick={onClose} className="btn-accent px-6 py-2.5 rounded-full font-medium" data-testid="book-demo-close-success">
              Mai ales
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 mb-2">
              <Calendar className="w-4 h-4 text-[#d4ff3a]" />
              <span className="text-[10px] uppercase tracking-wider text-[#d4ff3a]">Demonstrație live · 30 min</span>
            </div>
            <h2 className="font-serif text-3xl text-white mb-2">Vrei să vezi PropManage live?</h2>
            <p className="text-stone-400 text-sm mb-6">Completează formularul și îți vom arăta cum funcționează platforma pentru tine.</p>

            <form onSubmit={submit} className="space-y-3">
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Numele tău *"
                required
                className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-[#d4ff3a] outline-none text-white text-sm"
                data-testid="book-demo-name"
              />
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="Email *"
                required
                className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-[#d4ff3a] outline-none text-white text-sm"
                data-testid="book-demo-email"
              />
              <input
                type="tel"
                value={form.whatsapp}
                onChange={(e) => setForm({ ...form, whatsapp: e.target.value })}
                placeholder="WhatsApp / telefon (opțional, +40...)"
                className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-[#25d366] outline-none text-white text-sm"
                data-testid="book-demo-whatsapp"
              />
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="text"
                  value={form.company}
                  onChange={(e) => setForm({ ...form, company: e.target.value })}
                  placeholder="Companie"
                  className="px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-[#d4ff3a] outline-none text-white text-sm"
                  data-testid="book-demo-company"
                />
                <input
                  type="text"
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                  placeholder="Rol"
                  className="px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-[#d4ff3a] outline-none text-white text-sm"
                  data-testid="book-demo-role"
                />
              </div>
              <textarea
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                placeholder="Ce te interesează? (opțional)"
                rows={3}
                className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-[#d4ff3a] outline-none text-white text-sm resize-none"
                data-testid="book-demo-message"
              />

              {error && (
                <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2" data-testid="book-demo-error">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="btn-accent w-full py-3 rounded-full font-medium disabled:opacity-50"
                data-testid="book-demo-submit"
              >
                {submitting ? "Se trimite..." : "Trimite cererea"}
              </button>
              <p className="text-[10px] text-stone-500 text-center mt-2">Datele tale sunt private. Te contactăm doar pentru această demonstrație.</p>
            </form>
          </>
        )}
      </div>
    </div>
  );
};

export default BookDemoModal;
