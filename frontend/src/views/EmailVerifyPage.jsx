// PropManage — Email Verification Landing Page
// Accessed via link from email: /verify-email?token=xyz
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, XCircle, Loader2, Building2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_BACKEND_URL;

export const EmailVerifyPage = () => {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [state, setState] = useState({ loading: true, ok: false, msg: "" });

  useEffect(() => {
    if (!token) {
      setState({ loading: false, ok: false, msg: "Link invalid: token lipsă." });
      return;
    }
    axios.get(`${API}/api/auth/verify-email`, { params: { token } })
      .then(r => setState({ loading: false, ok: true, msg: r.data?.already_verified ? "Emailul era deja confirmat." : "Email confirmat cu succes!" }))
      .catch(e => setState({ loading: false, ok: false, msg: e?.response?.data?.detail || "Eroare la verificare." }));
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[#0a0a0b]">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-[#d4ff3a] blur-[200px] opacity-10 -z-10" />
      <div className="absolute top-6 left-6 z-10">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
            <Building2 className="w-4 h-4 text-black" strokeWidth={2.5} />
          </div>
          <span className="font-serif text-xl font-semibold">PropManage</span>
        </Link>
      </div>
      <div className="glass-strong rounded-3xl p-10 max-w-md w-full text-center" data-testid="email-verify-page">
        {state.loading ? (
          <>
            <Loader2 className="w-12 h-12 text-[#d4ff3a] animate-spin mx-auto mb-4" />
            <div className="text-lg font-semibold">Se verifică...</div>
          </>
        ) : state.ok ? (
          <>
            <CheckCircle2 className="w-14 h-14 text-emerald-400 mx-auto mb-4" data-testid="email-verify-success" />
            <h1 className="font-serif text-3xl mb-2">Email confirmat</h1>
            <p className="text-sm text-stone-400 mb-6">{state.msg}</p>
            <Link to="/login" className="btn-accent inline-block px-6 py-3 rounded-xl text-sm font-medium" data-testid="email-verify-login-link">
              Conectare
            </Link>
          </>
        ) : (
          <>
            <XCircle className="w-14 h-14 text-red-400 mx-auto mb-4" data-testid="email-verify-error" />
            <h1 className="font-serif text-3xl mb-2">Verificare eșuată</h1>
            <p className="text-sm text-stone-400 mb-6">{state.msg}</p>
            <Link to="/login" className="text-[#d4ff3a] hover:underline text-sm">
              Înapoi la login →
            </Link>
          </>
        )}
      </div>
    </div>
  );
};

export default EmailVerifyPage;
