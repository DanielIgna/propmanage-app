import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Sprout } from "lucide-react";
import { CARD } from "../../../design-system";
import { betaApi } from "../api_beta";

const FIELDS = [
  ["name", "Operator"],
  ["legal_form", "Formă juridică"],
  ["cui", "CUI"],
  ["reg_no", "Nr. Registrul Comerțului"],
  ["address", "Sediu"],
  ["email", "Email de contact"],
  ["phone", "Telefon"],
  ["dpo_email", "Protecția datelor (GDPR)"],
];

// Pagina publică „Despre și contact”: cine operează platforma (date din configurarea serverului),
// ce face și ce nu face Rădăcini, cum se raportează conținut și cum se contestă o decizie.
export default function Despre() {
  const [info, setInfo] = useState(null);
  useEffect(() => {
    let alive = true;
    betaApi.operator().then((d) => alive && setInfo(d), () => alive && setInfo({ operator: {}, complete: false }));
    const prev = document.title;
    document.title = "Despre și contact · Rădăcini";
    return () => {
      alive = false;
      document.title = prev;
    };
  }, []);
  const op = info?.operator || {};
  const mail = (v) => <a href={`mailto:${v}`} className="text-emerald-700 underline dark:text-emerald-300">{v}</a>;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0b0c0d] px-4 py-8" data-testid="radacini-despre">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-2 font-bold text-slate-900 dark:text-white">
            <Sprout className="w-5 h-5 text-emerald-600" /> Rădăcini
          </span>
          <Link to="/radacini" className="inline-flex items-center gap-1 text-sm text-slate-600 dark:text-slate-300 hover:underline">
            <ArrowLeft className="w-4 h-4" /> Înapoi
          </Link>
        </div>

        <section className={`${CARD} p-5 space-y-3`}>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white">Despre Rădăcini</h1>
          <p className="text-sm text-slate-700 dark:text-slate-300">
            Rădăcini pune în legătură, în județul Cluj, proprietari de teren, cultivatori și familii care vor hrană locală.
            Platforma afișează informații și consemnează înțelegerile dintre membri.
          </p>
          <ul className="list-disc pl-5 text-sm text-slate-700 dark:text-slate-300 space-y-1">
            <li>Nu procesează plăți și nu ține bani. Plata se face direct între membri, la ridicare.</li>
            <li>Nu vinde produse și nu e parte în acordurile dintre membri.</li>
            <li>Acordurile din platformă nu înlocuiesc contractele cerute de lege (de exemplu, arenda înregistrată la primărie).</li>
            <li>Platforma e în <b>versiune beta</b>: funcțiile se pot schimba, iar termenii sunt în revizuire juridică.</li>
          </ul>
        </section>

        <section className={`${CARD} p-5 space-y-3`} data-testid="radacini-despre-operator">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Cine operează platforma</h2>
          {!info && <p className="text-sm text-slate-500">Se încarcă…</p>}
          {info && !info.complete && (
            <p className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Datele de identificare ale operatorului vor fi publicate înainte de deschiderea publică.
            </p>
          )}
          {info && (
            <dl className="grid grid-cols-1 sm:grid-cols-[200px_1fr] gap-x-4 gap-y-1 text-sm">
              {FIELDS.filter(([k]) => op[k]).map(([k, label]) => (
                <React.Fragment key={k}>
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="font-medium text-slate-900 dark:text-white break-words">{k.includes("email") ? mail(op[k]) : op[k]}</dd>
                </React.Fragment>
              ))}
            </dl>
          )}
        </section>

        <section className={`${CARD} p-5 space-y-2 text-sm text-slate-700 dark:text-slate-300`}>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Raportări, contestații și date personale</h2>
          <p>
            <b>Conținut ilegal sau contrar regulilor:</b> folosește butonul „Raportează” de pe anunț, teren sau comunitate.
            Primești confirmarea și decizia motivată în <Link to="/radacini/raportari" className="underline">Raportări</Link>.
          </p>
          <p>
            <b>Contestarea unei decizii de moderare:</b> scrie-ne la {op.email ? mail(op.email) : "adresa de contact de mai sus"},
            cu linkul conținutului și motivul. Răspundem în cel mult 30 de zile.
          </p>
          <p>
            <b>Datele tale:</b> din <Link to="/radacini/setari" className="underline">Setări</Link> poți descărca toate datele
            Rădăcini sau poți cere ștergerea contului. Pentru alte cereri GDPR: {op.dpo_email ? mail(op.dpo_email) : op.email ? mail(op.email) : "adresa de contact"}.
          </p>
          <p>
            <Link to="/radacini/termeni" className="underline">Termeni și politica de confidențialitate</Link>
          </p>
        </section>
      </div>
    </div>
  );
}
