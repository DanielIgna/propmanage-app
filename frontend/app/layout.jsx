import Script from "next/script";
import "@/index.css";
import "@/styles/themes.css";
import { STRUCTURED_DATA } from "./structured-data";

const TITLE = "PropManage — Cartea Digitală a Casei Tale · Documente, istoric, specialiști";
const DESCRIPTION =
  "PropManage — Cartea Digitală a Casei Tale. Un loc unic în care păstrezi documentele proprietății, istoricul lucrărilor, mentenanța și specialiștii verificați ai casei. Pentru proprietari care vor claritate și control.";

export const metadata = {
  metadataBase: new URL("https://propmanage.ro"),
  title: TITLE,
  description: DESCRIPTION,
  keywords:
    "cartea digitală a casei, cartea casei, documentele casei, istoricul lucrărilor, mentenanță locuință, administrarea proprietății, specialiști pentru casă, PropManage, apartament, proprietate",
  authors: [{ name: "PropManage" }],
  robots: { index: true, follow: true, "max-image-preview": "large", googleBot: { index: true, follow: true } },
  verification: { google: "W9yerKU6o_slXxwZSefxumjy_QxXfq-YsWqj2MbjD-k" },
  openGraph: {
    type: "website",
    title: "PropManage — Cartea Digitală a Casei Tale",
    description:
      "Documentele, istoricul lucrărilor, mentenanța și specialiștii casei tale — într-un singur loc. Cartea Digitală a Casei Tale, gata în câteva minute.",
    images: [{ url: "/og-cover.svg", width: 1200, height: 630 }],
    url: "https://propmanage.ro",
    siteName: "PropManage",
    locale: "ro_RO",
  },
  twitter: {
    card: "summary_large_image",
    title: "PropManage — Cartea Digitală a Casei Tale",
    description: "Documentele, istoricul lucrărilor, mentenanța și specialiștii casei tale — într-un singur loc.",
    images: ["/og-cover.svg"],
  },
  other: { "geo.region": "RO", "geo.placename": "România" },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0a0a0b",
};

// Google Ads (gtag) with GDPR Consent Mode v2: DENIED by default, restored from the cookie banner choice.
const GTAG_CONSENT = `
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
(function () {
  var analytics = false, marketing = false;
  try {
    var saved = JSON.parse(localStorage.getItem('pm_cookie_consent_v1') || 'null');
    if (saved) { analytics = !!saved.analytics; marketing = !!saved.marketing; }
  } catch (e) {}
  gtag('consent', 'default', {
    ad_storage: marketing ? 'granted' : 'denied',
    ad_user_data: marketing ? 'granted' : 'denied',
    ad_personalization: marketing ? 'granted' : 'denied',
    analytics_storage: analytics ? 'granted' : 'denied',
    wait_for_update: 500
  });
})();
gtag('config', 'AW-18423416296');
`;

const DATACLONE_GUARD = `window.addEventListener("error",function(e){if(e.error instanceof DOMException&&e.error.name==="DataCloneError"&&e.message&&e.message.includes("PerformanceServerTiming")){e.stopImmediatePropagation();e.preventDefault()}},true);`;

// PostHog: captures nothing until the "Statistice" consent is given.
const POSTHOG = `
!function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="init me ws ys ps bs capture je Di ks register register_once register_for_session unregister unregister_for_session Ps getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSurveysLoaded onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey canRenderSurveyAsync identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty Es $s createPersonProfile Is opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing Ss debug xs getPageViewId captureTraceFeedback captureTraceMetric".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
posthog.init("phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs", {
  api_host: "https://us.i.posthog.com",
  person_profiles: "identified_only",
  opt_out_capturing_by_default: true,
  session_recording: { recordCrossOriginIframes: true, capturePerformance: false }
});
try {
  var _pmc = JSON.parse(localStorage.getItem("pm_cookie_consent_v1") || "null");
  if (_pmc && _pmc.analytics) { posthog.opt_in_capturing(); }
} catch (e) {}
`;

export default function RootLayout({ children }) {
  return (
    <html lang="ro">
      <head>
        <meta httpEquiv="Content-Language" content="ro" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@600&display=swap" rel="stylesheet" />
        {STRUCTURED_DATA.map((d) => (
          <script key={d["@type"]} type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(d) }} />
        ))}
        <script dangerouslySetInnerHTML={{ __html: DATACLONE_GUARD }} />
      </head>
      <body>
        <noscript>You need to enable JavaScript to run this app.</noscript>
        <div id="root">{children}</div>
        <Script id="gtag-consent" strategy="beforeInteractive" dangerouslySetInnerHTML={{ __html: GTAG_CONSENT }} />
        <Script src="https://www.googletagmanager.com/gtag/js?id=AW-18423416296" strategy="afterInteractive" />
        <Script id="posthog" strategy="afterInteractive" dangerouslySetInnerHTML={{ __html: POSTHOG }} />
      </body>
    </html>
  );
}
