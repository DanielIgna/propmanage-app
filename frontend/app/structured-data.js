// JSON-LD blocks for the homepage (moved from the CRA public/index.html).
export const STRUCTURED_DATA = [
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "PropManage",
    alternateName: "Residency",
    url: "https://propmanage.ro",
    logo: "https://propmanage.ro/og-cover.svg",
    description:
      "Cartea Digitală a Casei Tale — documentele proprietății, istoricul lucrărilor, mentenanța și specialiștii verificați ai casei, într-un singur loc.",
    email: "contact@propmanage.ro",
    address: { "@type": "PostalAddress", addressCountry: "RO" },
    areaServed: { "@type": "Country", name: "România" },
    sameAs: [],
  },
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "PropManage",
    url: "https://propmanage.ro",
    inLanguage: "ro-RO",
    potentialAction: {
      "@type": "SearchAction",
      target: "https://propmanage.ro/marketplace?category={search_term_string}",
      "query-input": "required name=search_term_string",
    },
  },
  {
    "@context": "https://schema.org",
    "@type": "Service",
    serviceType: "Property Management Platform",
    provider: { "@type": "Organization", name: "PropManage", url: "https://propmanage.ro" },
    areaServed: "RO",
    name: "Cartea Digitală a Casei Tale + specialiști verificați",
    description:
      "Platformă unde proprietarii își păstrează documentele casei, istoricul lucrărilor și mentenanța, și găsesc specialiști verificați pentru intervenții pe casă.",
    offers: { "@type": "Offer", priceCurrency: "RON", availability: "https://schema.org/InStock" },
  },
  {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: "PropManage — Cartea Digitală a Casei Tale",
    url: "https://propmanage.ro/",
    inLanguage: "ro-RO",
    description:
      "Cartea Digitală a Casei Tale — documentele proprietății, istoricul lucrărilor, mentenanța și specialiștii verificați ai casei, într-un singur loc.",
    isPartOf: { "@type": "WebSite", url: "https://propmanage.ro", name: "PropManage" },
    about: { "@type": "Thing", name: "Cartea Digitală a Casei Tale" },
  },
];
