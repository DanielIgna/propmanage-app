// Public tokenized doc viewer at /help/{token}
// Accessible without login. Renders the doc using the shared DocViewer component.
import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { Building2, AlertCircle } from "lucide-react";
import DocViewer from "../components/DocViewer";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

export const HelpPage = () => {
  const { token } = useParams();
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/help/${token}`)
      .then(r => setDoc(r.data.doc))
      .catch(() => setError("Link invalid sau expirat. Cere administratorului tău un link nou."))
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-stone-100">
      <header className="border-b border-white/5 sticky top-0 z-30 bg-[#0a0a0b]/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#d4ff3a] to-[#a8e028] flex items-center justify-center">
              <Building2 className="w-3.5 h-3.5 text-black" strokeWidth={2.5} />
            </div>
            <span className="font-serif text-lg font-semibold">PropManage</span>
          </Link>
          <span className="text-xs text-stone-500">Ghid intern · acces tokenizat</span>
        </div>
      </header>

      <main className="px-4 sm:px-6 py-10">
        {loading && (
          <div className="text-center text-stone-500 py-20">Se încarcă...</div>
        )}
        {error && (
          <div className="max-w-md mx-auto text-center py-20" data-testid="help-error">
            <AlertCircle className="w-10 h-10 text-amber-400 mx-auto mb-3" />
            <p className="text-stone-300 mb-2">{error}</p>
            <Link to="/" className="text-[#d4ff3a] text-sm hover:underline">Înapoi la PropManage</Link>
          </div>
        )}
        {doc && <DocViewer doc={doc} downloadPdfUrl={`${API}/help/${token}/pdf`} />}
      </main>

      <footer className="border-t border-white/5 mt-16 py-8 text-center text-xs text-stone-500">
        © {new Date().getFullYear()} PropManage · Ghid intern privat
      </footer>
    </div>
  );
};

export default HelpPage;
