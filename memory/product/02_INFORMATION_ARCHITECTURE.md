# 02 · INFORMATION ARCHITECTURE (propunere Faza 2 — spre aprobare Fondator)
Redesign de IA, nu vizual. Business logic/API/DB neschimbate.

## De ce există fiecare pagină + pasul logic următor
| Pagina | De ce există | Obiectivul userului | Pasul logic următor |
|---|---|---|---|
| `/` Landing | încredere + conversie | să înțeleagă valoarea | Creează cont |
| `/client` Acasă | UNICA acțiune de azi | să-și avanseze casa | pasul din Next Action |
| `/client` Casa mea (Property Hub) | starea casei | „cum stă casa mea?" | next step din scorul unic |
| `/client` Lucrări | tranzacții active | să finalizeze lucrarea | plată/confirmare |
| `/specialist` | venit | următoarea lucrare | acceptă/răspunde |
| `/imobile-verificate` | cumpărare cu încredere | să găsească imobil | caută → detaliu → vizionare |
| `/p/{slug}` | dovada publică | să verifice casa | contact / creează cont |
| `/marketplace` | alegerea specialistului | să compare | vezi profil → cere ofertă |

## Informație inutilă / de mutat mai târziu (sinteza auditului)
- Client J0: tile-uri quick actions, Copilot, Descoperă → apar abia după prima proprietate/document.
- Property Hub: PVI, Twin Maturity, Risc → drill-down în scorul unic „Sănătatea casei"; Active+Detalii → secțiune colapsată; evenimente → istoric colapsat, tradus uman.
- Specialist: ghid+quests+config → UN card de progres derivat din starea reală; unelte blocate → invizibile (+1 rând „următoarea deblocare"); Cockpit → doar Advanced+.
- Marketplace public: scoruri interne și statusuri de moderare nu se afișează.

## Navigație (Faza 4)
- Client: header 4 tab-uri (Acasă · Casa mea · Lucrări · Setări) — tile-urile care duplică tab-urile dispar.
- Specialist: O SINGURĂ navigație (bottom pe mobil, header pe desktop — nu ambele).
- Un singur element plutitor per ecran (chat). Tur → „?" on-demand. Feedback beta → în Setări/meniu.
