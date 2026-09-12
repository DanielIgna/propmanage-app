// ServiceProvidersPage — pagina publică a serviciilor cu destinație externă (/servicii/:id).
// Listează partenerii administrați din Admin → Menu Manager (nume, logo, descriere, URL, prioritate).
import React, { useEffect, useState } from "react";
import { useParams, Link, Navigate } from "react-router-dom";
import axios from "axios";
import { ArrowLeft, ExternalLink, Store, Sparkles } from "lucide-react";
import { SiteNav } from "../components/SiteNav";
import { EcosystemFlow } from "../components/ecosystem/EcosystemFlow";
import { NextStep } from "../components/ecosystem/NextStep";

const API = process.env.REACT_APP_BACKEND_URL;

export default function ServiceProvidersPage() {
  const { id } = useParams();
  const [svc, setSvc] = useState(undefined); // undefined=loading, null=indisponibil

  useEffect(() => {
    setSvc(undefined);
    axios.get(`${API}/api/public/services/${id}`)
      .then((r) => setSvc(r.data))
      .catch(() => setSvc(null));
  }, [id]);

  useEffect(() => {
    if (svc?.label) document.title = `${svc.label} · Parteneri verificați | PropManage`;
  }, [svc]);

  if (svc === null) return <Navigate to="/" replace />;

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-white" data-testid="service-providers-page">
      <SiteNav />
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pt-28 pb-16">
        <Link to="/" className="text-stone-500 hover:text-white inline-flex items-center gap-1.5 text-sm mb-8" data-testid="svc-back-home">
          <ArrowLeft className="w-4 h-4" /> Acasă
        </Link>
        {svc === undefined ? (
          <div className="py-24 flex justify-center"><div className="w-6 h-6 border-2 border-stone-600 border-t-[#d4ff3a] rounded-full animate-spin" /></div>
        ) : (
          <>
            <div className="inline-flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[#d4ff3a] bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 px-3 py-1 rounded-full mb-4">
              <Store className="w-3 h-3" /> Parteneri verificați PropManage
            </div>
            <h1 className="font-serif text-4xl sm:text-5xl mb-3" data-testid="svc-title">{svc.label}</h1>
            <p className="text-stone-400 max-w-2xl mb-10">{svc.description}</p>

            {svc.providers.length > 0 ? (
              <div className="grid sm:grid-cols-2 gap-4 mb-12" data-testid="svc-providers-grid">
                {svc.providers.map((p, i) => (
                  <div key={i} className="p-6 rounded-3xl bg-[#0e0e10] border border-white/10 hover:border-[#d4ff3a]/40 transition-colors flex flex-col gap-3" data-testid={`svc-provider-${i}`}>
                    <div className="flex items-center gap-3">
                      {p.logo ? (
                        <img src={p.logo} alt={p.name} className="w-12 h-12 rounded-2xl object-cover bg-white/5" />
                      ) : (
                        <div className="w-12 h-12 rounded-2xl bg-[#d4ff3a]/10 border border-[#d4ff3a]/30 flex items-center justify-center">
                          <Store className="w-5 h-5 text-[#d4ff3a]" />
                        </div>
                      )}
                      <h3 className="font-bold text-lg">{p.name}</h3>
                    </div>
                    {p.description && <p className="text-sm text-stone-400 leading-relaxed">{p.description}</p>}
                    {p.url && (
                      <a href={p.url} target="_blank" rel="noopener noreferrer"
                        className="mt-auto self-start px-5 py-2.5 rounded-full bg-[#d4ff3a] text-black text-sm font-bold inline-flex items-center gap-1.5 hover:opacity-90 transition-opacity"
                        data-testid={`svc-provider-link-${i}`}>
                        Vizitează <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-10 rounded-3xl bg-[#0e0e10] border border-dashed border-white/15 text-center mb-12" data-testid="svc-no-providers">
                <Sparkles className="w-8 h-8 text-[#d4ff3a] mx-auto mb-3" />
                <p className="font-bold text-lg mb-1">Selectăm partenerii potriviți</p>
                <p className="text-sm text-stone-400 mb-6 max-w-md mx-auto">
                  Lucrăm doar cu parteneri validați. Între timp, spune-ne ce ai nevoie și te punem în legătură directă.
                </p>
                <Link to="/design-interior#lead" className="px-6 py-3 rounded-full bg-[#d4ff3a] text-black text-sm font-bold" data-testid="svc-lead-cta">
                  Cere ofertă →
                </Link>
              </div>
            )}

            <div className="p-5 rounded-3xl bg-white/[0.03] border border-white/10 mb-8">
              <EcosystemFlow dark compact />
            </div>
            <NextStep
              dark
              title="Începe procesul complet: Audit + Digital Twin"
              desc="Mobilierul perfect pornește de la măsurători exacte. Cu Digital Twin, partenerii lucrează pe planurile reale ale locuinței tale."
              to="/imobile-verificate/sell"
              cta="Începe cu un audit"
            />
          </>
        )}
      </section>
    </div>
  );
}
