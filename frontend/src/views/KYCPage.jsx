// KYC Page — specialist uploads ID front + back + selfie for identity verification.
// Design matches AdminCard/PMCard: light cards, violet/emerald accents, drag&drop.
import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Upload, Camera, ShieldCheck, X, FileImage, CheckCircle2, Clock, AlertTriangle, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

const STATUS_TONE = {
  not_started: { bg: "bg-slate-100 dark:bg-slate-800",        text: "text-slate-600 dark:text-slate-300",   icon: Upload,        label: "NEÎNCEPUT" },
  uploaded:    { bg: "bg-amber-100 dark:bg-amber-500/15",     text: "text-amber-700 dark:text-amber-300",  icon: Clock,         label: "ÎN AȘTEPTARE" },
  reviewing:   { bg: "bg-cyan-100 dark:bg-cyan-500/15",       text: "text-cyan-700 dark:text-cyan-300",    icon: RefreshCw,     label: "ÎN REVIZIE" },
  approved:    { bg: "bg-emerald-100 dark:bg-emerald-500/15", text: "text-emerald-700 dark:text-emerald-300", icon: CheckCircle2, label: "APROBAT" },
  rejected:    { bg: "bg-red-100 dark:bg-red-500/15",         text: "text-red-700 dark:text-red-300",      icon: AlertTriangle, label: "RESPINS" },
};

const DropZone = ({ label, value, onChange, testid, icon: Icon = FileImage }) => {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const readFile = (file) => {
    if (!file) return;
    if (file.size > 4_500_000) {
      alert("Fișierul depășește 3MB. Comprimă imaginea și încearcă din nou.");
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => onChange(e.target.result);
    reader.readAsDataURL(file);
  };

  return (
    <div className="space-y-2">
      <label className="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-medium flex items-center gap-1.5">
        <Icon className="w-3.5 h-3.5" />
        {label}
      </label>
      <div
        className={`relative rounded-xl border-2 border-dashed transition-all ${
          dragging
            ? "border-violet-500 bg-violet-50 dark:bg-violet-500/10"
            : value
              ? "border-emerald-300 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-500/5"
              : "border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/30 hover:border-violet-400"
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          readFile(e.dataTransfer.files?.[0]);
        }}
        onClick={() => inputRef.current?.click()}
        data-testid={testid}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/heic"
          className="hidden"
          onChange={(e) => readFile(e.target.files?.[0])}
        />
        {value ? (
          <div className="relative p-2">
            <img
              src={value}
              alt={label}
              className="w-full h-48 object-cover rounded-lg"
              data-testid={`${testid}-preview`}
            />
            <button
              onClick={(e) => { e.stopPropagation(); onChange(""); }}
              className="absolute top-3 right-3 w-7 h-7 rounded-full bg-red-500 hover:bg-red-600 text-white flex items-center justify-center"
              data-testid={`${testid}-remove`}
            >
              <X className="w-3.5 h-3.5" />
            </button>
            <div className="absolute bottom-3 left-3 text-[10px] font-medium px-2 py-1 rounded-full bg-emerald-500 text-white flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" />
              Încărcat
            </div>
          </div>
        ) : (
          <div className="py-12 px-4 text-center cursor-pointer">
            <Upload className="w-8 h-8 mx-auto text-slate-400 dark:text-slate-600 mb-2" />
            <div className="text-sm font-medium text-slate-700 dark:text-slate-200">Trage fișierul aici sau click</div>
            <div className="text-[11px] text-slate-500 mt-1">JPG, PNG, WebP · max 3MB</div>
          </div>
        )}
      </div>
    </div>
  );
};

export default function KYCPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  const [idFront, setIdFront] = useState("");
  const [idBack, setIdBack] = useState("");
  const [selfie, setSelfie] = useState("");
  const [fullName, setFullName] = useState("");
  const [cnp, setCnp] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/kyc/status`);
      setStatus(r.data);
    } catch (e) {
      if (e.response?.status === 401) navigate("/login?next=/kyc");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    if (!idFront || !idBack || !selfie) {
      alert("Te rog încarcă toate cele 3 documente (buletin față + verso + selfie).");
      return;
    }
    if (!fullName || fullName.length < 3) {
      alert("Te rog completează numele complet așa cum apare pe buletin.");
      return;
    }
    setSubmitting(true);
    try {
      await axios.post(`${API}/kyc/upload`, {
        id_front: idFront,
        id_back: idBack,
        selfie,
        full_name_on_id: fullName,
        national_id_number: cnp || null,
      });
      setIdFront(""); setIdBack(""); setSelfie(""); setFullName(""); setCnp("");
      await load();
    } catch (e) {
      alert(e.response?.data?.detail || "Eroare la submit");
    } finally {
      setSubmitting(false);
    }
  };

  const tone = STATUS_TONE[status?.status || "not_started"];
  const StatusIcon = tone.icon;
  const canUpload = status?.can_upload !== false && ["not_started", "rejected"].includes(status?.status || "not_started");

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="text-slate-500">Se încarcă statusul KYC…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 py-10 px-4">
      <div className="max-w-3xl mx-auto" data-testid="kyc-page">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate(-1)}
            className="text-xs text-slate-500 hover:text-violet-500 mb-3"
            data-testid="kyc-back"
          >
            ← Înapoi
          </button>
          <h1 className="font-serif text-3xl sm:text-4xl mb-1 flex items-center gap-3">
            <ShieldCheck className="w-7 h-7 text-violet-500" />
            Verificare Identitate
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Trimite buletinul (față + verso) și un selfie pentru a primi badge-ul <strong>VERIFIED</strong>.
          </p>
        </div>

        {/* Status banner */}
        <div className={`rounded-2xl border p-4 mb-6 flex items-center gap-3 ${tone.bg} border-transparent`} data-testid="kyc-status-banner">
          <StatusIcon className={`w-5 h-5 ${tone.text}`} />
          <div className="flex-1">
            <div className={`text-xs font-bold uppercase tracking-wider ${tone.text}`}>Status: {tone.label}</div>
            {status?.submitted_at && (
              <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                Trimis: {new Date(status.submitted_at).toLocaleString("ro-RO")}
              </div>
            )}
            {status?.reviewed_at && (
              <div className="text-[11px] text-slate-500 dark:text-slate-400">
                Revizuit: {new Date(status.reviewed_at).toLocaleString("ro-RO")}
                {status.reviewed_by_email && ` de ${status.reviewed_by_email}`}
              </div>
            )}
            {status?.review_note && (
              <div className="text-xs mt-2 p-2 rounded-lg bg-white/60 dark:bg-black/30 italic">
                "{status.review_note}"
              </div>
            )}
          </div>
          {status?.verified_in_user_doc && (
            <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-emerald-500 text-white">
              CONT VERIFIED ✓
            </span>
          )}
        </div>

        {/* Upload form */}
        {canUpload ? (
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 space-y-6" data-testid="kyc-upload-form">
            <div>
              <h2 className="font-serif text-lg mb-1">1. Date personale</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">Trebuie să se potrivească cu numele de pe buletin.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">Nume complet *</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Maria Popescu"
                    className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm"
                    data-testid="kyc-fullname"
                  />
                </div>
                <div>
                  <label className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">CNP (opțional, masked)</label>
                  <input
                    type="text"
                    value={cnp}
                    onChange={(e) => setCnp(e.target.value.replace(/[^0-9]/g, "").slice(0, 13))}
                    placeholder="1980101******"
                    className="w-full mt-1 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm font-mono"
                    data-testid="kyc-cnp"
                  />
                  <div className="text-[10px] text-slate-500 mt-1">Stocat doar masked: 123******45</div>
                </div>
              </div>
            </div>

            <div>
              <h2 className="font-serif text-lg mb-3">2. Documente</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <DropZone label="Buletin · Față" value={idFront} onChange={setIdFront} testid="kyc-id-front" icon={FileImage} />
                <DropZone label="Buletin · Verso" value={idBack} onChange={setIdBack} testid="kyc-id-back" icon={FileImage} />
                <DropZone label="Selfie cu buletin" value={selfie} onChange={setSelfie} testid="kyc-selfie" icon={Camera} />
              </div>
              <div className="mt-3 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                ℹ️ Asigură-te că textul de pe buletin e clar lizibil. Selfie-ul trebuie să te arate ținând buletinul lângă față.
                Datele sunt criptate și folosite doar pentru verificare.
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-200 dark:border-slate-700">
              <button
                onClick={() => { setIdFront(""); setIdBack(""); setSelfie(""); setFullName(""); setCnp(""); }}
                className="text-sm px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300"
                data-testid="kyc-reset"
              >
                Resetează
              </button>
              <button
                onClick={submit}
                disabled={submitting || !idFront || !idBack || !selfie || !fullName}
                className="text-sm px-5 py-2.5 rounded-lg bg-violet-500 text-white hover:bg-violet-600 disabled:opacity-50 flex items-center gap-2 font-medium"
                data-testid="kyc-submit"
              >
                <ShieldCheck className="w-4 h-4" />
                {submitting ? "Se trimite…" : "Trimite pentru verificare"}
              </button>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 text-center" data-testid="kyc-locked">
            <div className="text-sm text-slate-700 dark:text-slate-200 mb-2">
              {status?.status === "approved"
                ? "🎉 Identitatea ta a fost verificată cu succes."
                : "📋 Documentele tale sunt în review. Te anunțăm pe email când e gata."}
            </div>
            {status?.status === "approved" && (
              <button
                onClick={() => navigate("/specialist")}
                className="mt-3 text-sm px-5 py-2.5 rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 font-medium"
                data-testid="kyc-back-to-dashboard"
              >
                Înapoi la dashboard
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
