import React from "react";
import { Link } from "react-router-dom";
import { CARD } from "../../../../design-system";
import { PageHeader } from "../../shared";

const STEPS = [
  ["1. Ce este asociația?", "Este grupul tuturor celor care au o parte din pădurea sau pășunea comună. Fiecare are o cotă. Conducerea trebuie să ne arate documentele și banii."],
  ["2. Care este cota mea?", "Deschide asociația, apoi fila „Cota mea”. Acolo vezi câte cote ai și din ce acte provin (de exemplu „Nr 372 = 0,20”)."],
  ["3. Cum îmi revendic cota?", "Apasă „Revendică”. Scrie numele cum apare în registru sau codul tău. Dacă ai moștenit, alege „Sunt moștenitor” și spune al cui ești urmaș. Conducerea îți răspunde și îți poate cere acte."],
  ["4. Cum dau mandat altcuiva?", "Dacă nu poți veni la adunare, intră la „Ședințe”, alege adunarea și apasă „Dau mandat”. Alegi un alt membru care votează în locul tău. Poți anula mandatul înainte de adunare."],
  ["5. Cum cer documente sau lămuriri?", "Intră la „Cereri”, scrie ce vrei să afli sau ce act vrei. Conducerea trebuie să îți răspundă în 30 de zile. Dacă întârzie, apare marcat."],
];

export default function GhidMembru() {
  return (
    <div className="space-y-5 max-w-3xl" data-testid="ghid-membru">
      <PageHeader title="Ghid pentru membri" subtitle="Pași simpli, pe înțelesul tuturor." />
      {STEPS.map(([t, d]) => (
        <section key={t} className={`${CARD} p-6`}>
          <h3 className="text-2xl font-bold text-slate-900 dark:text-white">{t}</h3>
          <p className="mt-2 text-xl leading-relaxed text-slate-700 dark:text-slate-200">{d}</p>
        </section>
      ))}
      <div className="flex flex-wrap gap-3 text-lg">
        <Link to="/radacini/composesorate/revendica" className="underline font-semibold">Revendică</Link>
        <Link to="/radacini/composesorate" className="underline font-semibold">Asociațiile</Link>
      </div>
    </div>
  );
}
