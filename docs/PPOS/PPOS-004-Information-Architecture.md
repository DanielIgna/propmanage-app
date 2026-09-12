# PPOS-004 · Information Architecture
Status: Draft v1.0 · Owner: Product Council
(Consolidează propunerea aprobată spre discuție din audit — `/app/memory/product/02_INFORMATION_ARCHITECTURE.md`.)

## De ce există fiecare pagină + pasul următor
| Pagina | De ce există | Obiectiv user | Pas logic următor |
|---|---|---|---|
| `/` | încredere + conversie | înțelege valoarea | Creează cont |
| `/client` Acasă | UNICA acțiune de azi | avansează casa | CTA-ul din Next Action |
| `/client` Casa mea | starea casei | „cum stă casa mea?" | next step din scorul unic |
| `/client` Lucrări | tranzacții | finalizează lucrarea | plată/confirmare |
| `/specialist` | venit | următoarea lucrare | acceptă/răspunde |
| `/imobile-verificate` | cumpărare cu încredere | găsește imobil | caută → detaliu |
| `/p/{slug}` | dovada publică | verifică o casă | contact/cont |
| `/marketplace` | alegerea specialistului | compară | profil → ofertă |

## Ierarhie & navigație
- Client: 4 destinații (Acasă · Casa mea · Lucrări · Setări). Tile-urile care duplică navigația dispar.
- Specialist: O singură navigație per device (desktop: left nav în workspace; mobil: bottom nav).
- Informația inutilă se mută la etapa corectă a călătoriei (matricea PPOS-007), nu se șterge din produs.
- Desktopul primește arhitectura proprie de workspace (PPOS-005); mobilul rămâne task-first (PPOS-006).
