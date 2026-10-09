// Stripe wallet topup — success/cancel handler page.
import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import axios from "axios";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { API } from "./DashShared";

export const PaymentSuccess = () => {
  const [params] = useSearchParams();
  const [status, setStatus] = useState("polling");
  const [amount, setAmount] = useState(null);
  const [err, setErr] = useState(null);
  const sessionId = params.get("session_id");
  const type = params.get("type");

  useEffect(() => {
    if (!sessionId || type !== "topup") return;
    let attempts = 0;
    const poll = async () => {
      try {
        const { data } = await axios.get(`${API}/wallet/topup-status/${sessionId}`);
        setAmount(data.amount);
        if (data.payment_status === "paid") {
          setStatus("paid");
          // Conversie Google Ads + intern: plată reușită (wallet topup / escrow finanțat)
          import("../lib/analytics").then(({ trackConversion }) => trackConversion("purchase", { value: Number(data.amount) || 0 })).catch(() => {});
        } else if (data.status === "expired") {
          setStatus("expired");
        } else if (attempts < 10) {
          attempts++;
          setTimeout(poll, 1500);
        } else {
          setStatus("timeout");
        }
      } catch (e) {
        setErr(e?.response?.data?.detail || "Eroare la verificare.");
        setStatus("error");
      }
    };
    poll();
  }, [sessionId, type]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0b] text-stone-100 p-6">
      <div className="glass-strong rounded-3xl p-10 max-w-md w-full text-center" data-testid="payment-success-page">
        {status === "polling" && (
          <>
            <Loader2 className="w-16 h-16 mx-auto text-[#d4ff3a] animate-spin mb-4" />
            <h2 className="font-serif text-2xl mb-2">Confirmăm plata...</h2>
            <p className="text-sm text-stone-400">Te rugăm așteaptă câteva secunde.</p>
          </>
        )}
        {status === "paid" && (
          <>
            <div className="w-20 h-20 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-12 h-12 text-emerald-400" />
            </div>
            <h2 className="font-serif text-3xl mb-2" data-testid="payment-success-title">Plată confirmată!</h2>
            <p className="text-sm text-stone-400 mb-2">Wallet-ul tău a fost alimentat cu</p>
            <div className="font-serif text-4xl text-[#d4ff3a] mb-6">{amount} RON</div>
            <Link to="/client" className="btn-accent inline-flex px-6 py-3 rounded-full font-medium" data-testid="back-to-dashboard">
              Înapoi la dashboard
            </Link>
          </>
        )}
        {(status === "expired" || status === "timeout") && (
          <>
            <div className="w-20 h-20 rounded-full bg-amber-500/20 flex items-center justify-center mx-auto mb-4">
              <XCircle className="w-12 h-12 text-amber-400" />
            </div>
            <h2 className="font-serif text-2xl mb-2">Sesiune expirată</h2>
            <p className="text-sm text-stone-400 mb-6">Plata nu a fost finalizată în timp util.</p>
            <Link to="/client" className="glass px-6 py-3 rounded-full inline-flex">Înapoi</Link>
          </>
        )}
        {status === "error" && (
          <>
            <XCircle className="w-16 h-16 mx-auto text-red-400 mb-4" />
            <h2 className="font-serif text-2xl mb-2">Eroare</h2>
            <p className="text-sm text-stone-400 mb-6">{err}</p>
            <Link to="/client" className="glass px-6 py-3 rounded-full inline-flex">Înapoi</Link>
          </>
        )}
      </div>
    </div>
  );
};
