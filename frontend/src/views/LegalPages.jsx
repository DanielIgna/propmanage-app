// Privacy Policy + Terms of Service + Cookie Policy — static public pages, GDPR-aware (RO).
import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Shield, FileText, Cookie } from "lucide-react";

const Layout = ({ icon: Icon, title, subtitle, children, testid }) => (
  <div className="min-h-screen bg-[#0a0a0b] text-stone-200 grain" data-testid={testid}>
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      <Link to="/" className="inline-flex items-center gap-1.5 text-xs text-stone-400 hover:text-[#d4ff3a] mb-6">
        <ArrowLeft className="w-3 h-3" /> Înapoi acasă
      </Link>
      <div className="flex items-center gap-3 mb-2">
        <Icon className="w-6 h-6 text-[#d4ff3a]" />
        <h1 className="font-serif text-4xl sm:text-5xl text-white">{title}</h1>
      </div>
      <p className="text-stone-400 text-sm mb-8">{subtitle}</p>
      <article className="prose prose-invert prose-stone max-w-none prose-headings:font-serif prose-headings:text-white prose-h2:text-2xl prose-h2:mt-8 prose-h2:mb-3 prose-h3:text-lg prose-h3:mt-6 prose-h3:mb-2 prose-p:text-sm prose-p:leading-relaxed prose-p:text-stone-300 prose-li:text-sm prose-li:text-stone-300 prose-a:text-[#d4ff3a] prose-strong:text-white">
        {children}
      </article>
      <div className="mt-12 pt-6 border-t border-stone-800 text-xs text-stone-500">
        Pentru întrebări legate de date sau drepturile tale: <a href="mailto:contact@propmanage.ro" className="text-[#d4ff3a]">contact@propmanage.ro</a>
      </div>
    </div>
  </div>
);

export const PrivacyPage = () => (
  <Layout icon={Shield} title="Politică de confidențialitate" subtitle="Ultima actualizare: februarie 2026" testid="privacy-page">
    <p><strong>VINTAGE FURNITURE S.R.L.</strong> — operatorul platformei <strong>PropManage</strong> (&quot;noi&quot;, &quot;platforma&quot;) — respectă confidențialitatea utilizatorilor și se conformează regulamentului GDPR (Regulamentul UE 2016/679) și legislației române privind protecția datelor personale.</p>
    <p className="text-sm">Operator de date: VINTAGE FURNITURE S.R.L. · CUI 35250247 · Nr. Reg. Com. J12/3534/2015 · Sediu: Aleea Negoiu nr. 8D, Ap. 25, Cluj-Napoca, jud. Cluj, 400676, România.</p>

    <h2>1. Ce date colectăm</h2>
    <ul>
      <li><strong>Date de cont</strong>: nume, email, telefon, rol (client / specialist / operator).</li>
      <li><strong>Date despre proprietăți</strong>: adresă, fotografii, plan, istoric mentenanță (doar pentru proprietățile tale).</li>
      <li><strong>Date de plată</strong>: procesate exclusiv prin Stripe — nu stocăm numerele de card.</li>
      <li><strong>Conversații cu AI Concierge</strong>: pentru îmbunătățirea serviciului, cu redactare automată a datelor sensibile.</li>
      <li><strong>Logging tehnic</strong>: IP, user-agent, ora accesului, pentru securitate și anti-abuz.</li>
    </ul>

    <h2>2. Cum folosim datele</h2>
    <ul>
      <li>Furnizarea serviciilor platformei (matching specialiști, plăți escrow, Digital Twin).</li>
      <li>Comunicare tranzacțională (notificări proiecte, plăți, dispute).</li>
      <li>Îmbunătățire produs (analiză agregată — niciodată identificabilă).</li>
      <li>Conformitate legală (facturi, audit, anti-fraudă).</li>
    </ul>
    <p><strong>NU vindem date</strong> către terți și NU folosim datele pentru reclamă behavioral targeting.</p>

    <h2>3. Cu cine partajăm datele</h2>
    <ul>
      <li><strong>Specialiști / Clienți</strong>: doar datele necesare pentru o cerere activă comună (nume, locație, descriere lucrare).</li>
      <li><strong>Stripe</strong> (procesare plăți).</li>
      <li><strong>Anthropic / Emergent</strong> (motorul AI Concierge — fără PII, redactare automată).</li>
      <li><strong>Resend</strong> (livrare emailuri tranzacționale).</li>
      <li><strong>Autorități</strong> doar la cerere legală formală (instanță, ANAF, GDPR DSAR).</li>
    </ul>

    <h2>4. Drepturile tale (GDPR)</h2>
    <ul>
      <li><strong>Acces</strong>: cere o copie a datelor tale.</li>
      <li><strong>Rectificare</strong>: corectează date inexacte.</li>
      <li><strong>Ștergere</strong> (&quot;dreptul de a fi uitat&quot;): cere ștergerea contului și a datelor (exceptând cele necesare pentru obligații legale).</li>
      <li><strong>Portabilitate</strong>: primește datele într-un format structurat (JSON / CSV).</li>
      <li><strong>Obiecție</strong>: opune-te procesării pentru anumite scopuri.</li>
      <li><strong>Plângere ANSPDCP</strong>: dacă consideri că drepturile îți sunt încălcate.</li>
    </ul>
    <p>Pentru orice cerere DSAR, scrie la <a href="mailto:contact@propmanage.ro">contact@propmanage.ro</a> — răspundem în maximum 30 zile.</p>

    <p className="mt-4 p-4 rounded-xl bg-white/5 border border-white/10">
      <strong className="text-[#d4ff3a]">📑 Notificări de confidențialitate per rol:</strong>{" "}
      Vezi notificările detaliate pentru <Link to="/privacy/notices" className="text-[#d4ff3a] underline">Client, Specialist, Operator, Vizitator + DPA (B2B)</Link> — toate descărcabile ca PDF.
    </p>

    <h2>5. Cookies</h2>
    <p>Folosim cookies <strong>strict necesare</strong> (autentificare, preferințe UI) și NU folosim cookies de tracking publicitar. Nu este necesar consent banner pentru cookies necesare.</p>

    <h2>6. Retenția datelor</h2>
    <ul>
      <li>Date cont activ: pe durata existenței contului.</li>
      <li>Date tranzacționale (facturi, contracte): 10 ani (obligație legală).</li>
      <li>Date AI Concierge: maxim 90 zile, apoi anonimizate.</li>
      <li>Logs securitate: maxim 12 luni.</li>
    </ul>

    <h2>7. Securitate</h2>
    <p>Aplicăm criptare la rest și în tranzit (HTTPS), hash bcrypt pentru parole, validare prompt-injection pentru AI, rate limiting, GEO / VPN blocking, monitorizare 24/7 cu sistem AI Health Score.</p>

    <h2>8. Modificări</h2>
    <p>Vom anunța modificările materiale prin email cu cel puțin 14 zile înainte de intrarea în vigoare.</p>
  </Layout>
);

export const TermsPage = () => (
  <Layout icon={FileText} title="Termeni și condiții" subtitle="Ultima actualizare: februarie 2026" testid="terms-page">
    <p>Prin utilizarea platformei <strong>PropManage</strong> (&quot;Platforma&quot;), accepți acești Termeni. Dacă nu ești de acord, te rugăm să nu folosești serviciile.</p>

    <h2>1. Cine este responsabil</h2>
    <p>Operator: <strong>VINTAGE FURNITURE S.R.L.</strong> (brandul comercial <strong>PropManage</strong>) · CUI 35250247 · Nr. Reg. Com. J12/3534/2015 · Sediu: Aleea Negoiu nr. 8D, Ap. 25, Cluj-Napoca, jud. Cluj, 400676, România. Contact: <a href="mailto:contact@propmanage.ro">contact@propmanage.ro</a>.</p>

    <h2>2. Cont utilizator</h2>
    <ul>
      <li>Trebuie să ai minim 18 ani și să furnizezi date reale.</li>
      <li>Răspunzi pentru păstrarea în siguranță a parolei.</li>
      <li>Ne rezervăm dreptul de a suspenda conturi în caz de abuz, fraudă sau încălcare a acestor termeni.</li>
    </ul>

    <h2>3. Roluri</h2>
    <ul>
      <li><strong>Client</strong>: postează cereri, contractează specialiști, plătește în escrow.</li>
      <li><strong>Specialist</strong>: oferă servicii contra cost, plătește 45 RON / lead acceptat, primește 95% din valoarea proiectului.</li>
      <li><strong>Operator</strong>: validează Digital Twin-uri (la invitație Admin).</li>
      <li><strong>Admin</strong>: rol intern — nu se înregistrează prin formular public.</li>
    </ul>

    <h2>4. Plăți și escrow</h2>
    <ul>
      <li>Toate plățile sunt procesate prin Stripe (PCI-DSS Level 1).</li>
      <li>Fondurile sunt blocate în escrow până la confirmarea livrării de către client.</li>
      <li>Pentru proiecte multi-milestone, fiecare tranșă (25%) se eliberează după acceptul clientului.</li>
      <li><strong>Garanție 30 zile</strong>: pe tranșa finală există rețineți o garanție automată, eliberată după 30 zile sau confirmare explicită.</li>
      <li>Comision platformă: <strong>5%</strong> din valoarea fiecărei tranșe.</li>
      <li>Lead-fee specialist: <strong>45 RON</strong> per acceptare.</li>
    </ul>

    <h2>5. Dispute</h2>
    <p>Disputele se rezolvă inițial direct între părți prin chat-ul integrat. Dacă nu se ajunge la o soluție în 7 zile, intervine echipa PropManage prin arbitraj intern. Decizia poate fi contestată conform legislației.</p>

    <h2>6. Trust Score și verificare</h2>
    <p>Specialiștii sunt verificați manual de echipa de Admin. Trust Score este calculat automat din evaluări, rate de livrare la timp, dispute. Nu garantăm calitatea individuală a fiecărui specialist — este un marketplace P2P.</p>

    <h2>7. AI Concierge</h2>
    <p>Concierge AI este un asistent informativ. <strong>Nu execută acțiuni</strong> în cont. Răspunsurile pot conține inacurăți — verifică întotdeauna în UI sau cu suportul uman pentru decizii importante.</p>

    <h2>8. Interdicții</h2>
    <ul>
      <li>Folosirea platformei pentru activități ilegale, scam, money laundering.</li>
      <li>Încercări de prompt injection, scraping automat, evitarea sistemelor de securitate.</li>
      <li>Postarea de conținut ofensator, discriminatoriu, sau care încalcă proprietatea intelectuală.</li>
      <li>Comunicarea în afara platformei pentru a evita comisionul (anti-circumvent).</li>
    </ul>

    <h2>9. Răspundere</h2>
    <p>Platforma este &quot;AS IS&quot;. Nu garantăm continuitatea serviciului 24/7 (vezi <Link to="/status" className="text-[#d4ff3a]">/status</Link>). Răspunderea noastră maximă este limitată la valoarea comisioanelor încasate în ultimele 12 luni de la utilizator.</p>

    <h2>10. Reziliere</h2>
    <p>Poți închide contul oricând din setări. Datele tranzacționale rămân arhivate conform <Link to="/privacy" className="text-[#d4ff3a]">Politicii de Confidențialitate</Link>.</p>

    <h2>11. Legea aplicabilă</h2>
    <p>Acești termeni sunt guvernați de legea română. Disputele se rezolvă la instanțele competente din România.</p>

    <h2>12. Modificări</h2>
    <p>Vom notifica modificările materiale prin email cu cel puțin 14 zile înainte.</p>
  </Layout>
);


export const CookiePolicyPage = () => (
  <Layout icon={Cookie} title="Politică de cookies" subtitle="Ultima actualizare: iunie 2026" testid="cookies-page">
    <p>Această pagină explică în detaliu cum folosește <strong>PropManage</strong> cookies-uri și tehnologii similare. Politica este conformă cu <strong>GDPR</strong>, <strong>Directiva ePrivacy</strong> și legea română 506/2004.</p>

    <h2>1. Ce sunt cookies-urile</h2>
    <p>Cookies-urile sunt fișiere text mici stocate de browser pe dispozitivul tău. Le folosim pentru a-ți păstra sesiunea de autentificare, preferințele de interfață, pentru securitate și — <strong>doar cu consimțământul tău</strong> — pentru statistici de utilizare și măsurarea campaniilor de marketing.</p>

    <h2>2. Ce cookies folosim</h2>
    <p>Folosim cookies <strong>strict necesare</strong> și <strong>funcționale</strong> (fără consimțământ, esențiale pentru funcționare), precum și cookies <strong>opționale</strong> de <strong>statistică</strong> și de <strong>marketing</strong> care se activează <strong>numai după ce le accepți</strong> din bannerul de consimțământ. Până la acceptare, cookies-urile opționale rămân dezactivate (Google Consent Mode v2 pornește implicit pe „denied").</p>

    <table style={{width:'100%', borderCollapse:'collapse', margin:'16px 0', fontSize:'13px'}}>
      <thead>
        <tr style={{borderBottom:'1px solid #ffffff20', textAlign:'left'}}>
          <th style={{padding:'8px 10px', color:'#d4ff3a'}}>Nume</th>
          <th style={{padding:'8px 10px', color:'#d4ff3a'}}>Scop</th>
          <th style={{padding:'8px 10px', color:'#d4ff3a'}}>Durată</th>
          <th style={{padding:'8px 10px', color:'#d4ff3a'}}>Tip</th>
        </tr>
      </thead>
      <tbody style={{color:'#c8c8cc'}}>
        <tr style={{borderBottom:'1px solid #ffffff10'}}>
          <td style={{padding:'8px 10px'}}><code>access_token</code></td>
          <td style={{padding:'8px 10px'}}>Autentificare JWT — îți păstrează sesiunea activă.</td>
          <td style={{padding:'8px 10px'}}>1 oră</td>
          <td style={{padding:'8px 10px'}}>Strict necesar</td>
        </tr>
        <tr style={{borderBottom:'1px solid #ffffff10'}}>
          <td style={{padding:'8px 10px'}}><code>refresh_token</code></td>
          <td style={{padding:'8px 10px'}}>Reînnoire automată a sesiunii fără logout.</td>
          <td style={{padding:'8px 10px'}}>30 zile</td>
          <td style={{padding:'8px 10px'}}>Strict necesar</td>
        </tr>
        <tr style={{borderBottom:'1px solid #ffffff10'}}>
          <td style={{padding:'8px 10px'}}><code>theme</code> / <code>locale</code></td>
          <td style={{padding:'8px 10px'}}>Reține preferințele tale de UI (dark/light, limba RO/EN).</td>
          <td style={{padding:'8px 10px'}}>1 an</td>
          <td style={{padding:'8px 10px'}}>Funcțional</td>
        </tr>
        <tr style={{borderBottom:'1px solid #ffffff10'}}>
          <td style={{padding:'8px 10px'}}><code>csrf_token</code></td>
          <td style={{padding:'8px 10px'}}>Protecție anti-CSRF pentru formulare sensibile.</td>
          <td style={{padding:'8px 10px'}}>Sesiune</td>
          <td style={{padding:'8px 10px'}}>Strict necesar (Securitate)</td>
        </tr>
        <tr>
          <td style={{padding:'8px 10px'}}><code>onboarding_seen</code></td>
          <td style={{padding:'8px 10px'}}>Indică dacă ai parcurs deja tour-ul inițial (pentru a nu-l reafișa).</td>
          <td style={{padding:'8px 10px'}}>1 an</td>
          <td style={{padding:'8px 10px'}}>Funcțional</td>
        </tr>
        <tr style={{borderBottom:'1px solid #ffffff10'}}>
          <td style={{padding:'8px 10px'}}><code>ph_*_posthog</code></td>
          <td style={{padding:'8px 10px'}}>Statistici de utilizare (PostHog) — cum sunt folosite paginile, pentru a îmbunătăți produsul. Se activează doar după consimțământ „Statistice".</td>
          <td style={{padding:'8px 10px'}}>~1 an</td>
          <td style={{padding:'8px 10px'}}>Opțional · Statistică</td>
        </tr>
        <tr>
          <td style={{padding:'8px 10px'}}><code>_gcl_au</code> (Google Ads)</td>
          <td style={{padding:'8px 10px'}}>Măsurarea conversiilor și remarketing pentru campaniile Google Ads. Se activează doar după consimțământ „Marketing".</td>
          <td style={{padding:'8px 10px'}}>~90 zile</td>
          <td style={{padding:'8px 10px'}}>Opțional · Marketing</td>
        </tr>
      </tbody>
    </table>

    <h2>3. Cookies de la terți</h2>
    <p>Folosim un set <strong>limitat și auditat</strong> de servicii terțe:</p>
    <ul>
      <li><strong>Stripe</strong> (<code>__stripe_mid</code>, <code>__stripe_sid</code>) — anti-fraudă pentru plățile escrow. Strict necesar. Stripe nu primește datele tale personale dincolo de ce e necesar pentru a procesa o plată.</li>
      <li><strong>Cloudflare</strong> (<code>__cf_bm</code>, <code>cf_clearance</code>) — protecție anti-bot și CDN. Strict necesar. Nu folosit pentru profilare.</li>
      <li><strong>PostHog</strong> — statistici de utilizare a produsului (first-party analytics). <strong>Opțional</strong>, se activează doar după consimțământul „Statistice".</li>
      <li><strong>Google Ads</strong> (<code>AW-18423416296</code>, via <code>googletagmanager.com</code>) — măsurarea conversiilor și remarketing. <strong>Opțional</strong>, se activează doar după consimțământul „Marketing", prin Google Consent Mode v2.</li>
    </ul>

    <h2>4. Consimțământ și bannerul de cookies</h2>
    <p>La prima vizită îți afișăm un <strong>banner de consimțământ</strong> cu opțiuni granulare — <strong>Accept toate</strong>, <strong>Refuz</strong> (opționalele) și <strong>Personalizează</strong> (Statistice / Marketing separat), ÎNAINTE de a seta cookies-urile opționale. Cookies-urile strict necesare și funcționale solicitate explicit (ex: „ține-mă logat") nu necesită consimțământ conform art. 5(3) ePrivacy.</p>
    <p>Pentru cookies-urile de marketing (Google Ads) folosim <strong>Google Consent Mode v2</strong>: implicit pe „denied", activate doar când accepți „Marketing". Îți poți schimba oricând alegerea din butonul cu iconița de cookie (stânga-jos).</p>

    <h2>5. Cum controlezi cookies-urile</h2>
    <ul>
      <li><strong>Browser</strong>: setările tale de browser îți permit să blochezi sau să ștergi cookies-uri. Atenție: blocarea cookies-urilor strict necesare va face imposibilă autentificarea pe PropManage.</li>
      <li><strong>Mobil</strong>: Setări → Aplicații → Browser → Permisiuni → Cookies.</li>
      <li><strong>Logout</strong>: la logout din contul tău, cookies-urile de autentificare sunt invalidate imediat (server-side blacklist).</li>
    </ul>

    <h2>6. LocalStorage și sessionStorage</h2>
    <p>Pe lângă cookies, folosim <code>localStorage</code> pentru a stoca preferințe UI (sortare tabele, filtrele tale salvate, cache offline pentru Digital Twin). Acestea NU conțin date personale identificabile și NU sunt trimise către server. Le poți șterge oricând din DevTools → Application → Storage.</p>

    <h2>7. Modificări ale acestei politici</h2>
    <p>Orice modificare materială va fi anunțată prin email tuturor utilizatorilor înregistrați cu cel puțin <strong>14 zile</strong> înainte. Versiunea curentă este întotdeauna afișată la <Link to="/cookies" className="text-[#d4ff3a]">/cookies</Link>.</p>

    <h2>8. Contact DPO</h2>
    <p>Pentru orice întrebare legată de cookies sau alte date personale, scrie la <a href="mailto:contact@propmanage.ro">contact@propmanage.ro</a>. Răspundem în maximum 30 zile (de obicei sub 7 zile).</p>

    <p className="mt-6 p-4 rounded-xl bg-white/5 border border-white/10 text-xs">
      Vezi și: <Link to="/privacy" className="text-[#d4ff3a]">Politica de confidențialitate</Link> · <Link to="/privacy/notices" className="text-[#d4ff3a]">Notificări per rol</Link> · <Link to="/terms" className="text-[#d4ff3a]">Termeni și condiții</Link>
    </p>
  </Layout>
);
