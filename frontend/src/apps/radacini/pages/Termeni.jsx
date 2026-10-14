import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { ArrowLeft, Sprout } from "lucide-react";
import { CARD } from "../../../design-system";
import { s8Api } from "../api_s8";

const TITLES = { terms: "Termeni și condiții", privacy: "Politica de confidențialitate" };

// react-markdown nu interpretează HTML brut (fără rehype-raw): sigur pentru texte din bază.
export const LegalMarkdown = ({ children }) => (
  <div className="space-y-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300 [&_h1]:text-xl [&_h1]:font-bold [&_h2]:text-base [&_h2]:font-bold [&_h2]:mt-4 [&_h3]:font-semibold [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_a]:text-emerald-700 [&_a]:underline">
    <ReactMarkdown
      components={{
        a: ({ href, children: c }) => (
          <a href={/^https?:|^mailto:|^\//.test(href || "") ? href : undefined} target="_blank" rel="noopener noreferrer">
            {c}
          </a>
        ),
      }}
    >
      {children || ""}
    </ReactMarkdown>
  </div>
);

export default function Termeni() {
  const [docs, setDocs] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let alive = true;
    s8Api
      .legalDocuments()
      .then((d) => alive && setDocs(d?.items || []))
      .catch(() => alive && setError(true));
    const prev = document.title;
    document.title = "Termeni · Rădăcini";
    return () => {
      alive = false;
      document.title = prev;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0b0c0d] px-4 py-8" data-testid="radacini-termeni">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-2 font-bold text-slate-900 dark:text-white">
            <Sprout className="w-5 h-5 text-emerald-600" /> Rădăcini
          </span>
          <Link to="/radacini" className="inline-flex items-center gap-1 text-sm text-slate-600 dark:text-slate-300 hover:underline">
            <ArrowLeft className="w-4 h-4" /> Înapoi
          </Link>
        </div>
        <p className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900" data-testid="radacini-termeni-draft">
          Versiune pilot — în revizuire juridică
        </p>
        {error && <p className="text-sm text-red-600">Nu am putut încărca documentele. Încearcă din nou mai târziu.</p>}
        {!docs && !error && <p className="text-sm text-slate-500">Se încarcă…</p>}
        {docs?.length === 0 && <p className="text-sm text-slate-500">Nu există documente publicate.</p>}
        {docs?.map((d) => (
          <article key={`${d.type}-${d.version}`} className={`${CARD} p-5 space-y-3`} data-testid={`radacini-termeni-${d.type}`}>
            <header>
              <h1 className="text-lg font-bold text-slate-900 dark:text-white">{d.title || TITLES[d.type] || d.type}</h1>
              <p className="text-xs text-slate-500">Versiunea {d.version}</p>
            </header>
            <LegalMarkdown>{d.body}</LegalMarkdown>
          </article>
        ))}
      </div>
    </div>
  );
}
